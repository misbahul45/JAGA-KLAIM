import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Index, Numeric, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship
from sqlmodel.main import SQLModelConfig

from app.domain.enums import (
    FindingStatus,
    JobStatus,
    RunOutcome,
    RunStatus,
    StepStatus,
    sql_values,
)
from app.models.base import (
    TimestampedModel,
    UUIDModel,
    check,
    created_at_field,
    jsonb_object_field,
    jsonb_optional_field,
    timestamptz_field,
)

if TYPE_CHECKING:
    from app.models.claims import Claim, ClaimCode
    from app.models.evidence import EvidenceCitation, EvidenceSource
    from app.models.review import Intervention
    from app.models.rules import PolicyVersion, RiskVector, RuleVersion


class InvestigationJob(TimestampedModel, table=True):
    __tablename__ = "investigation_job"
    __table_args__ = (
        UniqueConstraint("faskes_id", "idempotency_key"),
        Index("ix_investigation_job_status_created_at", "status", "created_at"),
        check("status_valid", f"status IN ({sql_values(JobStatus)})"),
        check("attempt_count_non_negative", "attempt_count >= 0"),
        check("claim_version_positive", "claim_version >= 1"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    claim_id: uuid.UUID = Field(foreign_key="claim.id", index=True)
    claim_version: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    event_type: str
    status: str
    attempt_count: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    idempotency_key: str
    requested_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    reason: str | None = Field(default=None, sa_type=Text)
    error_message: str | None = Field(default=None, sa_type=Text)
    next_attempt_at: datetime | None = timestamptz_field()
    locked_at: datetime | None = timestamptz_field()
    processed_at: datetime | None = timestamptz_field()

    claim: "Claim" = Relationship(back_populates="jobs")
    runs: list["InvestigationRun"] = Relationship(back_populates="job")


class InvestigationRun(UUIDModel, table=True):
    __tablename__ = "investigation_run"
    __table_args__ = (
        check("status_valid", f"status IN ({sql_values(RunStatus)})"),
        check(
            "outcome_valid",
            f"outcome IS NULL OR outcome IN ({sql_values(RunOutcome)})",
        ),
        check("claim_version_positive", "claim_version >= 1"),
    )
    model_config = SQLModelConfig(protected_namespaces=())

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    claim_id: uuid.UUID = Field(foreign_key="claim.id", index=True)
    claim_version: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    job_id: uuid.UUID | None = Field(
        default=None, foreign_key="investigation_job.id", index=True
    )
    rerun_of_run_id: uuid.UUID | None = Field(
        default=None, foreign_key="investigation_run.id", index=True
    )
    correlation_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    rule_version_id: uuid.UUID = Field(foreign_key="rule_version.id", index=True)
    policy_version_id: uuid.UUID = Field(foreign_key="policy_version.id", index=True)
    trigger: str
    status: str
    outcome: str | None = None
    abstain_reason: str | None = Field(default=None, sa_type=Text)
    coverage: dict[str, Any] = jsonb_object_field()
    validation_errors: dict[str, Any] | None = jsonb_optional_field()
    model_name: str
    model_version: str
    prompt_version: str
    started_at: datetime = created_at_field()
    finished_at: datetime | None = timestamptz_field()
    stale_at: datetime | None = timestamptz_field()

    claim: "Claim" = Relationship(back_populates="runs")
    job: Optional["InvestigationJob"] = Relationship(back_populates="runs")
    rule_version: "RuleVersion" = Relationship()
    policy_version: "PolicyVersion" = Relationship()
    steps: list["AgentStep"] = Relationship(back_populates="run")
    findings: list["Finding"] = Relationship(back_populates="run")
    interventions: list["Intervention"] = Relationship(back_populates="run")


class AgentStep(TimestampedModel, table=True):
    __tablename__ = "agent_step"
    __table_args__ = (
        UniqueConstraint("run_id", "seq"),
        check("status_valid", f"status IN ({sql_values(StepStatus)})"),
    )

    run_id: uuid.UUID = Field(foreign_key="investigation_run.id")
    seq: int
    step_type: str
    tool_name: str | None = None
    query: str | None = Field(default=None, sa_type=Text)
    source_id: uuid.UUID | None = Field(
        default=None, foreign_key="evidence_source.id", index=True
    )
    status: str
    result_ref: dict[str, Any] | None = jsonb_optional_field()
    latency_ms: int | None = None
    error_message: str | None = Field(default=None, sa_type=Text)

    run: "InvestigationRun" = Relationship(back_populates="steps")
    source: Optional["EvidenceSource"] = Relationship()


class Finding(TimestampedModel, table=True):
    __tablename__ = "finding"
    __table_args__ = (
        check("status_valid", f"status IN ({sql_values(FindingStatus)})"),
        check("confidence_in_unit_range", "confidence >= 0 AND confidence <= 1"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    run_id: uuid.UUID = Field(foreign_key="investigation_run.id", index=True)
    vector_id: uuid.UUID = Field(foreign_key="risk_vector.id", index=True)
    claim_code_id: uuid.UUID | None = Field(
        default=None, foreign_key="claim_code.id", index=True
    )
    status: str = Field(
        default=FindingStatus.VALID.value,
        sa_column_kwargs={"server_default": FindingStatus.VALID.value},
    )
    mismatch_desc: str = Field(sa_type=Text)
    delta: dict[str, Any] = jsonb_object_field()
    confidence: Decimal = Field(sa_type=Numeric)

    run: "InvestigationRun" = Relationship(back_populates="findings")
    vector: "RiskVector" = Relationship()
    claim_code: Optional["ClaimCode"] = Relationship(back_populates="findings")
    citations: list["EvidenceCitation"] = Relationship(back_populates="finding")
    interventions: list["Intervention"] = Relationship(back_populates="finding")
