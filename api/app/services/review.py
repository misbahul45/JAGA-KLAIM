import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.core.errors import conflict, not_found, unprocessable
from app.domain.enums import ClaimStatus, FollowUp, Verdict
from app.domain.permissions import Permission
from app.models import (
    Claim,
    ClaimCode,
    CognitiveAssessment,
    EvidenceCitation,
    EvidenceItem,
    EvidenceSource,
    Finding,
    HumanVerdict,
    Intervention,
    InvestigationRun,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleVersion,
)
from app.models.base import utcnow
from app.services import audit
from app.services.auth import Principal
from app.services.claim_state import REVIEW_TIERS, sync_claim_status

MIN_RATIONALE_LENGTH = 10
MAX_TEXT_LENGTH = 2000


@dataclass(frozen=True)
class QueueRow:
    intervention: Intervention
    claim: Claim
    run: InvestigationRun
    vector_code: str
    assessed: bool


@dataclass(frozen=True)
class InterventionDetail:
    intervention: Intervention
    claim: Claim
    run: InvestigationRun
    vector_code: str
    rule_version_label: str
    rule_validation_status: str
    policy_version_label: str
    codes: list[ClaimCode]
    evidence: list[tuple[EvidenceItem, EvidenceSource]]
    gate_required: bool
    revealed: bool
    finding: Finding | None
    citations: list[EvidenceCitation]
    own_assessment: CognitiveAssessment | None
    verdicts: list[HumanVerdict]
    stale: bool
    evidence_updated_after_run: bool


def _assessed_ids(session: Session, principal: Principal, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not ids:
        return set()
    return set(
        session.exec(
            select(CognitiveAssessment.intervention_id).where(
                col(CognitiveAssessment.intervention_id).in_(ids),
                CognitiveAssessment.verifier_id == principal.user_id,
            )
        )
    )


def list_queue(
    session: Session,
    principal: Principal,
    *,
    tiers: list[str],
    state: str,
    vector: str | None,
    page: int,
    page_size: int,
) -> tuple[list[QueueRow], int]:
    conditions: list[ColumnElement[bool]] = [
        col(Intervention.faskes_id) == principal.faskes_id,
        col(Intervention.tier).in_(tiers),
        col(InvestigationRun.stale_at).is_(None),
        col(InvestigationRun.claim_version) == col(Claim.version),
    ]
    if state == "open":
        conditions.append(col(Intervention.resolved_at).is_(None))
    elif state == "resolved":
        conditions.append(col(Intervention.resolved_at).is_not(None))
    if vector:
        conditions.append(col(RiskVector.code) == vector)

    statement = (
        select(Intervention, Claim, InvestigationRun, RiskVector.code)
        .select_from(Intervention)
        .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
        .join(Claim, col(Claim.id) == col(InvestigationRun.claim_id))
        .join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(*conditions)
    )
    total = session.execute(
        statement.with_only_columns(func.count(), maintain_column_froms=True)
    ).scalar_one()
    rows = session.exec(
        statement.order_by(
            col(Intervention.tier).desc(), col(Intervention.created_at), col(Intervention.id)
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    assessed = _assessed_ids(session, principal, [r[0].id for r in rows])
    return (
        [QueueRow(i, c, r, v, i.id in assessed) for i, c, r, v in rows],
        total,
    )


def _get_intervention(
    session: Session, principal: Principal, intervention_id: uuid.UUID, *, for_update: bool = False
) -> Intervention:
    query = select(Intervention).where(
        Intervention.id == intervention_id, Intervention.faskes_id == principal.faskes_id
    )
    if for_update:
        query = query.with_for_update()
    intervention = session.exec(query).first()
    if intervention is None:
        raise not_found("Intervensi")
    return intervention


def _own_assessment(
    session: Session, principal: Principal, intervention_id: uuid.UUID
) -> CognitiveAssessment | None:
    return session.exec(
        select(CognitiveAssessment).where(
            CognitiveAssessment.intervention_id == intervention_id,
            CognitiveAssessment.verifier_id == principal.user_id,
        )
    ).first()


def _gate_required(principal: Principal, intervention: Intervention) -> bool:
    return intervention.tier in REVIEW_TIERS and principal.can(Permission.REVIEW_ASSESS)


def _current_verdict(session: Session, intervention_id: uuid.UUID) -> HumanVerdict | None:
    superseded = (
        select(HumanVerdict.supersedes_verdict_id)
        .where(col(HumanVerdict.supersedes_verdict_id).is_not(None))
        .scalar_subquery()
    )
    return session.exec(
        select(HumanVerdict).where(
            HumanVerdict.intervention_id == intervention_id,
            col(HumanVerdict.id).not_in(superseded),
        )
    ).first()


def intervention_detail(
    session: Session, principal: Principal, intervention_id: uuid.UUID
) -> InterventionDetail:
    intervention = _get_intervention(session, principal, intervention_id)
    run = session.get(InvestigationRun, intervention.run_id)
    assert run is not None
    claim = session.get(Claim, run.claim_id)
    assert claim is not None
    vector_code, rule_label, rule_validation = session.exec(
        select(RiskVector.code, RuleVersion.version, RuleVersion.validation_status)
        .join(RuleSet, col(RuleSet.vector_id) == col(RiskVector.id))
        .join(RuleVersion, col(RuleVersion.rule_set_id) == col(RuleSet.id))
        .where(RuleVersion.id == run.rule_version_id)
    ).one()
    policy = session.get(PolicyVersion, run.policy_version_id)
    assert policy is not None

    own = _own_assessment(session, principal, intervention.id)
    gate = _gate_required(principal, intervention)
    revealed = (not gate) or own is not None

    evidence = list(
        session.exec(
            select(EvidenceItem, EvidenceSource)
            .join(EvidenceSource, col(EvidenceSource.id) == col(EvidenceItem.source_id))
            .where(EvidenceItem.claim_id == claim.id, EvidenceItem.faskes_id == principal.faskes_id)
            .order_by(col(EvidenceItem.recorded_at))
        ).all()
    )
    codes = list(
        session.exec(
            select(ClaimCode)
            .where(ClaimCode.claim_id == claim.id, col(ClaimCode.superseded_at).is_(None))
            .order_by(col(ClaimCode.created_at))
        )
    )
    finding: Finding | None = None
    citations: list[EvidenceCitation] = []
    verdicts: list[HumanVerdict] = []
    if revealed:
        if intervention.finding_id:
            finding = session.get(Finding, intervention.finding_id)
            citations = list(
                session.exec(
                    select(EvidenceCitation)
                    .where(EvidenceCitation.finding_id == intervention.finding_id)
                    .order_by(col(EvidenceCitation.cited_at))
                )
            )
        verdicts = list(
            session.exec(
                select(HumanVerdict)
                .where(HumanVerdict.intervention_id == intervention.id)
                .order_by(col(HumanVerdict.created_at))
            )
        )
    latest_evidence = max((e.created_at for e, _ in evidence), default=None)
    return InterventionDetail(
        intervention=intervention,
        claim=claim,
        run=run,
        vector_code=vector_code,
        rule_version_label=rule_label,
        rule_validation_status=rule_validation,
        policy_version_label=policy.version,
        codes=codes,
        evidence=evidence,
        gate_required=gate,
        revealed=revealed,
        finding=finding,
        citations=citations,
        own_assessment=own,
        verdicts=verdicts,
        stale=run.stale_at is not None or run.claim_version != claim.version,
        evidence_updated_after_run=latest_evidence is not None and latest_evidence > run.started_at,
    )


def _ensure_actionable(session: Session, intervention: Intervention) -> tuple[InvestigationRun, Claim]:
    if intervention.tier not in REVIEW_TIERS:
        raise unprocessable(
            "review_not_required",
            "Hanya intervensi T2 dan T3 yang memerlukan penilaian dan verdict",
        )
    run = session.get(InvestigationRun, intervention.run_id)
    assert run is not None
    claim = session.exec(select(Claim).where(Claim.id == run.claim_id).with_for_update()).one()
    if claim.status == ClaimStatus.LOCKED.value:
        raise conflict("claim_locked", "Klaim sudah dikunci")
    if run.stale_at is not None or run.claim_version != claim.version:
        raise conflict(
            "stale_result",
            "Hasil pemeriksaan ini sudah tidak berlaku karena klaim berubah atau diperiksa ulang",
        )
    return run, claim


def _clean_text(value: str | None, *, required: bool, minimum: int = 0) -> str | None:
    text = (value or "").strip()
    if required and len(text) < minimum:
        raise unprocessable(
            "text_too_short", f"Teks wajib diisi minimal {minimum} karakter", {"minimum": minimum}
        )
    if len(text) > MAX_TEXT_LENGTH:
        raise unprocessable("text_too_long", f"Teks maksimal {MAX_TEXT_LENGTH} karakter")
    return text or None


def submit_assessment(
    session: Session,
    principal: Principal,
    intervention_id: uuid.UUID,
    *,
    self_verdict: Verdict,
    note: str | None,
) -> CognitiveAssessment:
    intervention = _get_intervention(session, principal, intervention_id, for_update=True)
    _ensure_actionable(session, intervention)
    if intervention.resolved_at is not None:
        raise conflict("verdict_exists", "Verdict untuk intervensi ini sudah dicatat")
    if _own_assessment(session, principal, intervention.id) is not None:
        raise conflict("assessment_exists", "Penilaian mandiri Anda sudah tersimpan dan tidak dapat diubah")
    assessment = CognitiveAssessment(
        intervention_id=intervention.id,
        verifier_id=principal.user_id,
        self_verdict=self_verdict.value,
        self_note=_clean_text(note, required=False),
    )
    session.add(assessment)
    session.flush()
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="intervention",
        entity_id=intervention.id,
        event_type="review.assessment_submitted",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"tier": intervention.tier, "self_verdict": self_verdict.value, "assessment_id": assessment.id},
    )
    session.commit()
    return assessment


def submit_verdict(
    session: Session,
    principal: Principal,
    intervention_id: uuid.UUID,
    *,
    verdict: Verdict,
    follow_up: FollowUp,
    rationale: str,
) -> HumanVerdict:
    intervention = _get_intervention(session, principal, intervention_id, for_update=True)
    run, claim = _ensure_actionable(session, intervention)
    if intervention.resolved_at is not None:
        raise conflict(
            "verdict_exists",
            "Verdict sudah dicatat. Gunakan koreksi verdict untuk mengubahnya.",
        )
    assessment = _own_assessment(session, principal, intervention.id)
    if assessment is None:
        raise conflict(
            "assessment_required",
            "Simpan penilaian mandiri Anda terlebih dahulu sebelum mencatat verdict",
        )
    now = utcnow()
    record = HumanVerdict(
        intervention_id=intervention.id,
        verifier_id=principal.user_id,
        assessment_id=assessment.id,
        verdict=verdict.value,
        follow_up=follow_up.value,
        rationale=_clean_text(rationale, required=True, minimum=MIN_RATIONALE_LENGTH),
        time_to_decision_ms=int((now - intervention.created_at).total_seconds() * 1000),
    )
    session.add(record)
    intervention.resolved_at = now
    session.add(intervention)
    session.flush()
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="intervention",
        entity_id=intervention.id,
        event_type="review.verdict_recorded",
        actor_type="user",
        actor_id=principal.user_id,
        payload={
            "tier": intervention.tier,
            "verdict": verdict.value,
            "follow_up": follow_up.value,
            "verdict_id": record.id,
            "assessment_id": assessment.id,
            "rule_version_id": run.rule_version_id,
            "policy_version_id": run.policy_version_id,
        },
    )
    sync_claim_status(
        session, claim, actor_type="user", actor_id=principal.user_id, reason="verdict dicatat"
    )
    session.commit()
    return record


def correct_verdict(
    session: Session,
    principal: Principal,
    intervention_id: uuid.UUID,
    *,
    verdict: Verdict,
    follow_up: FollowUp,
    rationale: str,
) -> HumanVerdict:
    intervention = _get_intervention(session, principal, intervention_id, for_update=True)
    run, claim = _ensure_actionable(session, intervention)
    previous = _current_verdict(session, intervention.id)
    if previous is None:
        raise conflict("no_verdict_to_correct", "Belum ada verdict yang dapat dikoreksi")
    record = HumanVerdict(
        intervention_id=intervention.id,
        verifier_id=principal.user_id,
        assessment_id=previous.assessment_id,
        supersedes_verdict_id=previous.id,
        verdict=verdict.value,
        follow_up=follow_up.value,
        rationale=_clean_text(rationale, required=True, minimum=MIN_RATIONALE_LENGTH),
        time_to_decision_ms=previous.time_to_decision_ms,
    )
    session.add(record)
    session.flush()
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="intervention",
        entity_id=intervention.id,
        event_type="review.verdict_corrected",
        actor_type="user",
        actor_id=principal.user_id,
        payload={
            "verdict": verdict.value,
            "follow_up": follow_up.value,
            "verdict_id": record.id,
            "supersedes_verdict_id": previous.id,
            "previous_verdict": previous.verdict,
            "run_id": run.id,
        },
    )
    sync_claim_status(
        session, claim, actor_type="user", actor_id=principal.user_id, reason="verdict dikoreksi"
    )
    session.commit()
    return record
