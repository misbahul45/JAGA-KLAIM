from app.api.schemas.claims import (
    ClaimDetailOut,
    ClaimListItem,
    ClaimOut,
    CodeOut,
    JobOut,
    RunSummaryOut,
)
from app.api.schemas.evidence import EvidenceOut
from app.api.schemas.investigation import FindingOut, RunDetailOut, StepOut
from app.api.schemas.review import (
    TIER_LABELS,
    AssessmentOut,
    CitationOut,
    ClaimBriefOut,
    InterventionDetailOut,
    QueueItemOut,
    RecommendationOut,
    ReviewGateOut,
    RunBriefOut,
    VerdictOut,
)
from app.domain.permissions import Permission
from app.models import (
    Claim,
    ClaimCode,
    CognitiveAssessment,
    EvidenceCitation,
    HumanVerdict,
    InvestigationJob,
)
from app.services.auth import Principal
from app.services.claim_state import REVIEW_TIERS
from app.services.claims import ClaimDetail, ClaimListRow
from app.services.review import InterventionDetail, QueueRow
from app.services.run_detail import RunDetail


def code_out(code: ClaimCode) -> CodeOut:
    return CodeOut(
        id=code.id,
        code_type=code.code_type,
        code=code.code,
        position=code.position,
        description=code.description,
    )


def job_out(job: InvestigationJob, *, replay: bool = False) -> JobOut:
    return JobOut(
        id=job.id,
        claim_id=job.claim_id,
        claim_version=job.claim_version,
        event_type=job.event_type,
        status=job.status,
        attempt_count=job.attempt_count,
        reason=job.reason,
        error_message=job.error_message,
        created_at=job.created_at,
        processed_at=job.processed_at,
        idempotent_replay=replay,
    )


def claim_out(claim: Claim, codes: list[ClaimCode]) -> ClaimOut:
    return ClaimOut(
        id=claim.id,
        episode_no=claim.episode_no,
        patient_pseudonym=claim.patient_pseudonym,
        status=claim.status,
        version=claim.version,
        episode_start=claim.episode_start,
        episode_end=claim.episode_end,
        submitted_at=claim.submitted_at,
        locked_at=claim.locked_at,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        codes=[code_out(c) for c in codes],
    )


def claim_list_item(row: ClaimListRow) -> ClaimListItem:
    claim = row.claim
    return ClaimListItem(
        id=claim.id,
        episode_no=claim.episode_no,
        patient_pseudonym=claim.patient_pseudonym,
        status=claim.status,
        version=claim.version,
        updated_at=claim.updated_at,
        code_count=row.code_count,
        open_review_count=row.open_review_count,
        highest_open_tier=row.highest_open_tier,
    )


def claim_detail_out(detail: ClaimDetail) -> ClaimDetailOut:
    base = claim_out(detail.claim, detail.codes)
    return ClaimDetailOut(
        **base.model_dump(),
        evidence_count=detail.evidence_count,
        quarantined_count=detail.quarantined_count,
        open_review_count=detail.open_review_count,
        evidence_updated_after_run=detail.evidence_updated_after_run,
        runs=[
            RunSummaryOut(
                id=s.run.id,
                vector_code=s.vector_code,
                rule_version=s.rule_version_label,
                status=s.run.status,
                outcome=s.run.outcome,
                claim_version=s.run.claim_version,
                stale=s.stale,
                rerun_of_run_id=s.run.rerun_of_run_id,
                abstain_reason=s.run.abstain_reason,
                tier_counts=s.tier_counts,
                started_at=s.run.started_at,
                finished_at=s.run.finished_at,
            )
            for s in detail.runs
        ],
        latest_job=job_out(detail.latest_job) if detail.latest_job else None,
    )


def assessment_out(item: CognitiveAssessment) -> AssessmentOut:
    return AssessmentOut(
        id=item.id,
        intervention_id=item.intervention_id,
        self_verdict=item.self_verdict,
        self_note=item.self_note,
        submitted_at=item.submitted_at,
    )


def verdict_out(item: HumanVerdict) -> VerdictOut:
    return VerdictOut(
        id=item.id,
        intervention_id=item.intervention_id,
        verifier_id=item.verifier_id,
        verdict=item.verdict,
        follow_up=item.follow_up,
        rationale=item.rationale,
        supersedes_verdict_id=item.supersedes_verdict_id,
        time_to_decision_ms=item.time_to_decision_ms,
        created_at=item.created_at,
    )


def citation_out(item: EvidenceCitation) -> CitationOut:
    span = item.quote_span or {}
    return CitationOut(
        evidence_item_id=item.evidence_item_id,
        evidence_hash=item.evidence_hash,
        validation_status=item.validation_status,
        role=span.get("role"),
        quote=span.get("quote"),
        start=span.get("start"),
        end=span.get("end"),
        invalid_reason=span.get("invalid_reason"),
    )


def queue_item_out(row: QueueRow) -> QueueItemOut:
    return QueueItemOut(
        intervention_id=row.intervention.id,
        tier=row.intervention.tier,
        tier_label=TIER_LABELS[row.intervention.tier],
        vector_code=row.vector_code,
        claim_id=row.claim.id,
        episode_no=row.claim.episode_no,
        claim_status=row.claim.status,
        created_at=row.intervention.created_at,
        resolved_at=row.intervention.resolved_at,
        assessed_by_me=row.assessed,
        requires_assessment=row.intervention.tier in REVIEW_TIERS,
    )


def intervention_detail_out(detail: InterventionDetail, principal: Principal) -> InterventionDetailOut:
    intervention = detail.intervention
    include_content = principal.can(Permission.EVIDENCE_CONTENT)
    recommendation: RecommendationOut | None = None
    if detail.revealed:
        finding = detail.finding
        recommendation = RecommendationOut(
            finding_id=finding.id if finding else None,
            finding_status=finding.status if finding else None,
            mismatch_desc=finding.mismatch_desc if finding else None,
            abstain_reason=detail.run.abstain_reason if intervention.finding_id is None else None,
            signal_strength=float(finding.confidence) if finding else None,
            delta=finding.delta if finding else {"coverage": detail.run.coverage},
            citations=[citation_out(c) for c in detail.citations],
            policy_rule=intervention.policy_rule_ref,
        )
    return InterventionDetailOut(
        id=intervention.id,
        tier=intervention.tier,
        tier_label=TIER_LABELS[intervention.tier],
        vector_code=detail.vector_code,
        created_at=intervention.created_at,
        resolved_at=intervention.resolved_at,
        stale=detail.stale,
        evidence_updated_after_run=detail.evidence_updated_after_run,
        claim=ClaimBriefOut(
            id=detail.claim.id,
            episode_no=detail.claim.episode_no,
            patient_pseudonym=detail.claim.patient_pseudonym,
            status=detail.claim.status,
            version=detail.claim.version,
            codes=[code_out(c) for c in detail.codes],
        ),
        run=RunBriefOut(
            id=detail.run.id,
            status=detail.run.status,
            outcome=detail.run.outcome,
            claim_version=detail.run.claim_version,
            rule_version_id=detail.run.rule_version_id,
            rule_version=detail.rule_version_label,
            rule_validation_status=detail.rule_validation_status,
            policy_version=detail.policy_version_label,
            model_name=detail.run.model_name,
            model_version=detail.run.model_version,
            prompt_version=detail.run.prompt_version,
            correlation_id=detail.run.correlation_id,
            started_at=detail.run.started_at,
        ),
        evidence=[
            EvidenceOut.from_item(item, source, include_content=include_content)
            for item, source in detail.evidence
        ],
        gate=ReviewGateOut(
            required=detail.gate_required,
            revealed=detail.revealed,
            own_assessment=assessment_out(detail.own_assessment) if detail.own_assessment else None,
        ),
        recommendation=recommendation,
        verdicts=[verdict_out(v) for v in detail.verdicts],
    )


def run_detail_out(detail: RunDetail) -> RunDetailOut:
    run = detail.run
    return RunDetailOut(
        id=run.id,
        claim_id=run.claim_id,
        claim_version=run.claim_version,
        vector_code=detail.vector_code,
        status=run.status,
        outcome=run.outcome,
        stale=detail.stale,
        trigger=run.trigger,
        rerun_of_run_id=run.rerun_of_run_id,
        correlation_id=run.correlation_id,
        rule_version=detail.rule_version_label,
        policy_version=detail.policy_version_label,
        model_name=run.model_name,
        model_version=run.model_version,
        prompt_version=run.prompt_version,
        abstain_reason=run.abstain_reason,
        coverage=run.coverage,
        validation_errors=run.validation_errors,
        tier_counts=detail.tier_counts,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[
            StepOut(
                seq=s.seq,
                step_type=s.step_type,
                tool_name=s.tool_name,
                status=s.status,
                source_id=s.source_id,
                result_ref=s.result_ref,
                latency_ms=s.latency_ms,
                error_message=s.error_message,
            )
            for s in detail.steps
        ],
        findings=[
            FindingOut(
                id=f.finding.id,
                status=f.finding.status,
                claim_code=f.claim_code,
                tier=f.intervention.tier if f.intervention else None,
                intervention_id=f.intervention.id if f.intervention else None,
                revealed=f.revealed,
                mismatch_desc=f.finding.mismatch_desc if f.revealed else None,
                signal_strength=float(f.finding.confidence) if f.revealed else None,
                delta=f.finding.delta if f.revealed else None,
                citations=[citation_out(c) for c in f.citations],
            )
            for f in detail.findings
        ],
    )
