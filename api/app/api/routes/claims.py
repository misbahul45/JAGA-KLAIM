import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response

from app.api.deps import require
from app.api.mappers import claim_detail_out, claim_list_item, claim_out, job_out
from app.api.schemas.claims import (
    ClaimCreate,
    ClaimDetailOut,
    ClaimListItem,
    ClaimOut,
    ClaimSortField,
    ClaimUpdate,
    JobOut,
    LockRequest,
    RerunRequest,
)
from app.api.schemas.common import Page
from app.api.schemas.evidence import EvidenceIngest, EvidenceOut
from app.db.session import SessionDep
from app.domain.enums import ClaimStatus
from app.domain.permissions import Permission
from app.services import claims as claim_service
from app.services import evidence as evidence_service
from app.services.auth import Principal

router = APIRouter(prefix="/v1/claims", tags=["claims"])

IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.get("", response_model=Page[ClaimListItem])
def list_claims(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_READ))],
    status: ClaimStatus | None = None,
    q: Annotated[str | None, Query(max_length=64)] = None,
    tier: Annotated[str | None, Query(pattern="^T[0-3]$")] = None,
    vector: Annotated[str | None, Query(max_length=32)] = None,
    sort: ClaimSortField = "updated_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ClaimListItem]:
    rows, total = claim_service.list_claims(
        session,
        principal,
        status=status.value if status else None,
        q=q,
        tier=tier,
        vector=vector,
        updated_from=None,
        updated_to=None,
        sort=sort,
        descending=order == "desc",
        page=page,
        page_size=page_size,
    )
    return Page[ClaimListItem](
        items=[claim_list_item(r) for r in rows], page=page, page_size=page_size, total=total
    )


@router.post("", response_model=ClaimOut, status_code=201)
def create_claim(
    body: ClaimCreate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_WRITE))],
) -> ClaimOut:
    claim = claim_service.create_claim(
        session,
        principal,
        episode_no=body.episode_no,
        patient_pseudonym=body.patient_pseudonym,
        codes=[c.to_spec() for c in body.codes],
        episode_start=body.episode_start,
        episode_end=body.episode_end,
    )
    return claim_out(claim, claim_service.current_codes(session, claim.id))


@router.get("/{claim_id}", response_model=ClaimDetailOut)
def get_claim(
    claim_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_READ))],
) -> ClaimDetailOut:
    return claim_detail_out(claim_service.claim_detail(session, principal, claim_id))


@router.patch("/{claim_id}", response_model=ClaimOut)
def update_claim(
    claim_id: uuid.UUID,
    body: ClaimUpdate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_WRITE))],
) -> ClaimOut:
    claim = claim_service.update_claim(
        session,
        principal,
        claim_id,
        expected_version=body.expected_version,
        codes=[c.to_spec() for c in body.codes] if body.codes is not None else None,
        episode_start=body.episode_start,
        episode_end=body.episode_end,
        set_episode=bool({"episode_start", "episode_end"} & body.model_fields_set),
    )
    return claim_out(claim, claim_service.current_codes(session, claim.id))


@router.post("/{claim_id}/submit-coding", response_model=JobOut)
def submit_coding(
    claim_id: uuid.UUID,
    response: Response,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_SUBMIT))],
    idempotency_key: IdempotencyKey = None,
) -> JobOut:
    job, replayed = claim_service.submit_coding(
        session, principal, claim_id, idempotency_key=idempotency_key
    )
    response.status_code = 200 if replayed else 202
    return job_out(job, replay=replayed)


@router.post("/{claim_id}/investigations", response_model=JobOut)
def request_rerun(
    claim_id: uuid.UUID,
    body: RerunRequest,
    response: Response,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.INVESTIGATION_TRIGGER))],
    idempotency_key: IdempotencyKey = None,
) -> JobOut:
    job, replayed = claim_service.request_rerun(
        session, principal, claim_id, reason=body.reason, idempotency_key=idempotency_key
    )
    response.status_code = 200 if replayed else 202
    return job_out(job, replay=replayed)


@router.post("/{claim_id}/lock", response_model=ClaimOut)
def lock_claim(
    claim_id: uuid.UUID,
    body: LockRequest,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.CLAIM_LOCK))],
) -> ClaimOut:
    claim = claim_service.lock_claim(
        session, principal, claim_id, acknowledge_limitations=body.acknowledge_limitations
    )
    return claim_out(claim, claim_service.current_codes(session, claim.id))


@router.get("/{claim_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(
    claim_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.EVIDENCE_READ))],
) -> list[EvidenceOut]:
    _, rows = evidence_service.list_claim_evidence(session, principal, claim_id)
    include_content = principal.can(Permission.EVIDENCE_CONTENT)
    return [EvidenceOut.from_item(i, s, include_content=include_content) for i, s in rows]


@router.post("/{claim_id}/evidence", response_model=EvidenceOut)
def ingest_evidence(
    claim_id: uuid.UUID,
    body: EvidenceIngest,
    response: Response,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.EVIDENCE_INGEST))],
) -> EvidenceOut:
    result = evidence_service.ingest_evidence(
        session,
        principal,
        claim_id,
        source_id=body.source_id,
        recorded_at=body.recorded_at,
        kind=body.kind,
        assertion=body.assertion,
        content_text=body.content_text,
    )
    response.status_code = 201 if result.created else 200
    source = evidence_service.get_source(session, principal, result.item.source_id)
    return EvidenceOut.from_item(
        result.item, source, include_content=principal.can(Permission.EVIDENCE_CONTENT)
    )
