import uuid
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field

from app.api.schemas.claims import CodeOut
from app.api.schemas.evidence import EvidenceOut
from app.domain.enums import FollowUp, Verdict

TIER_LABELS: dict[str, str] = {
    "T0": "Abstain",
    "T1": "Inform",
    "T2": "Recommend Review",
    "T3": "Flag for Human Verdict",
}


class AssessmentIn(BaseModel):
    self_verdict: Verdict
    note: str | None = Field(default=None, max_length=2000)


class VerdictIn(BaseModel):
    verdict: Verdict
    follow_up: FollowUp = FollowUp.PROCEED
    rationale: str = Field(min_length=10, max_length=2000)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    intervention_id: uuid.UUID
    self_verdict: str
    self_note: str | None
    submitted_at: AwareDatetime


class VerdictOut(BaseModel):
    id: uuid.UUID
    intervention_id: uuid.UUID
    verifier_id: uuid.UUID
    verdict: str
    follow_up: str
    rationale: str | None
    supersedes_verdict_id: uuid.UUID | None
    time_to_decision_ms: int | None
    created_at: AwareDatetime


class QueueItemOut(BaseModel):
    intervention_id: uuid.UUID
    tier: str
    tier_label: str
    vector_code: str
    claim_id: uuid.UUID
    episode_no: str
    claim_status: str
    created_at: AwareDatetime
    resolved_at: AwareDatetime | None
    assessed_by_me: bool
    requires_assessment: bool


class CitationOut(BaseModel):
    evidence_item_id: uuid.UUID
    evidence_hash: str
    validation_status: str
    role: str | None
    quote: str | None
    start: int | None
    end: int | None
    invalid_reason: str | None


class RecommendationOut(BaseModel):
    finding_id: uuid.UUID | None
    finding_status: str | None
    mismatch_desc: str | None
    abstain_reason: str | None
    signal_strength: float | None
    delta: dict[str, Any]
    citations: list[CitationOut]
    policy_rule: str


class ReviewGateOut(BaseModel):
    required: bool
    revealed: bool
    own_assessment: AssessmentOut | None


class ClaimBriefOut(BaseModel):
    id: uuid.UUID
    episode_no: str
    patient_pseudonym: str
    status: str
    version: int
    codes: list[CodeOut]


class RunBriefOut(BaseModel):
    id: uuid.UUID
    status: str
    outcome: str | None
    claim_version: int
    rule_version_id: uuid.UUID
    rule_version: str
    rule_validation_status: str
    policy_version: str
    model_name: str
    model_version: str
    prompt_version: str
    correlation_id: uuid.UUID
    started_at: AwareDatetime


class InterventionDetailOut(BaseModel):
    id: uuid.UUID
    tier: str
    tier_label: str
    vector_code: str
    created_at: AwareDatetime
    resolved_at: AwareDatetime | None
    stale: bool
    evidence_updated_after_run: bool
    claim: ClaimBriefOut
    run: RunBriefOut
    evidence: list[EvidenceOut]
    gate: ReviewGateOut
    recommendation: RecommendationOut | None
    verdicts: list[VerdictOut]
