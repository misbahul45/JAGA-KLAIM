import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, Index, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

from app.domain.enums import (
    FollowUp,
    RuleUpdateStatus,
    Tier,
    Verdict,
    sql_values,
)
from app.models.base import (
    TimestampedModel,
    UUIDModel,
    check,
    created_at_field,
    jsonb_optional_field,
    jsonb_required_field,
    timestamptz_field,
)

if TYPE_CHECKING:
    from app.models.investigation import Finding, InvestigationRun
    from app.models.rules import PolicyRule, RuleVersion
    from app.models.tenancy import AppUser


class Intervention(TimestampedModel, table=True):
    __tablename__ = "intervention"
    __table_args__ = (
        Index(
            "uq_intervention_run_finding",
            "run_id",
            "finding_id",
            unique=True,
            postgresql_where=text("finding_id IS NOT NULL"),
        ),
        Index(
            "uq_intervention_run_without_finding",
            "run_id",
            unique=True,
            postgresql_where=text("finding_id IS NULL"),
        ),
        Index("ix_intervention_faskes_id_resolved_at", "faskes_id", "resolved_at"),
        check("tier_valid", f"tier IN ({sql_values(Tier)})"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    run_id: uuid.UUID = Field(foreign_key="investigation_run.id", index=True)
    finding_id: uuid.UUID | None = Field(
        default=None, foreign_key="finding.id", index=True
    )
    policy_rule_id: uuid.UUID = Field(foreign_key="policy_rule.id", index=True)
    tier: str
    policy_rule_ref: str
    resolved_at: datetime | None = timestamptz_field()

    run: "InvestigationRun" = Relationship(back_populates="interventions")
    finding: Optional["Finding"] = Relationship(back_populates="interventions")
    policy_rule: "PolicyRule" = Relationship()
    cognitive_assessments: list["CognitiveAssessment"] = Relationship(
        back_populates="intervention"
    )
    human_verdicts: list["HumanVerdict"] = Relationship(back_populates="intervention")


class CognitiveAssessment(UUIDModel, table=True):
    __tablename__ = "cognitive_assessment"
    __table_args__ = (
        UniqueConstraint(
            "intervention_id", "verifier_id", name="uq_cognitive_assessment_intervention_verifier"
        ),
        check("self_verdict_valid", f"self_verdict IN ({sql_values(Verdict)})"),
    )

    intervention_id: uuid.UUID = Field(foreign_key="intervention.id", index=True)
    verifier_id: uuid.UUID = Field(foreign_key="app_user.id", index=True)
    self_verdict: str
    self_note: str | None = Field(default=None, sa_type=Text)
    submitted_at: datetime = created_at_field()

    intervention: "Intervention" = Relationship(back_populates="cognitive_assessments")
    verifier: "AppUser" = Relationship()


class HumanVerdict(TimestampedModel, table=True):
    __tablename__ = "human_verdict"
    __table_args__ = (
        Index(
            "uq_human_verdict_original_per_intervention",
            "intervention_id",
            unique=True,
            postgresql_where=text("supersedes_verdict_id IS NULL"),
        ),
        UniqueConstraint("supersedes_verdict_id", name="uq_human_verdict_supersedes"),
        check("verdict_valid", f"verdict IN ({sql_values(Verdict)})"),
        check("follow_up_valid", f"follow_up IN ({sql_values(FollowUp)})"),
        check(
            "correction_requires_rationale",
            "supersedes_verdict_id IS NULL OR (rationale IS NOT NULL AND length(trim(rationale)) > 0)",
        ),
    )

    intervention_id: uuid.UUID = Field(foreign_key="intervention.id", index=True)
    verifier_id: uuid.UUID = Field(foreign_key="app_user.id", index=True)
    assessment_id: uuid.UUID | None = Field(
        default=None, foreign_key="cognitive_assessment.id", index=True
    )
    supersedes_verdict_id: uuid.UUID | None = Field(
        default=None, foreign_key="human_verdict.id"
    )
    verdict: str
    follow_up: str = Field(
        default=FollowUp.PROCEED.value,
        sa_column_kwargs={"server_default": FollowUp.PROCEED.value},
    )
    rationale: str | None = Field(default=None, sa_type=Text)
    time_to_decision_ms: int | None = Field(default=None, sa_type=BigInteger)

    intervention: "Intervention" = Relationship(back_populates="human_verdicts")
    verifier: "AppUser" = Relationship()
    assessment: Optional["CognitiveAssessment"] = Relationship()
    rule_updates: list["RuleUpdate"] = Relationship(back_populates="verdict")


class RuleUpdate(TimestampedModel, table=True):
    __tablename__ = "rule_update"
    __table_args__ = (
        check("status_valid", f"status IN ({sql_values(RuleUpdateStatus)})"),
        check(
            "decider_not_proposer",
            "proposed_by IS NULL OR decided_by IS NULL OR proposed_by <> decided_by",
        ),
    )

    verdict_id: uuid.UUID = Field(foreign_key="human_verdict.id", index=True)
    base_rule_version_id: uuid.UUID = Field(foreign_key="rule_version.id", index=True)
    result_rule_version_id: uuid.UUID | None = Field(
        default=None, foreign_key="rule_version.id", index=True
    )
    proposed_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    proposed_change: dict[str, Any] = jsonb_required_field()
    evaluation: dict[str, Any] | None = jsonb_optional_field()
    evaluated_at: datetime | None = timestamptz_field()
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
    proposer: Optional["AppUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RuleUpdate.proposed_by]"}
    )
    decider: Optional["AppUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RuleUpdate.decided_by]"}
    )


class RuleUpdateBasis(SQLModel, table=True):
    __tablename__ = "rule_update_basis"

    rule_update_id: uuid.UUID = Field(foreign_key="rule_update.id", primary_key=True)
    verdict_id: uuid.UUID = Field(foreign_key="human_verdict.id", primary_key=True)
