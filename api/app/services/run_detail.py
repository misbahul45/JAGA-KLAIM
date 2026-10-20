import uuid
from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.core.errors import not_found
from app.domain.permissions import Permission
from app.models import (
    AgentStep,
    Claim,
    ClaimCode,
    CognitiveAssessment,
    EvidenceCitation,
    Finding,
    Intervention,
    InvestigationRun,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleVersion,
)
from app.services.auth import Principal
from app.services.claim_state import REVIEW_TIERS


@dataclass(frozen=True)
class FindingView:
    finding: Finding
    claim_code: str | None
    intervention: Intervention | None
    citations: list[EvidenceCitation]
    revealed: bool


@dataclass(frozen=True)
class RunDetail:
    run: InvestigationRun
    claim: Claim
    vector_code: str
    rule_version_label: str
    policy_version_label: str
    steps: list[AgentStep]
    findings: list[FindingView]
    tier_counts: dict[str, int]
    interventions: list[Intervention]
    stale: bool


def run_detail(session: Session, principal: Principal, run_id: uuid.UUID) -> RunDetail:
    run = session.exec(
        select(InvestigationRun).where(
            InvestigationRun.id == run_id, InvestigationRun.faskes_id == principal.faskes_id
        )
    ).first()
    if run is None:
        raise not_found("Hasil pemeriksaan")
    claim = session.get(Claim, run.claim_id)
    assert claim is not None
    vector_code, rule_label = session.exec(
        select(RiskVector.code, RuleVersion.version)
        .join(RuleSet, col(RuleSet.vector_id) == col(RiskVector.id))
        .join(RuleVersion, col(RuleVersion.rule_set_id) == col(RuleSet.id))
        .where(RuleVersion.id == run.rule_version_id)
    ).one()
    policy = session.get(PolicyVersion, run.policy_version_id)
    assert policy is not None
    steps = list(
        session.exec(select(AgentStep).where(AgentStep.run_id == run.id).order_by(col(AgentStep.seq)))
    )
    interventions = list(
        session.exec(
            select(Intervention).where(
                Intervention.run_id == run.id, Intervention.faskes_id == principal.faskes_id
            )
        )
    )
    by_finding = {i.finding_id: i for i in interventions if i.finding_id}
    gated = principal.can(Permission.REVIEW_ASSESS)
    assessed: set[uuid.UUID] = set()
    if gated and interventions:
        assessed = set(
            session.exec(
                select(CognitiveAssessment.intervention_id).where(
                    col(CognitiveAssessment.intervention_id).in_([i.id for i in interventions]),
                    CognitiveAssessment.verifier_id == principal.user_id,
                )
            )
        )
    findings: list[FindingView] = []
    for finding in session.exec(
        select(Finding)
        .where(Finding.run_id == run.id, Finding.faskes_id == principal.faskes_id)
        .order_by(col(Finding.created_at))
    ):
        intervention = by_finding.get(finding.id)
        needs_gate = (
            gated and intervention is not None and intervention.tier in REVIEW_TIERS
        )
        revealed = (not needs_gate) or (intervention is not None and intervention.id in assessed)
        citations: list[EvidenceCitation] = []
        if revealed:
            citations = list(
                session.exec(
                    select(EvidenceCitation)
                    .where(EvidenceCitation.finding_id == finding.id)
                    .order_by(col(EvidenceCitation.cited_at))
                )
            )
        code = (
            session.exec(select(ClaimCode.code).where(ClaimCode.id == finding.claim_code_id)).first()
            if finding.claim_code_id
            else None
        )
        findings.append(FindingView(finding, code, intervention, citations, revealed))
    tier_counts: dict[str, int] = {}
    for item in interventions:
        tier_counts[item.tier] = tier_counts.get(item.tier, 0) + 1
    return RunDetail(
        run=run,
        claim=claim,
        vector_code=vector_code,
        rule_version_label=rule_label,
        policy_version_label=policy.version,
        steps=steps,
        findings=findings,
        tier_counts=tier_counts,
        interventions=interventions,
        stale=run.stale_at is not None or run.claim_version != claim.version,
    )
