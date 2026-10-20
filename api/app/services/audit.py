import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, col, select

from app.domain.hashing import canonical_json, sha256_hex
from app.models import AuditLog
from app.models.base import utcnow


def _jsonable(value: Any) -> Any:
    return json.loads(canonical_json(value))


def compute_record_hash(
    *,
    faskes_id: uuid.UUID,
    seq: int,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    actor_type: str,
    actor_id: uuid.UUID | None,
    prev_hash: str | None,
    created_at: datetime,
) -> str:
    return sha256_hex(
        canonical_json(
            {
                "faskes_id": faskes_id,
                "seq": seq,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "payload": payload,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "prev_hash": prev_hash,
                "created_at": created_at.astimezone(UTC),
            }
        )
    )


def append_event(
    session: Session,
    *,
    faskes_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: str,
    actor_type: str,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"audit:{faskes_id}"},
    )
    last = session.exec(
        select(AuditLog.seq, AuditLog.record_hash)
        .where(AuditLog.faskes_id == faskes_id)
        .order_by(col(AuditLog.seq).desc())
        .limit(1)
    ).first()
    seq = 1 if last is None else last[0] + 1
    prev_hash = None if last is None else last[1]
    clean_payload = _jsonable(payload or {})
    created_at = utcnow()
    record = AuditLog(
        faskes_id=faskes_id,
        seq=seq,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload=clean_payload,
        actor_type=actor_type,
        actor_id=actor_id,
        prev_hash=prev_hash,
        created_at=created_at,
        record_hash=compute_record_hash(
            faskes_id=faskes_id,
            seq=seq,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=clean_payload,
            actor_type=actor_type,
            actor_id=actor_id,
            prev_hash=prev_hash,
            created_at=created_at,
        ),
    )
    session.add(record)
    session.flush()
    return record


@dataclass(frozen=True)
class ChainVerification:
    valid: bool
    checked: int
    first_invalid_seq: int | None
    reason: str | None


def verify_chain(session: Session, faskes_id: uuid.UUID) -> ChainVerification:
    rows = session.exec(
        select(AuditLog).where(AuditLog.faskes_id == faskes_id).order_by(col(AuditLog.seq))
    )
    expected_seq = 1
    previous_hash: str | None = None
    checked = 0
    for row in rows:
        checked += 1
        if row.seq != expected_seq:
            return ChainVerification(False, checked, row.seq, "urutan seq tidak berlanjut")
        if row.prev_hash != previous_hash:
            return ChainVerification(False, checked, row.seq, "prev_hash tidak cocok dengan catatan sebelumnya")
        recomputed = compute_record_hash(
            faskes_id=row.faskes_id,
            seq=row.seq,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            event_type=row.event_type,
            payload=row.payload,
            actor_type=row.actor_type,
            actor_id=row.actor_id,
            prev_hash=row.prev_hash,
            created_at=row.created_at,
        )
        if recomputed != row.record_hash:
            return ChainVerification(False, checked, row.seq, "record_hash tidak cocok dengan isi catatan")
        previous_hash = row.record_hash
        expected_seq += 1
    return ChainVerification(True, checked, None, None)
