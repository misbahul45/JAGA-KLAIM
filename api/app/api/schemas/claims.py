import uuid
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from app.services.claims import CodeSpec

CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._\-/]{0,31}$"
EPISODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._\-/]{2,63}$"
PSEUDONYM_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._\-]{2,63}$"

CodeType = Literal["diagnosis", "procedure", "inacbg", "other"]
ClaimSortField = Literal["updated_at", "created_at", "episode_no", "status"]


class CodeIn(BaseModel):
    code_type: CodeType
    code: str = Field(pattern=CODE_PATTERN)
    position: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)

    def to_spec(self) -> CodeSpec:
        return CodeSpec(self.code_type, self.code, self.position, self.description)


class CodeOut(BaseModel):
    id: uuid.UUID
    code_type: str
    code: str
    position: str | None
    description: str | None


class ClaimCreate(BaseModel):
    episode_no: str = Field(pattern=EPISODE_PATTERN)
    patient_pseudonym: str = Field(pattern=PSEUDONYM_PATTERN)
    codes: list[CodeIn] = Field(min_length=1, max_length=50)
    episode_start: AwareDatetime | None = None
    episode_end: AwareDatetime | None = None


class ClaimUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    codes: list[CodeIn] | None = Field(default=None, min_length=1, max_length=50)
    episode_start: AwareDatetime | None = None
    episode_end: AwareDatetime | None = None


class ClaimOut(BaseModel):
    id: uuid.UUID
    episode_no: str
    patient_pseudonym: str
    status: str
    version: int
    episode_start: AwareDatetime | None
    episode_end: AwareDatetime | None
    submitted_at: AwareDatetime | None
    locked_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    codes: list[CodeOut]


class ClaimListItem(BaseModel):
    id: uuid.UUID
    episode_no: str
    patient_pseudonym: str
    status: str
    version: int
    updated_at: AwareDatetime
    code_count: int
    open_review_count: int
    highest_open_tier: str | None


class JobOut(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    claim_version: int
    event_type: str
    status: str
    attempt_count: int
    reason: str | None
    error_message: str | None
    created_at: AwareDatetime
    processed_at: AwareDatetime | None
    idempotent_replay: bool = False


class RunSummaryOut(BaseModel):
    id: uuid.UUID
    vector_code: str
    rule_version: str
    status: str
    outcome: str | None
    claim_version: int
    stale: bool
    rerun_of_run_id: uuid.UUID | None
    abstain_reason: str | None
    tier_counts: dict[str, int]
    started_at: AwareDatetime
    finished_at: AwareDatetime | None


class ClaimDetailOut(ClaimOut):
    evidence_count: int
    quarantined_count: int
    open_review_count: int
    evidence_updated_after_run: bool
    runs: list[RunSummaryOut]
    latest_job: JobOut | None


class RerunRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class LockRequest(BaseModel):
    acknowledge_limitations: bool = False
