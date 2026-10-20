import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import conflict, not_found, unprocessable
from app.domain.enums import ClaimStatus, HealthStatus
from app.domain.hashing import content_hash
from app.domain.safety import looks_like_injection
from app.domain.specs import ASSERTIONS, EVIDENCE_KINDS, SOURCE_TYPES
from app.models import Claim, EvidenceItem, EvidenceSource
from app.models.base import utcnow
from app.services import audit
from app.services.auth import Principal
from app.services.claims import get_claim

MAX_CONTENT_CHARS = 50_000


def list_sources(session: Session, principal: Principal) -> list[EvidenceSource]:
    return list(
        session.exec(
            select(EvidenceSource)
            .where(EvidenceSource.faskes_id == principal.faskes_id)
            .order_by(col(EvidenceSource.source_type), col(EvidenceSource.system_ref))
        )
    )


def get_source(session: Session, principal: Principal, source_id: uuid.UUID) -> EvidenceSource:
    source = session.exec(
        select(EvidenceSource).where(
            EvidenceSource.id == source_id, EvidenceSource.faskes_id == principal.faskes_id
        )
    ).first()
    if source is None:
        raise not_found("Sumber bukti")
    return source


def create_source(
    session: Session,
    principal: Principal,
    *,
    source_type: str,
    system_ref: str,
    freshness_sla_seconds: int,
    coverage: dict[str, Any],
) -> EvidenceSource:
    if source_type not in SOURCE_TYPES:
        raise unprocessable("unknown_source_type", f"Tipe sumber tidak dikenal: {source_type}")
    taken = session.exec(
        select(EvidenceSource.id).where(
            EvidenceSource.faskes_id == principal.faskes_id, EvidenceSource.system_ref == system_ref
        )
    ).first()
    if taken is not None:
        raise conflict("source_exists", "Referensi sistem sumber sudah terdaftar")
    source = EvidenceSource(
        faskes_id=principal.faskes_id,
        source_type=source_type,
        system_ref=system_ref,
        freshness_sla_seconds=freshness_sla_seconds,
        coverage=coverage,
    )
    session.add(source)
    session.flush()
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="evidence_source",
        entity_id=source.id,
        event_type="source.created",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"source_type": source_type, "system_ref": system_ref},
    )
    session.commit()
    return source


def update_source(
    session: Session,
    principal: Principal,
    source_id: uuid.UUID,
    *,
    health_status: HealthStatus | None,
    last_synced_at: datetime | None,
    is_enabled: bool | None,
    freshness_sla_seconds: int | None,
    coverage: dict[str, Any] | None,
) -> EvidenceSource:
    source = get_source(session, principal, source_id)
    now = utcnow()
    changes: dict[str, Any] = {}
    if health_status is not None and health_status.value != source.health_status:
        changes["health_status"] = {"from": source.health_status, "to": health_status.value}
        source.health_status = health_status.value
    if last_synced_at is not None:
        if last_synced_at > now:
            raise unprocessable("sync_in_future", "Waktu sinkronisasi tidak boleh di masa depan")
        changes["last_synced_at"] = last_synced_at.isoformat()
        source.last_synced_at = last_synced_at
    if is_enabled is not None and is_enabled != source.is_enabled:
        changes["is_enabled"] = is_enabled
        source.is_enabled = is_enabled
    if freshness_sla_seconds is not None and freshness_sla_seconds != source.freshness_sla_seconds:
        changes["freshness_sla_seconds"] = freshness_sla_seconds
        source.freshness_sla_seconds = freshness_sla_seconds
    if coverage is not None:
        changes["coverage_updated"] = True
        source.coverage = coverage
    if changes:
        source.last_health_check_at = now
        session.add(source)
        audit.append_event(
            session,
            faskes_id=principal.faskes_id,
            entity_type="evidence_source",
            entity_id=source.id,
            event_type="source.updated",
            actor_type="user",
            actor_id=principal.user_id,
            payload=changes,
        )
        session.commit()
    return source


@dataclass(frozen=True)
class IngestResult:
    item: EvidenceItem
    created: bool


def ingest_evidence(
    session: Session,
    principal: Principal,
    claim_id: uuid.UUID,
    *,
    source_id: uuid.UUID,
    recorded_at: datetime,
    kind: str,
    assertion: str,
    content_text: str,
) -> IngestResult:
    claim = get_claim(session, principal, claim_id, for_update=True)
    if claim.status == ClaimStatus.LOCKED.value:
        raise conflict("claim_locked", "Klaim sudah dikunci")
    if kind not in EVIDENCE_KINDS:
        raise unprocessable("unknown_evidence_kind", f"Jenis bukti tidak dikenal: {kind}")
    if assertion not in ASSERTIONS:
        raise unprocessable("unknown_assertion", f"Nilai assertion tidak dikenal: {assertion}")
    text = content_text.strip()
    if not text:
        raise unprocessable("empty_content", "Isi bukti tidak boleh kosong")
    if len(text) > MAX_CONTENT_CHARS:
        raise unprocessable("content_too_large", f"Isi bukti maksimal {MAX_CONTENT_CHARS} karakter")
    if "\x00" in text:
        raise unprocessable("invalid_content", "Isi bukti mengandung karakter tidak valid")
    source = get_source(session, principal, source_id)
    if not source.is_enabled:
        raise conflict("source_disabled", "Sumber bukti sedang dinonaktifkan")

    digest = content_hash(text)
    existing = session.exec(
        select(EvidenceItem).where(
            EvidenceItem.claim_id == claim.id,
            EvidenceItem.source_id == source.id,
            EvidenceItem.content_hash == digest,
        )
    ).first()
    if existing is not None:
        return IngestResult(existing, False)

    suspected = looks_like_injection(text)
    item = EvidenceItem(
        faskes_id=claim.faskes_id,
        source_id=source.id,
        claim_id=claim.id,
        recorded_at=recorded_at,
        content_text=text,
        content_ref={"kind": kind, "assertion": assertion},
        content_hash=digest,
        injection_suspected=suspected,
    )
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise conflict("duplicate_evidence", "Bukti yang sama sudah tercatat") from exc
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="evidence_item",
        entity_id=item.id,
        event_type="evidence.ingested",
        actor_type="user",
        actor_id=principal.user_id,
        payload={
            "claim_id": claim.id,
            "source_id": source.id,
            "kind": kind,
            "assertion": assertion,
            "content_hash": digest,
            "injection_suspected": suspected,
        },
    )
    session.commit()
    return IngestResult(item, True)


def list_claim_evidence(
    session: Session, principal: Principal, claim_id: uuid.UUID
) -> tuple[Claim, list[tuple[EvidenceItem, EvidenceSource]]]:
    claim = get_claim(session, principal, claim_id)
    rows = session.exec(
        select(EvidenceItem, EvidenceSource)
        .join(EvidenceSource, col(EvidenceSource.id) == col(EvidenceItem.source_id))
        .where(EvidenceItem.claim_id == claim.id, EvidenceItem.faskes_id == principal.faskes_id)
        .order_by(col(EvidenceItem.recorded_at))
    ).all()
    return claim, list(rows)
