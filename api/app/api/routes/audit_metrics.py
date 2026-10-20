import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel

from app.api.deps import require
from app.api.schemas.common import Page
from app.db.session import SessionDep
from app.domain.permissions import Permission
from app.services import audit
from app.services.audit_query import query_audit_log
from app.services.auth import Principal
from app.services.metrics import compute_metrics, dashboard

router = APIRouter(prefix="/v1", tags=["audit-metrics"])


class AuditEntryOut(BaseModel):
    id: uuid.UUID
    seq: int
    created_at: AwareDatetime
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    actor_type: str
    actor_id: uuid.UUID | None
    payload: dict[str, Any]
    prev_hash: str | None
    record_hash: str


class ChainOut(BaseModel):
    valid: bool
    checked: int
    first_invalid_seq: int | None
    reason: str | None


class MetricOut(BaseModel):
    code: str
    label: str
    definition: str
    unit: str
    target: str | None
    status: str
    value: float | None
    numerator: float | None
    denominator: float | None
    sample_size: int
    note: str | None
    breakdown: dict[str, Any]
    window_start: AwareDatetime
    window_end: AwareDatetime


class DashboardOut(BaseModel):
    claims_by_status: dict[str, int]
    jobs_by_status: dict[str, int]
    open_review_by_tier: dict[str, int]
    run_outcomes_30d: dict[str, int]
    sources: list[dict[str, Any]]
    generated_at: AwareDatetime


@router.get("/audit-log", response_model=Page[AuditEntryOut])
def get_audit_log(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.AUDIT_READ))],
    event_type: Annotated[str | None, Query(max_length=64)] = None,
    entity_type: Annotated[str | None, Query(max_length=64)] = None,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    created_from: AwareDatetime | None = None,
    created_to: AwareDatetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[AuditEntryOut]:
    rows, total = query_audit_log(
        session,
        principal,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return Page[AuditEntryOut](
        items=[AuditEntryOut.model_validate(r, from_attributes=True) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/audit-log/verify", response_model=ChainOut)
def verify_audit_chain(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.AUDIT_READ))],
) -> ChainOut:
    result = audit.verify_chain(session, principal.faskes_id)
    return ChainOut(
        valid=result.valid,
        checked=result.checked,
        first_invalid_seq=result.first_invalid_seq,
        reason=result.reason,
    )


@router.get("/metrics", response_model=list[MetricOut])
def get_metrics(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.METRICS_READ))],
    window_start: AwareDatetime | None = None,
    window_end: AwareDatetime | None = None,
) -> list[MetricOut]:
    return [
        MetricOut(**m.__dict__)
        for m in compute_metrics(
            session, principal, window_start=window_start, window_end=window_end
        )
    ]


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_READ))],
) -> DashboardOut:
    summary = dashboard(session, principal)
    return DashboardOut(**summary.__dict__)

