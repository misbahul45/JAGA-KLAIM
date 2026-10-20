import uuid
from datetime import timedelta
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field

from app.domain.enums import HealthStatus
from app.models import EvidenceItem, EvidenceSource
from app.models.base import utcnow


class SourceCreate(BaseModel):
    source_type: str = Field(min_length=2, max_length=32)
    system_ref: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
    freshness_sla_seconds: int = Field(default=86400, ge=60, le=60 * 60 * 24 * 365)
    coverage: dict[str, Any] = Field(default_factory=dict)


class SourceUpdate(BaseModel):
    health_status: HealthStatus | None = None
    last_synced_at: AwareDatetime | None = None
    is_enabled: bool | None = None
    freshness_sla_seconds: int | None = Field(default=None, ge=60, le=60 * 60 * 24 * 365)
    coverage: dict[str, Any] | None = None


class SourceOut(BaseModel):
    id: uuid.UUID
    source_type: str
    system_ref: str
    is_enabled: bool
    health_status: str
    last_health_check_at: AwareDatetime | None
    last_synced_at: AwareDatetime | None
    freshness_sla_seconds: int
    fresh: bool
    coverage: dict[str, Any]

    @classmethod
    def from_source(cls, source: EvidenceSource) -> "SourceOut":
        fresh = source.last_synced_at is not None and utcnow() - source.last_synced_at <= timedelta(
            seconds=source.freshness_sla_seconds
        )
        return cls(
            id=source.id,
            source_type=source.source_type,
            system_ref=source.system_ref,
            is_enabled=source.is_enabled,
            health_status=source.health_status,
            last_health_check_at=source.last_health_check_at,
            last_synced_at=source.last_synced_at,
            freshness_sla_seconds=source.freshness_sla_seconds,
            fresh=fresh,
            coverage=source.coverage,
        )


class EvidenceIngest(BaseModel):
    source_id: uuid.UUID
    recorded_at: AwareDatetime
    kind: str = Field(min_length=2, max_length=32)
    assertion: str = Field(default="supports", max_length=16)
    content_text: str = Field(min_length=1, max_length=60_000)


class EvidenceOut(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    source_ref: str
    kind: str
    assertion: str
    recorded_at: AwareDatetime
    content_hash: str
    injection_suspected: bool
    content_text: str | None

    @classmethod
    def from_item(
        cls, item: EvidenceItem, source: EvidenceSource, *, include_content: bool
    ) -> "EvidenceOut":
        ref = item.content_ref or {}
        return cls(
            id=item.id,
            source_id=item.source_id,
            source_type=source.source_type,
            source_ref=source.system_ref,
            kind=ref.get("kind", "lainnya"),
            assertion=ref.get("assertion", "supports"),
            recorded_at=item.recorded_at,
            content_hash=item.content_hash,
            injection_suspected=item.injection_suspected,
            content_text=item.content_text if include_content else None,
        )
