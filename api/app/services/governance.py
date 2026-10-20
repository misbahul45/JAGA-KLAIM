import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.errors import ApiError, conflict, not_found, unprocessable
from app.domain.default_policy import POLICY_CONFIG
from app.domain.enums import (
    RuleUpdateStatus,
    RuleValidation,
    Tier,
    Verdict,
    VersionStatus,
)
from app.domain.hashing import config_hash
from app.domain.permissions import Permission
from app.domain.policy import (
    PolicyRuleView,
    PolicyValidationError,
    decide,
    validate_policy,
)
from app.domain.specs import ExpectedEvidenceSpec
from app.domain.states import (
    RULE_UPDATE_TRANSITIONS,
    VERSION_TRANSITIONS,
    InvalidTransition,
    ensure_transition,
)
from app.evaluation.cases import CASES
from app.evaluation.harness import compare_reports, evaluate
from app.models import (
    HumanVerdict,
    Intervention,
    InvestigationRun,
    PolicyRule,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleUpdate,
    RuleUpdateBasis,
    RuleVersion,
)
from app.models.base import utcnow
from app.models.rules import ExpectedRule
from app.services import audit
from app.services.auth import Principal
from app.services.investigation import active_policy, policy_views, rule_views

MIN_NOTE_LENGTH = 10
ELIGIBLE_BASIS_VERDICTS = frozenset(
    {Verdict.DOES_NOT_SUPPORT_FINDING.value, Verdict.INSUFFICIENT_EVIDENCE.value}
)
CREATABLE_VALIDATION = frozenset({RuleValidation.UNVALIDATED.value, RuleValidation.SIMULATION.value})


def _audit(
    session: Session,
    principal: Principal,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_type="user",
        actor_id=principal.user_id,
        payload=payload,
    )


def _step(entity: str, current: VersionStatus, target: VersionStatus) -> None:
    try:
        ensure_transition(entity, VERSION_TRANSITIONS, current, target)
    except InvalidTransition as exc:
        raise conflict("invalid_state", str(exc), {"from": exc.current, "to": exc.target}) from exc


def _separation_of_duties(author: uuid.UUID | None, actor: Principal, what: str) -> None:
    if author is not None and author == actor.user_id:
        raise ApiError(
            409,
            "separation_of_duties",
            f"{what} tidak boleh disetujui oleh pihak yang menyusunnya",
        )


@dataclass(frozen=True)
class RuleSetView:
    rule_set: RuleSet
    vector: RiskVector
    versions: list[RuleVersion]


def list_vectors(session: Session) -> list[RiskVector]:
    return list(session.exec(select(RiskVector).order_by(col(RiskVector.code))))


def list_rule_sets(session: Session) -> list[RuleSetView]:
    rows = session.exec(
        select(RuleSet, RiskVector)
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .order_by(col(RiskVector.code), col(RuleSet.name))
    ).all()
    views = []
    for rule_set, vector in rows:
        versions = list(
            session.exec(
                select(RuleVersion)
                .where(RuleVersion.rule_set_id == rule_set.id)
                .order_by(col(RuleVersion.created_at).desc())
            )
        )
        views.append(RuleSetView(rule_set, vector, versions))
    return views


def get_rule_version(
    session: Session, version_id: uuid.UUID
) -> tuple[RuleVersion, RuleSet, RiskVector, list[ExpectedRule]]:
    row = session.exec(
        select(RuleVersion, RuleSet, RiskVector)
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(RuleVersion.id == version_id)
    ).first()
    if row is None:
        raise not_found("Versi aturan")
    version, rule_set, vector = row
    rules = list(
        session.exec(
            select(ExpectedRule)
            .where(ExpectedRule.rule_version_id == version.id)
            .order_by(col(ExpectedRule.code_pattern))
        )
    )
    return version, rule_set, vector, rules


def _lock_version(session: Session, version_id: uuid.UUID) -> RuleVersion:
    version = session.exec(
        select(RuleVersion).where(RuleVersion.id == version_id).with_for_update()
    ).first()
    if version is None:
        raise not_found("Versi aturan")
    return version


def _validate_spec(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        return ExpectedEvidenceSpec.model_validate(raw).model_dump(mode="json")
    except ValidationError as exc:
        raise unprocessable(
            "invalid_spec",
            "Spesifikasi bukti yang diharapkan tidak valid",
            {"errors": [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]},
        ) from exc


def create_rule_version(
    session: Session,
    principal: Principal,
    *,
    rule_set_id: uuid.UUID,
    version: str,
    validation_status: str,
    base_version_id: uuid.UUID | None,
    expected_rules: list[tuple[str, dict[str, Any]]],
) -> RuleVersion:
    if validation_status not in CREATABLE_VALIDATION:
        raise unprocessable(
            "validation_requires_approver",
            "Status tervalidasi_pakar hanya dapat ditetapkan oleh persetujuan pakar",
        )
    rule_set = session.get(RuleSet, rule_set_id)
    if rule_set is None:
        raise not_found("Rule set")
    specs = [(pattern, _validate_spec(spec)) for pattern, spec in expected_rules]
    if base_version_id is not None and not specs:
        base = session.get(RuleVersion, base_version_id)
        if base is None or base.rule_set_id != rule_set.id:
            raise not_found("Versi aturan dasar")
        specs = [
            (r.code_pattern, r.expected_evidence_spec)
            for r in session.exec(
                select(ExpectedRule).where(
                    ExpectedRule.rule_version_id == base.id, col(ExpectedRule.is_active).is_(True)
                )
            )
        ]
    taken = session.exec(
        select(RuleVersion.id).where(RuleVersion.rule_set_id == rule_set.id, RuleVersion.version == version)
    ).first()
    if taken is not None:
        raise conflict("version_exists", "Label versi sudah dipakai pada rule set ini")
    created = RuleVersion(
        rule_set_id=rule_set.id,
        version=version,
        status=VersionStatus.DRAFT.value,
        validation_status=validation_status,
        created_by=principal.user_id,
    )
    session.add(created)
    session.flush()
    for pattern, spec in specs:
        session.add(ExpectedRule(rule_version_id=created.id, code_pattern=pattern, expected_evidence_spec=spec))
    _audit(session, principal, "rule_version", created.id, "rule_version.created",
           {"rule_set_id": rule_set.id, "version": version, "rules": len(specs), "base": base_version_id})
    session.commit()
    return created


def submit_rule_version(session: Session, principal: Principal, version_id: uuid.UUID) -> RuleVersion:
    version = _lock_version(session, version_id)
    _step("versi aturan", VersionStatus(version.status), VersionStatus.PENDING_APPROVAL)
    count = session.exec(
        select(func.count()).select_from(ExpectedRule).where(
            ExpectedRule.rule_version_id == version.id, col(ExpectedRule.is_active).is_(True)
        )
    ).one()
    if count == 0:
        raise unprocessable("empty_rule_version", "Versi aturan belum memiliki expected rule")
    version.status = VersionStatus.PENDING_APPROVAL.value
    version.submitted_at = utcnow()
    session.add(version)
    _audit(session, principal, "rule_version", version.id, "rule_version.submitted", {"rules": count})
    session.commit()
    return version


def approve_rule_version(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    validation_status: str | None,
    expert_validation_confirmed: bool,
    note: str | None,
) -> RuleVersion:
    version = _lock_version(session, version_id)
    _step("versi aturan", VersionStatus(version.status), VersionStatus.APPROVED)
    _separation_of_duties(version.created_by, principal, "Versi aturan")
    chosen = validation_status or version.validation_status
    if chosen not in {v.value for v in RuleValidation}:
        raise unprocessable("unknown_validation_status", "Status validasi tidak dikenal")
    if chosen == RuleValidation.EXPERT_VALIDATED.value and not (
        expert_validation_confirmed and len((note or "").strip()) >= MIN_NOTE_LENGTH
    ):
        raise unprocessable(
            "expert_validation_unconfirmed",
            "Status tervalidasi_pakar memerlukan konfirmasi eksplisit dan catatan dasar validasi",
        )
    version.status = VersionStatus.APPROVED.value
    version.validation_status = chosen
    version.approved_by = principal.user_id
    version.approved_at = utcnow()
    session.add(version)
    _audit(session, principal, "rule_version", version.id, "rule_version.approved",
           {"validation_status": chosen, "validation_note": (note or "").strip() or None})
    session.commit()
    return version


def reject_rule_version(
    session: Session, principal: Principal, version_id: uuid.UUID, *, reason: str
) -> RuleVersion:
    version = _lock_version(session, version_id)
    _step("versi aturan", VersionStatus(version.status), VersionStatus.REJECTED)
    version.status = VersionStatus.REJECTED.value
    session.add(version)
    _audit(session, principal, "rule_version", version.id, "rule_version.rejected", {"reason": reason})
    session.commit()
    return version


def _retire_active(session: Session, rule_set_id: uuid.UUID, principal: Principal) -> list[uuid.UUID]:
    retired: list[uuid.UUID] = []
    now = utcnow()
    for active in session.exec(
        select(RuleVersion)
        .where(RuleVersion.rule_set_id == rule_set_id, RuleVersion.status == VersionStatus.ACTIVE.value)
        .with_for_update()
    ):
        active.status = VersionStatus.RETIRED.value
        active.retired_at = now
        session.add(active)
        retired.append(active.id)
        _audit(session, principal, "rule_version", active.id, "rule_version.retired", {"reason": "superseded"})
    session.flush()
    return retired


def activate_rule_version(session: Session, principal: Principal, version_id: uuid.UUID) -> RuleVersion:
    version = _lock_version(session, version_id)
    _step("versi aturan", VersionStatus(version.status), VersionStatus.ACTIVE)
    retired = _retire_active(session, version.rule_set_id, principal)
    version.status = VersionStatus.ACTIVE.value
    version.activated_at = utcnow()
    session.add(version)
    _audit(session, principal, "rule_version", version.id, "rule_version.activated", {"retired": retired})
    session.commit()
    return version


def retire_rule_version(session: Session, principal: Principal, version_id: uuid.UUID) -> RuleVersion:
    version = _lock_version(session, version_id)
    _step("versi aturan", VersionStatus(version.status), VersionStatus.RETIRED)
    version.status = VersionStatus.RETIRED.value
    version.retired_at = utcnow()
    session.add(version)
    _audit(session, principal, "rule_version", version.id, "rule_version.retired", {"reason": "manual"})
    session.commit()
    return version


def list_policy_versions(session: Session) -> list[PolicyVersion]:
    return list(session.exec(select(PolicyVersion).order_by(col(PolicyVersion.created_at).desc())))


def get_policy_version(session: Session, version_id: uuid.UUID) -> tuple[PolicyVersion, list[PolicyRule]]:
    version = session.get(PolicyVersion, version_id)
    if version is None:
        raise not_found("Versi kebijakan")
    rules = list(
        session.exec(
            select(PolicyRule)
            .where(PolicyRule.policy_version_id == version.id)
            .order_by(col(PolicyRule.priority))
        )
    )
    return version, rules


def _views_of(rules: list[PolicyRule]) -> list[PolicyRuleView]:
    return [
        PolicyRuleView(r.id, r.code, Tier(r.tier), r.priority, r.condition_spec, r.is_active)
        for r in rules
    ]


def _check_policy(rules: list[PolicyRule]) -> None:
    try:
        validate_policy(_views_of(rules))
    except PolicyValidationError as exc:
        raise unprocessable("invalid_policy", "Kebijakan tidak valid", {"problems": exc.problems}) from exc


def create_policy_version(
    session: Session,
    principal: Principal,
    *,
    version: str,
    rules: list[dict[str, Any]],
) -> PolicyVersion:
    taken = session.exec(select(PolicyVersion.id).where(PolicyVersion.version == version)).first()
    if taken is not None:
        raise conflict("version_exists", "Label versi kebijakan sudah dipakai")
    created = PolicyVersion(
        version=version,
        status=VersionStatus.DRAFT.value,
        config=POLICY_CONFIG,
        config_hash="pending",
        created_by=principal.user_id,
    )
    session.add(created)
    session.flush()
    stored: list[PolicyRule] = []
    for rule in rules:
        row = PolicyRule(
            policy_version_id=created.id,
            code=rule["code"],
            tier=rule["tier"],
            condition_spec=rule["condition"],
            priority=rule["priority"],
        )
        session.add(row)
        stored.append(row)
    session.flush()
    created.config_hash = config_hash(
        {
            "config": created.config,
            "rules": [
                {"code": r.code, "tier": r.tier, "priority": r.priority, "condition": r.condition_spec}
                for r in sorted(stored, key=lambda r: r.priority)
            ],
        }
    )
    session.add(created)
    _audit(session, principal, "policy_version", created.id, "policy_version.created",
           {"version": version, "rules": len(stored), "config_hash": created.config_hash})
    session.commit()
    return created


def submit_policy_version(session: Session, principal: Principal, version_id: uuid.UUID) -> PolicyVersion:
    version, rules = get_policy_version(session, version_id)
    _step("versi kebijakan", VersionStatus(version.status), VersionStatus.PENDING_APPROVAL)
    _check_policy(rules)
    version.status = VersionStatus.PENDING_APPROVAL.value
    session.add(version)
    _audit(session, principal, "policy_version", version.id, "policy_version.submitted", {"rules": len(rules)})
    session.commit()
    return version


def approve_policy_version(session: Session, principal: Principal, version_id: uuid.UUID) -> PolicyVersion:
    version, rules = get_policy_version(session, version_id)
    _step("versi kebijakan", VersionStatus(version.status), VersionStatus.APPROVED)
    _separation_of_duties(version.created_by, principal, "Versi kebijakan")
    _check_policy(rules)
    version.status = VersionStatus.APPROVED.value
    version.approved_by = principal.user_id
    version.approved_at = utcnow()
    session.add(version)
    _audit(session, principal, "policy_version", version.id, "policy_version.approved", {})
    session.commit()
    return version


def reject_policy_version(
    session: Session, principal: Principal, version_id: uuid.UUID, *, reason: str
) -> PolicyVersion:
    version, _ = get_policy_version(session, version_id)
    _step("versi kebijakan", VersionStatus(version.status), VersionStatus.REJECTED)
    version.status = VersionStatus.REJECTED.value
    session.add(version)
    _audit(session, principal, "policy_version", version.id, "policy_version.rejected", {"reason": reason})
    session.commit()
    return version


def activate_policy_version(session: Session, principal: Principal, version_id: uuid.UUID) -> PolicyVersion:
    version, rules = get_policy_version(session, version_id)
    _step("versi kebijakan", VersionStatus(version.status), VersionStatus.ACTIVE)
    _check_policy(rules)
    now = utcnow()
    retired: list[uuid.UUID] = []
    for active in session.exec(
        select(PolicyVersion).where(PolicyVersion.status == VersionStatus.ACTIVE.value).with_for_update()
    ):
        active.status = VersionStatus.RETIRED.value
        session.add(active)
        retired.append(active.id)
    session.flush()
    version.status = VersionStatus.ACTIVE.value
    version.activated_at = now
    session.add(version)
    _audit(session, principal, "policy_version", version.id, "policy_version.activated", {"retired": retired})
    session.commit()
    return version


def retire_policy_version(session: Session, principal: Principal, version_id: uuid.UUID) -> PolicyVersion:
    version, _ = get_policy_version(session, version_id)
    _step("versi kebijakan", VersionStatus(version.status), VersionStatus.RETIRED)
    version.status = VersionStatus.RETIRED.value
    session.add(version)
    _audit(session, principal, "policy_version", version.id, "policy_version.retired", {})
    session.commit()
    return version


def preview_policy(
    session: Session, version_id: uuid.UUID, facts: dict[str, Any]
) -> dict[str, Any]:
    _, rules = get_policy_version(session, version_id)
    try:
        decision = decide(_views_of(rules), facts)
    except PolicyValidationError as exc:
        raise unprocessable("no_matching_rule", "Tidak ada aturan yang cocok", {"problems": exc.problems}) from exc
    return {"tier": decision.tier.value, "rule": decision.rule_code, "priority": decision.priority}


def _merge_spec(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return _validate_spec(merged)


def _get_update(session: Session, update_id: uuid.UUID) -> RuleUpdate:
    update = session.exec(select(RuleUpdate).where(RuleUpdate.id == update_id).with_for_update()).first()
    if update is None:
        raise not_found("Usulan pembaruan aturan")
    return update


def _update_step(current: RuleUpdateStatus, target: RuleUpdateStatus) -> None:
    try:
        ensure_transition("pembaruan aturan", RULE_UPDATE_TRANSITIONS, current, target)
    except InvalidTransition as exc:
        raise conflict("invalid_state", str(exc), {"from": exc.current, "to": exc.target}) from exc


def propose_rule_update(
    session: Session,
    principal: Principal,
    *,
    basis_verdict_ids: list[uuid.UUID],
    base_rule_version_id: uuid.UUID,
    expected_rule_id: uuid.UUID,
    spec_patch: dict[str, Any],
    rationale: str,
) -> RuleUpdate:
    base, _, vector, _ = get_rule_version(session, base_rule_version_id)
    target_rule = session.get(ExpectedRule, expected_rule_id)
    if target_rule is None or target_rule.rule_version_id != base.id:
        raise not_found("Expected rule pada versi dasar")
    _merge_spec(target_rule.expected_evidence_spec, spec_patch)

    unique_ids = list(dict.fromkeys(basis_verdict_ids))
    rows = session.exec(
        select(HumanVerdict, Intervention, RiskVector.code)
        .join(Intervention, col(Intervention.id) == col(HumanVerdict.intervention_id))
        .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
        .join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(
            col(HumanVerdict.id).in_(unique_ids),
            Intervention.faskes_id == principal.faskes_id,
        )
    ).all()
    if len(rows) != len(unique_ids):
        raise not_found("Verdict dasar")
    superseded = set(
        session.exec(
            select(HumanVerdict.supersedes_verdict_id).where(
                col(HumanVerdict.supersedes_verdict_id).in_(unique_ids)
            )
        )
    )
    for verdict, _, vector_code in rows:
        if verdict.id in superseded:
            raise conflict("verdict_superseded", "Verdict dasar sudah dikoreksi; gunakan verdict terbaru")
        if verdict.verdict not in ELIGIBLE_BASIS_VERDICTS:
            raise unprocessable(
                "verdict_not_eligible",
                "Hanya verdict yang menyatakan temuan tidak didukung atau bukti tidak cukup yang dapat menjadi dasar usulan",
            )
        if vector_code != vector.code:
            raise unprocessable("vector_mismatch", "Verdict dasar berasal dari vektor risiko yang berbeda")

    update = RuleUpdate(
        verdict_id=unique_ids[0],
        base_rule_version_id=base.id,
        proposed_by=principal.user_id,
        proposed_change={
            "expected_rule_id": str(expected_rule_id),
            "spec_patch": spec_patch,
            "rationale": rationale.strip(),
        },
        status=RuleUpdateStatus.PROPOSED.value,
    )
    session.add(update)
    session.flush()
    for verdict_id in unique_ids:
        session.add(RuleUpdateBasis(rule_update_id=update.id, verdict_id=verdict_id))
    _audit(session, principal, "rule_update", update.id, "rule_update.proposed",
           {"base_rule_version_id": base.id, "basis_verdict_ids": unique_ids, "vector": vector.code})
    session.commit()
    return update


def _clone_rule_version(
    session: Session,
    base: RuleVersion,
    *,
    version: str,
    created_by: uuid.UUID | None,
    validation_status: str,
) -> tuple[RuleVersion, dict[uuid.UUID, ExpectedRule]]:
    clone = RuleVersion(
        rule_set_id=base.rule_set_id,
        version=version,
        status=VersionStatus.DRAFT.value,
        validation_status=validation_status,
        created_by=created_by,
    )
    session.add(clone)
    session.flush()
    mapping: dict[uuid.UUID, ExpectedRule] = {}
    for original in session.exec(
        select(ExpectedRule).where(ExpectedRule.rule_version_id == base.id, col(ExpectedRule.is_active).is_(True))
    ):
        copy = ExpectedRule(
            rule_version_id=clone.id,
            code_pattern=original.code_pattern,
            expected_evidence_spec=original.expected_evidence_spec,
        )
        session.add(copy)
        mapping[original.id] = copy
    session.flush()
    return clone, mapping


def evaluate_rule_update(session: Session, principal: Principal, update_id: uuid.UUID) -> RuleUpdate:
    update = _get_update(session, update_id)
    _update_step(RuleUpdateStatus(update.status), RuleUpdateStatus.EVALUATING)
    base, _, vector, _ = get_rule_version(session, update.base_rule_version_id)
    policy = active_policy(session)
    if policy is None:
        raise conflict("no_active_policy", "Tidak ada policy version aktif untuk evaluasi")
    change = update.proposed_change
    candidate, mapping = _clone_rule_version(
        session,
        base,
        version=f"{base.version}+upd-{str(update.id)[:8]}",
        created_by=update.proposed_by,
        validation_status=RuleValidation.UNVALIDATED.value,
    )
    target = mapping.get(uuid.UUID(change["expected_rule_id"]))
    if target is None:
        raise not_found("Expected rule pada versi dasar")
    target.expected_evidence_spec = _merge_spec(target.expected_evidence_spec, change["spec_patch"])
    session.add(target)
    session.flush()

    policy_rules = policy_views(session, policy)
    cases = tuple(c for c in CASES if c.vector == vector.code)
    baseline = evaluate(rule_views(session, base, vector), policy_rules, cases)
    proposed = evaluate(rule_views(session, candidate, vector), policy_rules, cases)
    report = compare_reports(baseline, proposed)
    report["vector"] = vector.code
    report["candidate_rule_version_id"] = str(candidate.id)

    _update_step(RuleUpdateStatus.EVALUATING, RuleUpdateStatus.EVALUATED)
    update.result_rule_version_id = candidate.id
    update.evaluation = report
    update.evaluated_at = utcnow()
    update.status = RuleUpdateStatus.EVALUATED.value
    session.add(update)
    _audit(session, principal, "rule_update", update.id, "rule_update.evaluated",
           {"regression_count": report["regression_count"], "improvement_count": report["improvement_count"],
            "candidate_rule_version_id": candidate.id})
    session.commit()
    return update


def decide_rule_update(
    session: Session,
    principal: Principal,
    update_id: uuid.UUID,
    *,
    approve: bool,
    validation_status: str | None,
    expert_validation_confirmed: bool,
    note: str | None,
) -> RuleUpdate:
    update = _get_update(session, update_id)
    target_status = RuleUpdateStatus.APPROVED if approve else RuleUpdateStatus.REJECTED
    _update_step(RuleUpdateStatus(update.status), target_status)
    _separation_of_duties(update.proposed_by, principal, "Usulan pembaruan aturan")
    now = utcnow()
    candidate = (
        _lock_version(session, update.result_rule_version_id) if update.result_rule_version_id else None
    )
    if approve:
        evaluation = update.evaluation or {}
        if evaluation.get("regression_count", 1) != 0:
            raise conflict(
                "regression_detected",
                "Evaluasi offline menemukan regresi sehingga usulan tidak dapat disetujui",
                {"regressions": evaluation.get("regressions", [])},
            )
        assert candidate is not None
        base = session.get(RuleVersion, update.base_rule_version_id)
        assert base is not None
        default_validation = (
            RuleValidation.SIMULATION.value
            if base.validation_status == RuleValidation.SIMULATION.value
            else RuleValidation.UNVALIDATED.value
        )
        chosen = validation_status or default_validation
        if chosen not in {v.value for v in RuleValidation}:
            raise unprocessable("unknown_validation_status", "Status validasi tidak dikenal")
        if chosen == RuleValidation.SIMULATION.value and base.validation_status != RuleValidation.SIMULATION.value:
            raise unprocessable("simulation_not_inherited", "Status simulasi hanya untuk turunan aturan simulasi")
        if chosen == RuleValidation.EXPERT_VALIDATED.value and not (
            expert_validation_confirmed and len((note or "").strip()) >= MIN_NOTE_LENGTH
        ):
            raise unprocessable(
                "expert_validation_unconfirmed",
                "Status tervalidasi_pakar memerlukan konfirmasi eksplisit dan catatan dasar validasi",
            )
        candidate.status = VersionStatus.APPROVED.value
        candidate.validation_status = chosen
        candidate.submitted_at = now
        candidate.approved_by = principal.user_id
        candidate.approved_at = now
        session.add(candidate)
    elif candidate is not None and candidate.status == VersionStatus.DRAFT.value:
        candidate.status = VersionStatus.REJECTED.value
        session.add(candidate)
    update.status = target_status.value
    update.decided_by = principal.user_id
    update.decided_at = now
    session.add(update)
    _audit(session, principal, "rule_update", update.id,
           "rule_update.approved" if approve else "rule_update.rejected",
           {"note": (note or "").strip() or None})
    session.commit()
    return update


def activate_rule_update(session: Session, principal: Principal, update_id: uuid.UUID) -> RuleUpdate:
    update = _get_update(session, update_id)
    _update_step(RuleUpdateStatus(update.status), RuleUpdateStatus.ACTIVATED)
    assert update.result_rule_version_id is not None
    candidate = _lock_version(session, update.result_rule_version_id)
    _step("versi aturan", VersionStatus(candidate.status), VersionStatus.ACTIVE)
    retired = _retire_active(session, candidate.rule_set_id, principal)
    candidate.status = VersionStatus.ACTIVE.value
    candidate.activated_at = utcnow()
    session.add(candidate)
    update.status = RuleUpdateStatus.ACTIVATED.value
    session.add(update)
    basis = list(session.exec(select(RuleUpdateBasis.verdict_id).where(RuleUpdateBasis.rule_update_id == update.id)))
    _audit(session, principal, "rule_update", update.id, "rule_update.activated",
           {"rule_version_id": candidate.id, "retired": retired, "basis_verdict_ids": basis})
    session.commit()
    return update


def rollback_rule_update(session: Session, principal: Principal, update_id: uuid.UUID) -> RuleUpdate:
    update = _get_update(session, update_id)
    _update_step(RuleUpdateStatus(update.status), RuleUpdateStatus.ROLLED_BACK)
    base = session.get(RuleVersion, update.base_rule_version_id)
    assert base is not None and update.result_rule_version_id is not None
    candidate = _lock_version(session, update.result_rule_version_id)
    now = utcnow()
    if candidate.status == VersionStatus.ACTIVE.value:
        candidate.status = VersionStatus.RETIRED.value
        candidate.retired_at = now
        session.add(candidate)
        session.flush()
    existing = session.exec(
        select(func.count()).select_from(RuleVersion).where(
            RuleVersion.rule_set_id == base.rule_set_id, col(RuleVersion.version).like(f"{base.version}-rb%")
        )
    ).one()
    restored, _ = _clone_rule_version(
        session,
        base,
        version=f"{base.version}-rb{existing + 1}",
        created_by=None,
        validation_status=base.validation_status,
    )
    restored.status = VersionStatus.ACTIVE.value
    restored.approved_by = principal.user_id
    restored.approved_at = now
    restored.activated_at = now
    session.add(restored)
    update.status = RuleUpdateStatus.ROLLED_BACK.value
    session.add(update)
    _audit(session, principal, "rule_update", update.id, "rule_update.rolled_back",
           {"restored_rule_version_id": restored.id, "retired_rule_version_id": candidate.id})
    session.commit()
    return update


def list_rule_updates(session: Session, principal: Principal) -> list[RuleUpdate]:
    query = select(RuleUpdate).order_by(col(RuleUpdate.created_at).desc())
    if not (principal.can(Permission.RULE_APPROVE) or principal.can(Permission.RULE_WRITE)):
        query = (
            query.join(HumanVerdict, col(HumanVerdict.id) == col(RuleUpdate.verdict_id))
            .join(Intervention, col(Intervention.id) == col(HumanVerdict.intervention_id))
            .where(Intervention.faskes_id == principal.faskes_id)
        )
    return list(session.exec(query))


def get_rule_update(
    session: Session, principal: Principal, update_id: uuid.UUID
) -> tuple[RuleUpdate, list[uuid.UUID]]:
    update = session.get(RuleUpdate, update_id)
    if update is None:
        raise not_found("Usulan pembaruan aturan")
    if not (principal.can(Permission.RULE_APPROVE) or principal.can(Permission.RULE_WRITE)):
        owner = session.exec(
            select(Intervention.faskes_id)
            .join(HumanVerdict, col(HumanVerdict.intervention_id) == col(Intervention.id))
            .where(HumanVerdict.id == update.verdict_id)
        ).first()
        if owner != principal.faskes_id:
            raise not_found("Usulan pembaruan aturan")
    basis = list(session.exec(select(RuleUpdateBasis.verdict_id).where(RuleUpdateBasis.rule_update_id == update.id)))
    return update, basis
