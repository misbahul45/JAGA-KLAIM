import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Index, Numeric, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import (
    TimestampedModel,
    check,
    jsonb_object_field,
    jsonb_optional_field,
    required_timestamptz_field,
)
from app.models.tenancy import AppUser


class AuditLog(TimestampedModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = (
        UniqueConstraint("faskes_id", "seq", name="uq_audit_log_faskes_seq"),
        Index("ix_audit_log_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_log_faskes_id_created_at", "faskes_id", "created_at"),
        check("seq_positive", "seq >= 1"),
        check(
            "chain_link_consistent",
            "(seq = 1 AND prev_hash IS NULL) OR (seq > 1 AND prev_hash IS NOT NULL)",
        ),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id")
    seq: int = Field(sa_type=BigInteger)
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    payload: dict[str, Any] = jsonb_object_field()
    actor_type: str
    actor_id: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    prev_hash: str | None = None
    record_hash: str

    actor: AppUser | None = Relationship()


class MetricSnapshot(TimestampedModel, table=True):
    __tablename__ = "metric_snapshot"
    __table_args__ = (
        Index(
            "ix_metric_snapshot_faskes_id_metric_code_window_end",
            "faskes_id",
            "metric_code",
            "window_end",
        ),
        Index(
            "uq_metric_snapshot_identity",
            "faskes_id",
            "metric_code",
            "window_start",
            "window_end",
            "vector_id",
            "rule_version_id",
            "policy_version_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        check("window_valid", "window_end > window_start"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id")
    rule_version_id: uuid.UUID | None = Field(default=None, foreign_key="rule_version.id")
    policy_version_id: uuid.UUID | None = Field(
        default=None, foreign_key="policy_version.id"
    )
    vector_id: uuid.UUID | None = Field(default=None, foreign_key="risk_vector.id")
    metric_code: str
    window_start: datetime = required_timestamptz_field()
    window_end: datetime = required_timestamptz_field()
    value: Decimal = Field(sa_type=Numeric)
    numerator: Decimal | None = Field(default=None, sa_type=Numeric)
    denominator: Decimal | None = Field(default=None, sa_type=Numeric)
    context: dict[str, Any] | None = jsonb_optional_field()
