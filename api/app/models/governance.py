import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Index, Numeric
from sqlmodel import Field, Relationship

from app.models.base import (
    TimestampedModel,
    jsonb_object_field,
    jsonb_optional_field,
    required_timestamptz_field,
)
from app.models.tenancy import AppUser


class AuditLog(TimestampedModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_log_faskes_id_created_at", "faskes_id", "created_at"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id")
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

    actor: Optional[AppUser] = Relationship()


class MetricSnapshot(TimestampedModel, table=True):
    __tablename__ = "metric_snapshot"
    __table_args__ = (
        Index(
            "ix_metric_snapshot_faskes_id_metric_code_window_end",
            "faskes_id",
            "metric_code",
            "window_end",
        ),
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
