import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import AuditLog
from app.services.auth import Principal


def query_audit_log(
    session: Session,
    principal: Principal,
    *,
    event_type: str | None,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    created_from: datetime | None,
    created_to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[AuditLog], int]:
    conditions = [AuditLog.faskes_id == principal.faskes_id]
    if event_type:
        conditions.append(AuditLog.event_type == event_type)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if actor_id:
        conditions.append(AuditLog.actor_id == actor_id)
    if created_from:
        conditions.append(AuditLog.created_at >= created_from)
    if created_to:
        conditions.append(AuditLog.created_at <= created_to)
    total = session.exec(select(func.count()).select_from(AuditLog).where(*conditions)).one()
    rows = list(
        session.exec(
            select(AuditLog)
            .where(*conditions)
            .order_by(col(AuditLog.seq).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total
