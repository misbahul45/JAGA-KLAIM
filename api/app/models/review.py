import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, Text
from sqlmodel import Field, Relationship

from app.models.base import (
    TimestampedModel,
    UUIDModel,
    created_at_field,
    jsonb_required_field,
    timestamptz_field,
)

if TYPE_CHECKING:
    from app.models.investigation import Finding, InvestigationRun
    from app.models.rules import PolicyRule, RuleVersion
    from app.models.tenancy import AppUser


class Intervention(TimestampedModel, table=True):
    __tablename__ = "intervention"

    run_id: uuid.UUID = Field(foreign_key="investigation_run.id", index=True)
    finding_id: uuid.UUID | None = Field(
        default=None, foreign_key="finding.id", index=True
    )
    policy_rule_id: uuid.UUID = Field(foreign_key="policy_rule.id", index=True)
    tier: str
    policy_rule_ref: str

    run: "InvestigationRun" = Relationship(back_populates="interventions")
    finding: Optional["Finding"] = Relationship(back_populates="interventions")
    policy_rule: "PolicyRule" = Relationship()
    cognitive_assessments: list["CognitiveAssessment"] = Relationship(
        back_populates="intervention"
    )
    human_verdicts: list["HumanVerdict"] = Relationship(back_populates="intervention")


class CognitiveAssessment(UUIDModel, table=True):
    __tablename__ = "cognitive_assessment"

    intervention_id: uuid.UUID = Field(foreign_key="intervention.id", index=True)
    verifier_id: uuid.UUID = Field(foreign_key="app_user.id", index=True)
    self_verdict: str
    self_note: str | None = Field(default=None, sa_type=Text)
    submitted_at: datetime = created_at_field()

    intervention: "Intervention" = Relationship(back_populates="cognitive_assessments")
    verifier: "AppUser" = Relationship()


class HumanVerdict(TimestampedModel, table=True):
    __tablename__ = "human_verdict"

    intervention_id: uuid.UUID = Field(foreign_key="intervention.id", index=True)
    verifier_id: uuid.UUID = Field(foreign_key="app_user.id", index=True)
    verdict: str
    rationale: str | None = Field(default=None, sa_type=Text)
    time_to_decision_ms: int | None = Field(default=None, sa_type=BigInteger)

    intervention: "Intervention" = Relationship(back_populates="human_verdicts")
    verifier: "AppUser" = Relationship()
    rule_updates: list["RuleUpdate"] = Relationship(back_populates="verdict")


class RuleUpdate(TimestampedModel, table=True):
    __tablename__ = "rule_update"

    verdict_id: uuid.UUID = Field(foreign_key="human_verdict.id", index=True)
    base_rule_version_id: uuid.UUID = Field(foreign_key="rule_version.id", index=True)
    result_rule_version_id: uuid.UUID | None = Field(
        default=None, foreign_key="rule_version.id", index=True
    )
    proposed_change: dict[str, Any] = jsonb_required_field()
    status: str
    decided_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    decided_at: datetime | None = timestamptz_field()

    verdict: "HumanVerdict" = Relationship(back_populates="rule_updates")
    base_rule_version: "RuleVersion" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RuleUpdate.base_rule_version_id]"}
    )
    result_rule_version: Optional["RuleVersion"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RuleUpdate.result_rule_version_id]"}
    )
    decider: Optional["AppUser"] = Relationship()
