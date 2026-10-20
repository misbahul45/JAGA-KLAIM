import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require
from app.api.mappers import job_out, run_detail_out
from app.api.schemas.claims import JobOut
from app.api.schemas.investigation import RunDetailOut
from app.db.session import SessionDep
from app.domain.permissions import Permission
from app.services import claims as claim_service
from app.services.auth import Principal
from app.services.run_detail import run_detail

router = APIRouter(prefix="/v1", tags=["investigations"])


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.INVESTIGATION_READ))],
) -> JobOut:
    return job_out(claim_service.get_job(session, principal, job_id))


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(
    job_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.INVESTIGATION_TRIGGER))],
) -> JobOut:
    return job_out(claim_service.cancel_job(session, principal, job_id))


@router.get("/investigations/{run_id}", response_model=RunDetailOut)
def get_run(
    run_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.INVESTIGATION_READ))],
) -> RunDetailOut:
    return run_detail_out(run_detail(session, principal, run_id))
