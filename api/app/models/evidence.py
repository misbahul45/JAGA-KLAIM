import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Index, Text, UniqueConstraint, false, text, true
from sqlmodel import Field, Relationship

from app.domain.enums import CitationValidation, HealthStatus, sql_values
from app.models.base import (
    EMBEDDING_DIM,
    TimestampedModel,
    UUIDModel,
    check,
    created_at_field,
    jsonb_object_field,
    jsonb_optional_field,
    required_timestamptz_field,
    timestamptz_field,
)

if TYPE_CHECKING:
    from app.models.claims import Claim
    from app.models.investigation import Finding


class EvidenceSource(TimestampedModel, table=True):
    __tablename__ = "evidence_source"
    __table_args__ = (
        UniqueConstraint("faskes_id", "system_ref", name="uq_evidence_source_faskes_system_ref"),
        check("health_status_valid", f"health_status IN ({sql_values(HealthStatus)})"),
        check("freshness_sla_positive", "freshness_sla_seconds > 0"),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    source_type: str
    system_ref: str
    is_enabled: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
    config: dict[str, Any] = jsonb_object_field()
    health_status: str = Field(
        default=HealthStatus.UNKNOWN.value,
        sa_column_kwargs={"server_default": HealthStatus.UNKNOWN.value},
    )
    last_health_check_at: datetime | None = timestamptz_field()
    last_synced_at: datetime | None = timestamptz_field()
    freshness_sla_seconds: int = Field(
        default=86400, sa_column_kwargs={"server_default": text("86400")}
    )
    coverage: dict[str, Any] = jsonb_object_field()

    items: list["EvidenceItem"] = Relationship(back_populates="source")


class EvidenceItem(TimestampedModel, table=True):
    __tablename__ = "evidence_item"
    __table_args__ = (
        UniqueConstraint(
            "claim_id", "source_id", "content_hash", name="uq_evidence_item_claim_source_hash"
        ),
        Index("ix_evidence_item_claim_id_recorded_at", "claim_id", "recorded_at"),
        Index(
            "ix_evidence_item_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    source_id: uuid.UUID = Field(foreign_key="evidence_source.id", index=True)
    claim_id: uuid.UUID = Field(foreign_key="claim.id")
    recorded_at: datetime = required_timestamptz_field()
    content_text: str | None = Field(default=None, sa_type=Text)
    content_ref: dict[str, Any] | None = jsonb_optional_field()
    embedding: list[float] | None = Field(default=None, sa_type=VECTOR(EMBEDDING_DIM))
    content_hash: str = Field(index=True)
    injection_suspected: bool = Field(
        default=False, sa_column_kwargs={"server_default": false()}
    )

    source: "EvidenceSource" = Relationship(back_populates="items")
    claim: "Claim" = Relationship(back_populates="evidence_items")
    citations: list["EvidenceCitation"] = Relationship(back_populates="evidence_item")


class EvidenceCitation(UUIDModel, table=True):
    __tablename__ = "evidence_citation"
    __table_args__ = (
        check(
            "validation_status_valid",
            f"validation_status IN ({sql_values(CitationValidation)})",
        ),
    )

    finding_id: uuid.UUID = Field(foreign_key="finding.id", index=True)
    evidence_item_id: uuid.UUID = Field(foreign_key="evidence_item.id", index=True)
    quote_span: dict[str, Any] | None = jsonb_optional_field()
    evidence_hash: str
    validation_status: str = Field(
        default=CitationValidation.UNCHECKED.value,
        sa_column_kwargs={"server_default": CitationValidation.UNCHECKED.value},
    )
    cited_at: datetime = created_at_field()

    finding: "Finding" = Relationship(back_populates="citations")
    evidence_item: "EvidenceItem" = Relationship(back_populates="citations")
