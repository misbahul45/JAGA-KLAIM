import uuid
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field

from app.domain.enums import Tier


class RiskVectorOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_active: bool


class RuleVersionBrief(BaseModel):
    id: uuid.UUID
    version: str
    status: str
    validation_status: str
    created_by: uuid.UUID | None
    approved_by: uuid.UUID | None
    submitted_at: AwareDatetime | None
    approved_at: AwareDatetime | None
    activated_at: AwareDatetime | None
    retired_at: AwareDatetime | None


class RuleSetOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    vector: RiskVectorOut
    active_version_id: uuid.UUID | None
    versions: list[RuleVersionBrief]


class ExpectedRuleIn(BaseModel):
    code_pattern: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9*?\-._/]+$")
    spec: dict[str, Any]


class ExpectedRuleOut(BaseModel):
    id: uuid.UUID
    code_pattern: str
    spec: dict[str, Any]
    is_active: bool


class RuleVersionCreate(BaseModel):
    rule_set_id: uuid.UUID
    version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._\-+]+$")
    validation_status: str = "belum_tervalidasi"
    base_version_id: uuid.UUID | None = None
    expected_rules: list[ExpectedRuleIn] = Field(default_factory=list, max_length=100)


class RuleVersionOut(RuleVersionBrief):
    rule_set_id: uuid.UUID
    rule_set_name: str
    vector_code: str
    expected_rules: list[ExpectedRuleOut]


class ApprovalBody(BaseModel):
    validation_status: str | None = None
    expert_validation_confirmed: bool = False
    note: str | None = Field(default=None, max_length=1000)


class ReasonBody(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class PolicyRuleIn(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    tier: Tier
    priority: int = Field(ge=1, le=10_000)
    condition: dict[str, Any]


class PolicyRuleOut(BaseModel):
    id: uuid.UUID
    code: str
    tier: str
    priority: int
    condition: dict[str, Any]
    is_active: bool


class PolicyVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._\-+]+$")
    rules: list[PolicyRuleIn] = Field(min_length=1, max_length=100)


class PolicyVersionOut(BaseModel):
    id: uuid.UUID
    version: str
    status: str
    config_hash: str
    created_by: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: AwareDatetime | None
    activated_at: AwareDatetime | None
    rules: list[PolicyRuleOut]


class PolicyPreviewIn(BaseModel):
    facts: dict[str, Any]


class PolicyPreviewOut(BaseModel):
    tier: str
    rule: str
    priority: int


class RuleUpdateProposal(BaseModel):
    basis_verdict_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    base_rule_version_id: uuid.UUID
    expected_rule_id: uuid.UUID
    spec_patch: dict[str, Any] = Field(min_length=1)
    rationale: str = Field(min_length=10, max_length=1000)


class RuleUpdateOut(BaseModel):
    id: uuid.UUID
    status: str
    basis_verdict_ids: list[uuid.UUID]
    base_rule_version_id: uuid.UUID
    result_rule_version_id: uuid.UUID | None
    proposed_by: uuid.UUID | None
    decided_by: uuid.UUID | None
    proposed_change: dict[str, Any]
    evaluation: dict[str, Any] | None
    created_at: AwareDatetime
    evaluated_at: AwareDatetime | None
    decided_at: AwareDatetime | None
