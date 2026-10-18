import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Text, UniqueConstraint, true
from sqlmodel import Field, Relationship

from app.models.base import (
    TimestampedModel,
    UUIDModel,
    jsonb_required_field,
    timestamptz_field,
)

if TYPE_CHECKING:
    from app.models.tenancy import AppUser


class RiskVector(UUIDModel, table=True):
    __tablename__ = "risk_vector"

    code: str = Field(unique=True)
    name: str
    description: str | None = Field(default=None, sa_type=Text)
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})

    rule_sets: list["RuleSet"] = Relationship(back_populates="vector")


class RuleSet(TimestampedModel, table=True):
    __tablename__ = "rule_set"

    vector_id: uuid.UUID = Field(foreign_key="risk_vector.id", index=True)
    name: str
    description: str | None = Field(default=None, sa_type=Text)

    vector: "RiskVector" = Relationship(back_populates="rule_sets")
    versions: list["RuleVersion"] = Relationship(back_populates="rule_set")


class RuleVersion(TimestampedModel, table=True):
    __tablename__ = "rule_version"
    __table_args__ = (UniqueConstraint("rule_set_id", "version"),)

    rule_set_id: uuid.UUID = Field(foreign_key="rule_set.id")
    version: str
    status: str
    approved_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    approved_at: datetime | None = timestamptz_field()
    activated_at: datetime | None = timestamptz_field()
    retired_at: datetime | None = timestamptz_field()

    rule_set: "RuleSet" = Relationship(back_populates="versions")
    approver: Optional["AppUser"] = Relationship()
    expected_rules: list["ExpectedRule"] = Relationship(back_populates="rule_version")


class ExpectedRule(TimestampedModel, table=True):
    __tablename__ = "expected_rule"

    rule_version_id: uuid.UUID = Field(foreign_key="rule_version.id", index=True)
    code_pattern: str
    expected_evidence_spec: dict[str, Any] = jsonb_required_field()
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})

    rule_version: "RuleVersion" = Relationship(back_populates="expected_rules")


class PolicyVersion(TimestampedModel, table=True):
    __tablename__ = "policy_version"

    version: str = Field(unique=True)
    status: str
    config_hash: str
    approved_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    approved_at: datetime | None = timestamptz_field()
    config: dict[str, Any] = jsonb_required_field()

    approver: Optional["AppUser"] = Relationship()
    rules: list["PolicyRule"] = Relationship(back_populates="policy_version")


class PolicyRule(TimestampedModel, table=True):
    __tablename__ = "policy_rule"
    __table_args__ = (UniqueConstraint("policy_version_id", "code"),)

    policy_version_id: uuid.UUID = Field(foreign_key="policy_version.id")
    code: str
    tier: str
    condition_spec: dict[str, Any] = jsonb_required_field()
    priority: int
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})

    policy_version: "PolicyVersion" = Relationship(back_populates="rules")
