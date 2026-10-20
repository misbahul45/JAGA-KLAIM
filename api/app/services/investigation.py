import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.core.errors import conflict
from app.domain.assessment import Assessed, abstained, assess, outcome_of, surfaced
from app.domain.citations import EvidenceRecord
from app.domain.comparator import (
    ClaimView,
    CodeView,
    EvidenceView,
    RuleView,
    SourceView,
)
from app.domain.enums import (
    CitationValidation,
    FindingStatus,
    JobEvent,
    JobStatus,
    RunStatus,
    Tier,
    VersionStatus,
)
from app.domain.policy import PolicyRuleView
from app.domain.specs import ExpectedEvidenceSpec
from app.domain.states import JOB_TRANSITIONS, ensure_transition
from app.domain.synthesis import (
    ALLOWED_ACTIONS,
    Synthesizer,
    TemplateSynthesizer,
)
from app.domain.tools import StepRecorder
from app.models import (
    AgentStep,
    Claim,
    ClaimCode,
    EvidenceCitation,
    EvidenceItem,
    EvidenceSource,
    ExpectedRule,
    Finding,
    Intervention,
    InvestigationJob,
    InvestigationRun,
    PolicyRule,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleVersion,
)
from app.models.base import SQLModel, utcnow
from app.services import audit
from app.services.claim_state import sync_claim_status

JOB_TABLE = SQLModel.metadata.tables[InvestigationJob.__tablename__]

ENGINE_NAME = "deterministic-comparator"
ENGINE_VERSION = "1.0.0"
PROMPT_VERSION = "none"
MAX_ERROR_LENGTH = 300

T0_MESSAGES: dict[str, str] = {
    "T0_COVERAGE_INADEQUATE": "cakupan sumber bukti belum memadai",
    "T0_UNRESOLVED_CONFLICT": "bukti pendukung dan bukti yang bertentangan sama-sama ada dan belum terselesaikan",
    "T0_CITATION_UNVERIFIED": "sitasi bukti yang valid tidak tersedia untuk ketidaksesuaian yang terdeteksi",
}


class InvestigationConfigError(Exception):
    pass


@dataclass
class JobContext:
    claim: Claim
    claim_view: ClaimView
    evidence: list[EvidenceView]
    sources: list[SourceView]


def get_job_by_key(session: Session, faskes_id: uuid.UUID, key: str) -> InvestigationJob | None:
    return session.exec(
        select(InvestigationJob).where(
            InvestigationJob.faskes_id == faskes_id, InvestigationJob.idempotency_key == key
        )
    ).first()


def enqueue_job(
    session: Session,
    claim: Claim,
    *,
    event: JobEvent,
    idempotency_key: str,
    requested_by: uuid.UUID | None,
    reason: str | None = None,
) -> tuple[InvestigationJob, bool]:
    statement = (
        pg_insert(JOB_TABLE)
        .values(
            id=uuid.uuid4(),
            faskes_id=claim.faskes_id,
            claim_id=claim.id,
            claim_version=claim.version,
            event_type=event.value,
            status=JobStatus.QUEUED.value,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
            reason=reason,
        )
        .on_conflict_do_nothing(index_elements=["faskes_id", "idempotency_key"])
        .returning(JOB_TABLE.c.id)
    )
    inserted = session.execute(statement).scalar_one_or_none()
    if inserted is None:
        existing = get_job_by_key(session, claim.faskes_id, idempotency_key)
        assert existing is not None
        if existing.claim_id != claim.id or existing.event_type != event.value:
            raise conflict(
                "idempotency_key_conflict",
                "Idempotency-Key ini sudah dipakai untuk permintaan lain",
            )
        return existing, False
    job = session.get(InvestigationJob, inserted)
    assert job is not None
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="investigation_job",
        entity_id=job.id,
        event_type="investigation.job_queued",
        actor_type="user" if requested_by else "system",
        actor_id=requested_by,
        payload={"claim_id": claim.id, "event": event.value, "claim_version": claim.version},
    )
    return job, True


def active_policy(session: Session) -> PolicyVersion | None:
    return session.exec(
        select(PolicyVersion).where(PolicyVersion.status == VersionStatus.ACTIVE.value)
    ).first()


def active_rule_versions(session: Session) -> list[tuple[RuleVersion, RiskVector]]:
    rows = session.exec(
        select(RuleVersion, RiskVector)
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(
            RuleVersion.status == VersionStatus.ACTIVE.value,
            col(RiskVector.is_active).is_(True),
        )
        .order_by(col(RiskVector.code))
    )
    return list(rows)


def load_context(session: Session, claim: Claim) -> JobContext:
    codes = session.exec(
        select(ClaimCode).where(
            ClaimCode.claim_id == claim.id, col(ClaimCode.superseded_at).is_(None)
        )
    ).all()
    sources = session.exec(
        select(EvidenceSource).where(EvidenceSource.faskes_id == claim.faskes_id)
    ).all()
    source_types = {s.id: s.source_type for s in sources}
    items = session.exec(
        select(EvidenceItem).where(
            EvidenceItem.claim_id == claim.id, EvidenceItem.faskes_id == claim.faskes_id
        )
    ).all()
    evidence = [
        EvidenceView(
            id=i.id,
            source_id=i.source_id,
            source_type=source_types.get(i.source_id, "tidak_dikenal"),
            recorded_at=i.recorded_at,
            kind=(i.content_ref or {}).get("kind", "lainnya"),
            assertion=(i.content_ref or {}).get("assertion", "supports"),
            text=i.content_text or "",
            content_hash=i.content_hash,
            quarantined=i.injection_suspected,
        )
        for i in items
    ]
    return JobContext(
        claim=claim,
        claim_view=ClaimView(
            id=claim.id,
            episode_start=claim.episode_start,
            episode_end=claim.episode_end,
            codes=tuple(CodeView(c.id, c.code_type, c.code, c.position) for c in codes),
        ),
        evidence=evidence,
        sources=[
            SourceView(
                id=s.id,
                source_type=s.source_type,
                system_ref=s.system_ref,
                is_enabled=s.is_enabled,
                health_status=s.health_status,
                last_synced_at=s.last_synced_at,
                freshness_sla_seconds=s.freshness_sla_seconds,
            )
            for s in sources
        ],
    )


def rule_views(session: Session, rule_version: RuleVersion, vector: RiskVector) -> list[RuleView]:
    views: list[RuleView] = []
    expected = session.exec(
        select(ExpectedRule).where(
            ExpectedRule.rule_version_id == rule_version.id, col(ExpectedRule.is_active).is_(True)
        )
    )
    for rule in expected:
        try:
            spec = ExpectedEvidenceSpec.model_validate(rule.expected_evidence_spec)
        except ValidationError as exc:
            raise InvestigationConfigError(
                f"spesifikasi bukti pada aturan {rule.id} tidak valid ({exc.error_count()} galat)"
            ) from exc
        views.append(
            RuleView(
                id=rule.id,
                rule_version_id=rule_version.id,
                vector_code=vector.code,
                code_pattern=rule.code_pattern,
                spec=spec,
                validation_status=rule_version.validation_status,
            )
        )
    return views


def policy_views(session: Session, policy: PolicyVersion) -> list[PolicyRuleView]:
    return [
        PolicyRuleView(
            id=r.id,
            code=r.code,
            tier=Tier(r.tier),
            priority=r.priority,
            condition=r.condition_spec,
            is_active=r.is_active,
        )
        for r in session.exec(select(PolicyRule).where(PolicyRule.policy_version_id == policy.id))
    ]


def _rule_for_tier(rules: list[PolicyRuleView], tier: Tier) -> PolicyRuleView:
    candidates = sorted((r for r in rules if r.tier is tier and r.is_active), key=lambda r: r.priority)
    if not candidates:
        raise InvestigationConfigError(f"kebijakan aktif tidak punya aturan untuk tier {tier.value}")
    return candidates[0]


def _t0_reason(assessed: Assessed) -> str:
    code = assessed.comparison.code.code
    rule_code = assessed.decision.rule_code if assessed.decision else "SAFETY_GOVERNOR"
    message = T0_MESSAGES.get(rule_code)
    if message is None and assessed.governor_reasons:
        message = "; ".join(assessed.governor_reasons)
    message = message or f"aturan kebijakan {rule_code} menetapkan abstain"
    gaps = assessed.comparison.coverage_gaps[:3]
    suffix = f" ({'; '.join(gaps)})" if gaps else ""
    return f"{code}: {message}{suffix}"


def _source_report(sources: list[SourceView]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": str(s.id),
            "source_type": s.source_type,
            "system_ref": s.system_ref,
            "enabled": s.is_enabled,
            "health_status": s.health_status,
            "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None,
        }
        for s in sources
    ]


def _evidence_records(session: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, EvidenceRecord]:
    if not ids:
        return {}
    rows = session.exec(select(EvidenceItem).where(col(EvidenceItem.id).in_(ids)))
    return {
        r.id: EvidenceRecord(r.id, r.faskes_id, r.claim_id, r.content_text or "", r.content_hash)
        for r in rows
    }


def _previous_runs(session: Session, claim: Claim, vector: RiskVector) -> list[InvestigationRun]:
    return list(
        session.exec(
            select(InvestigationRun)
            .join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
            .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
            .where(
                InvestigationRun.claim_id == claim.id,
                RuleSet.vector_id == vector.id,
                InvestigationRun.status != RunStatus.FAILED.value,
            )
            .order_by(col(InvestigationRun.started_at).desc())
        )
    )


def execute_run(
    session: Session,
    *,
    job: InvestigationJob,
    ctx: JobContext,
    rule_version: RuleVersion,
    vector: RiskVector,
    policy: PolicyVersion,
    now: datetime,
    synthesizer: Synthesizer,
) -> InvestigationRun:
    claim = ctx.claim
    started_at = utcnow()
    recorder = StepRecorder()

    rules = recorder.run(
        "context_build",
        "load_claim_context",
        lambda: rule_views(session, rule_version, vector),
        summarize=lambda r: {
            "vector": vector.code,
            "rules": len(r),
            "codes": len(ctx.claim_view.codes),
            "evidence_items": len(ctx.evidence),
            "sources": len(ctx.sources),
        },
    )
    policy_rules = policy_views(session, policy)

    recorder.run(
        "source_check",
        "check_source_coverage",
        lambda: _source_report(ctx.sources),
        summarize=lambda r: {
            "sources": len(r),
            "healthy": sum(1 for s in r if s["health_status"] == "healthy"),
        },
    )
    recorder.run(
        "retrieval",
        "search_claim_evidence",
        lambda: ctx.evidence,
        summarize=lambda e: {
            "items": len(e),
            "quarantined": sum(1 for i in e if i.quarantined),
        },
    )
    assessed = assess(
        faskes_id=claim.faskes_id,
        claim=ctx.claim_view,
        rules=rules,
        policy_rules=policy_rules,
        evidence=ctx.evidence,
        sources=ctx.sources,
        now=now,
        records_provider=lambda ids: _evidence_records(session, ids),
        synthesizer=synthesizer,
        recorder=recorder,
    )
    findings_items = surfaced(assessed)
    abstained_items = abstained(assessed)
    outcome = outcome_of(assessed)
    status = RunStatus.PARTIAL if abstained_items else RunStatus.SUCCEEDED
    abstain_reason = "; ".join(_t0_reason(a) for a in abstained_items) if abstained_items else None

    previous = _previous_runs(session, claim, vector)
    run = InvestigationRun(
        faskes_id=claim.faskes_id,
        claim_id=claim.id,
        claim_version=claim.version,
        job_id=job.id,
        rerun_of_run_id=previous[0].id if previous else None,
        rule_version_id=rule_version.id,
        policy_version_id=policy.id,
        trigger=job.event_type,
        status=status.value,
        outcome=outcome.value,
        abstain_reason=abstain_reason,
        coverage={
            "sources": _source_report(ctx.sources),
            "comparisons": [
                {
                    "code": a.comparison.code.code,
                    "gaps": a.comparison.coverage_gaps,
                    "quarantined": sum(len(o.quarantined_ids) for o in a.comparison.unmet),
                }
                for a in assessed
                if a.comparison.coverage_gaps
            ],
        },
        model_name=ENGINE_NAME,
        model_version=ENGINE_VERSION,
        prompt_version=PROMPT_VERSION,
        started_at=started_at,
        finished_at=utcnow(),
    )
    session.add(run)
    session.flush()

    for old in previous:
        if old.stale_at is None:
            old.stale_at = now
            session.add(old)

    for step in recorder.steps:
        session.add(
            AgentStep(
                run_id=run.id,
                seq=step.seq,
                step_type=step.step_type,
                tool_name=step.tool_name,
                query=step.query,
                source_id=step.source_id,
                status=step.status.value,
                result_ref=step.result_ref,
                latency_ms=step.latency_ms,
                error_message=step.error_message,
            )
        )

    claim_code_ids = {c.code: c.id for c in ctx.claim_view.codes}
    tier_counts: dict[str, int] = {}

    for item in findings_items:
        assert item.synthesized is not None and item.decision is not None and item.final_tier
        cmp = item.comparison
        valid_count = len(item.valid_citations)
        finding = Finding(
            faskes_id=claim.faskes_id,
            run_id=run.id,
            vector_id=vector.id,
            claim_code_id=claim_code_ids.get(cmp.code.code),
            status=FindingStatus.VALID.value if valid_count else FindingStatus.DOWNGRADED.value,
            mismatch_desc=item.synthesized.mismatch_desc,
            confidence=item.facts["missing_ratio"],
            delta={
                "check": cmp.check.value,
                "code": cmp.code.code,
                "rule_id": str(cmp.rule.id),
                "rule_validation": cmp.rule.validation_status,
                "expected": [
                    {"requirement_id": o.requirement.id, "label": o.requirement.label, "min_count": o.requirement.min_count}
                    for o in cmp.outcomes
                ],
                "observed": [
                    {
                        "requirement_id": o.requirement.id,
                        "satisfied": o.satisfied,
                        "supporting_evidence_ids": [str(i) for i in o.supporting_ids],
                        "out_of_window_evidence_ids": [str(i) for i in o.out_of_window_ids],
                    }
                    for o in cmp.outcomes
                ],
                "missing": [o.requirement.id for o in cmp.unmet],
                "contradicting_evidence_ids": [str(i) for o in cmp.unmet for i in o.negating_ids],
                "conflicting_codes": [c.code for c in cmp.conflicting_codes],
                "coverage_gaps": cmp.coverage_gaps,
                "limitations": item.synthesized.limitations,
                "proposed_actions": [
                    {"code": a, "label": ALLOWED_ACTIONS[a]} for a in item.synthesized.proposed_actions
                ],
                "safety_flags": item.synthesized.safety_flags,
                "governor_reasons": item.governor_reasons,
                "signal_strength": item.facts["missing_ratio"],
            },
        )
        session.add(finding)
        session.flush()
        for verdict in item.verdicts:
            candidate = verdict.citation
            session.add(
                EvidenceCitation(
                    finding_id=finding.id,
                    evidence_item_id=candidate.evidence_item_id,
                    quote_span={
                        "start": candidate.start,
                        "end": candidate.end,
                        "quote": candidate.quote,
                        "role": candidate.role,
                        "invalid_reason": verdict.reason,
                    },
                    evidence_hash=candidate.evidence_hash,
                    validation_status=(
                        CitationValidation.VALID.value if verdict.valid else CitationValidation.INVALID.value
                    ),
                )
            )
        if item.final_tier is item.decision.tier:
            rule_view = next(r for r in policy_rules if r.id == item.decision.rule_id)
            ref = item.decision.rule_code
        else:
            rule_view = _rule_for_tier(policy_rules, item.final_tier)
            ref = f"safety_governor<-{item.decision.rule_code}"
        intervention = Intervention(
            faskes_id=claim.faskes_id,
            run_id=run.id,
            finding_id=finding.id,
            policy_rule_id=rule_view.id,
            tier=item.final_tier.value,
            policy_rule_ref=ref,
        )
        session.add(intervention)
        session.flush()
        tier_counts[item.final_tier.value] = tier_counts.get(item.final_tier.value, 0) + 1
        audit.append_event(
            session,
            faskes_id=claim.faskes_id,
            entity_type="intervention",
            entity_id=intervention.id,
            event_type="intervention.created",
            actor_type="system",
            payload={
                "run_id": run.id,
                "tier": intervention.tier,
                "policy_rule": intervention.policy_rule_ref,
                "vector": vector.code,
                "claim_id": claim.id,
            },
        )

    if abstained_items:
        first = abstained_items[0]
        assert first.decision is not None
        if first.decision.tier is Tier.T0:
            rule_view = next(r for r in policy_rules if r.id == first.decision.rule_id)
            ref = rule_view.code
        else:
            rule_view = _rule_for_tier(policy_rules, Tier.T0)
            ref = f"safety_governor<-{first.decision.rule_code}"
        intervention = Intervention(
            faskes_id=claim.faskes_id,
            run_id=run.id,
            finding_id=None,
            policy_rule_id=rule_view.id,
            tier=Tier.T0.value,
            policy_rule_ref=ref,
        )
        session.add(intervention)
        session.flush()
        tier_counts[Tier.T0.value] = len(abstained_items)
        audit.append_event(
            session,
            faskes_id=claim.faskes_id,
            entity_type="intervention",
            entity_id=intervention.id,
            event_type="intervention.created",
            actor_type="system",
            payload={
                "run_id": run.id,
                "tier": Tier.T0.value,
                "policy_rule": ref,
                "vector": vector.code,
                "claim_id": claim.id,
            },
        )

    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="investigation_run",
        entity_id=run.id,
        event_type="investigation.run_completed",
        actor_type="system",
        payload={
            "claim_id": claim.id,
            "job_id": job.id,
            "vector": vector.code,
            "status": run.status,
            "outcome": run.outcome,
            "tiers": tier_counts,
            "rule_version_id": rule_version.id,
            "policy_version_id": policy.id,
            "rerun_of_run_id": run.rerun_of_run_id,
        },
    )
    session.flush()
    return run


def _record_failed_run(
    session: Session,
    *,
    job: InvestigationJob,
    claim: Claim,
    rule_version: RuleVersion,
    policy: PolicyVersion,
    error: str,
) -> InvestigationRun:
    run = InvestigationRun(
        faskes_id=claim.faskes_id,
        claim_id=claim.id,
        claim_version=claim.version,
        job_id=job.id,
        rule_version_id=rule_version.id,
        policy_version_id=policy.id,
        trigger=job.event_type,
        status=RunStatus.FAILED.value,
        validation_errors={"error": error[:MAX_ERROR_LENGTH]},
        model_name=ENGINE_NAME,
        model_version=ENGINE_VERSION,
        prompt_version=PROMPT_VERSION,
        finished_at=utcnow(),
    )
    session.add(run)
    session.flush()
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="investigation_run",
        entity_id=run.id,
        event_type="investigation.run_failed",
        actor_type="system",
        payload={"claim_id": claim.id, "job_id": job.id, "error": error[:MAX_ERROR_LENGTH]},
    )
    return run


def _finish_job(session: Session, job: InvestigationJob, status: JobStatus, error: str | None) -> None:
    ensure_transition("job investigasi", JOB_TRANSITIONS, JobStatus(job.status), status)
    job.status = status.value
    job.processed_at = utcnow()
    job.error_message = error[:MAX_ERROR_LENGTH] if error else None
    job.locked_at = None
    session.add(job)
    audit.append_event(
        session,
        faskes_id=job.faskes_id,
        entity_type="investigation_job",
        entity_id=job.id,
        event_type=f"investigation.job_{status.value}",
        actor_type="system",
        payload={"claim_id": job.claim_id, "attempt": job.attempt_count},
    )


def run_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    now: datetime | None = None,
    synthesizer: Synthesizer | None = None,
) -> JobStatus:
    current = now or utcnow()
    engine_synthesizer = synthesizer or TemplateSynthesizer()
    job = session.get(InvestigationJob, job_id)
    if job is None or job.status != JobStatus.PROCESSING.value:
        raise InvestigationConfigError("job tidak dalam status processing")
    claim = session.exec(select(Claim).where(Claim.id == job.claim_id).with_for_update()).one()

    if claim.version != job.claim_version:
        _finish_job(session, job, JobStatus.STALE, "versi klaim telah berubah sebelum pemeriksaan dimulai")
        session.commit()
        return JobStatus.STALE

    policy = active_policy(session)
    rule_versions = active_rule_versions(session)
    if policy is None or not rule_versions:
        _finish_job(session, job, JobStatus.FAILED, "tidak ada rule version atau policy version aktif")
        session.commit()
        return JobStatus.FAILED

    ctx = load_context(session, claim)
    statuses: list[RunStatus] = []
    errors: list[str] = []
    for rule_version, vector in rule_versions:
        savepoint = session.begin_nested()
        try:
            run = execute_run(
                session,
                job=job,
                ctx=ctx,
                rule_version=rule_version,
                vector=vector,
                policy=policy,
                now=current,
                synthesizer=engine_synthesizer,
            )
            savepoint.commit()
            statuses.append(RunStatus(run.status))
        except Exception as exc:
            savepoint.rollback()
            message = f"{vector.code}: {exc}"
            errors.append(message)
            _record_failed_run(
                session, job=job, claim=claim, rule_version=rule_version, policy=policy, error=message
            )
            statuses.append(RunStatus.FAILED)

    if all(s is RunStatus.FAILED for s in statuses):
        final = JobStatus.FAILED
    elif any(s in (RunStatus.FAILED, RunStatus.PARTIAL) for s in statuses):
        final = JobStatus.PARTIAL
    else:
        final = JobStatus.SUCCEEDED
    _finish_job(session, job, final, "; ".join(errors) if errors else None)

    if final in (JobStatus.SUCCEEDED, JobStatus.PARTIAL):
        sync_claim_status(
            session,
            claim,
            actor_type="system",
            actor_id=None,
            reason=f"investigasi {final.value}",
        )
    session.commit()
    return final


def latest_job_for_claim(
    session: Session, claim: Claim, *, event: JobEvent | None = None
) -> InvestigationJob | None:
    query = select(InvestigationJob).where(
        InvestigationJob.claim_id == claim.id, InvestigationJob.claim_version == claim.version
    )
    if event is not None:
        query = query.where(InvestigationJob.event_type == event.value)
    return session.exec(query.order_by(col(InvestigationJob.created_at).desc())).first()


def count_jobs(session: Session, claim: Claim, event: JobEvent) -> int:
    return session.exec(
        select(func.count())
        .select_from(InvestigationJob)
        .where(
            InvestigationJob.claim_id == claim.id,
            InvestigationJob.claim_version == claim.version,
            InvestigationJob.event_type == event.value,
        )
    ).one()
