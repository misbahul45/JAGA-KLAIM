import uuid
from typing import Any

from pydantic import AwareDatetime, BaseModel

from app.api.schemas.review import CitationOut


class StepOut(BaseModel):
    seq: int
    step_type: str
    tool_name: str | None
    status: str
    source_id: uuid.UUID | None
    result_ref: dict[str, Any] | None
    latency_ms: int | None
    error_message: str | None


class FindingOut(BaseModel):
    id: uuid.UUID
    status: str
    claim_code: str | None
    tier: str | None
    intervention_id: uuid.UUID | None
    revealed: bool
    mismatch_desc: str | None
    signal_strength: float | None
    delta: dict[str, Any] | None
    citations: list[CitationOut]


class RunDetailOut(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    claim_version: int
    vector_code: str
    status: str
    outcome: str | None
    stale: bool
    trigger: str
    rerun_of_run_id: uuid.UUID | None
    correlation_id: uuid.UUID
    rule_version: str
    policy_version: str
    model_name: str
    model_version: str
    prompt_version: str
    abstain_reason: str | None
    coverage: dict[str, Any]
    validation_errors: dict[str, Any] | None
    tier_counts: dict[str, int]
    started_at: AwareDatetime
    finished_at: AwareDatetime | None
    steps: list[StepOut]
    findings: list[FindingOut]
