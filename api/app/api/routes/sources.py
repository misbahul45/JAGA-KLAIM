import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require
from app.api.schemas.evidence import SourceCreate, SourceOut, SourceUpdate
from app.db.session import SessionDep
from app.domain.permissions import Permission
from app.services import evidence as evidence_service
from app.services.auth import Principal

router = APIRouter(prefix="/v1/evidence-sources", tags=["evidence-sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.SOURCE_READ))],
) -> list[SourceOut]:
    return [SourceOut.from_source(s) for s in evidence_service.list_sources(session, principal)]


@router.post("", response_model=SourceOut, status_code=201)
def create_source(
    body: SourceCreate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.SOURCE_MANAGE))],
) -> SourceOut:
    source = evidence_service.create_source(
        session,
        principal,
        source_type=body.source_type,
        system_ref=body.system_ref,
        freshness_sla_seconds=body.freshness_sla_seconds,
        coverage=body.coverage,
    )
    return SourceOut.from_source(source)


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.SOURCE_MANAGE))],
) -> SourceOut:
    source = evidence_service.update_source(
        session,
        principal,
        source_id,
        health_status=body.health_status,
        last_synced_at=body.last_synced_at,
        is_enabled=body.is_enabled,
        freshness_sla_seconds=body.freshness_sla_seconds,
        coverage=body.coverage,
    )
    return SourceOut.from_source(source)
