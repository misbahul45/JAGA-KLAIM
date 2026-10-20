import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import require
from app.api.mappers import (
    assessment_out,
    intervention_detail_out,
    queue_item_out,
    verdict_out,
)
from app.api.schemas.common import Page
from app.api.schemas.review import (
    AssessmentIn,
    AssessmentOut,
    InterventionDetailOut,
    QueueItemOut,
    VerdictIn,
    VerdictOut,
)
from app.db.session import SessionDep
from app.domain.enums import Tier
from app.domain.permissions import Permission
from app.services import review as review_service
from app.services.auth import Principal

router = APIRouter(prefix="/v1/interventions", tags=["review"])

REVIEW_TIER_VALUES = [Tier.T2.value, Tier.T3.value]


@router.get("", response_model=Page[QueueItemOut])
def list_queue(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW_READ))],
    tier: Annotated[list[Tier] | None, Query()] = None,
    state: Literal["open", "resolved", "all"] = "open",
    vector: Annotated[str | None, Query(max_length=32)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[QueueItemOut]:
    tiers = [t.value for t in tier] if tier else REVIEW_TIER_VALUES
    rows, total = review_service.list_queue(
        session,
        principal,
        tiers=tiers,
        state=state,
        vector=vector,
        page=page,
        page_size=page_size,
    )
    return Page[QueueItemOut](
        items=[queue_item_out(r) for r in rows], page=page, page_size=page_size, total=total
    )


@router.get("/{intervention_id}", response_model=InterventionDetailOut)
def get_intervention(
    intervention_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW_READ))],
) -> InterventionDetailOut:
    detail = review_service.intervention_detail(session, principal, intervention_id)
    return intervention_detail_out(detail, principal)


@router.post("/{intervention_id}/assessment", response_model=AssessmentOut, status_code=201)
def submit_assessment(
    intervention_id: uuid.UUID,
    body: AssessmentIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW_ASSESS))],
) -> AssessmentOut:
    return assessment_out(
        review_service.submit_assessment(
            session, principal, intervention_id, self_verdict=body.self_verdict, note=body.note
        )
    )


@router.post("/{intervention_id}/verdict", response_model=VerdictOut, status_code=201)
def submit_verdict(
    intervention_id: uuid.UUID,
    body: VerdictIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW_VERDICT))],
) -> VerdictOut:
    return verdict_out(
        review_service.submit_verdict(
            session,
            principal,
            intervention_id,
            verdict=body.verdict,
            follow_up=body.follow_up,
            rationale=body.rationale,
        )
    )


@router.post("/{intervention_id}/verdict/correction", response_model=VerdictOut, status_code=201)
def correct_verdict(
    intervention_id: uuid.UUID,
    body: VerdictIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW_VERDICT))],
) -> VerdictOut:
    return verdict_out(
        review_service.correct_verdict(
            session,
            principal,
            intervention_id,
            verdict=body.verdict,
            follow_up=body.follow_up,
            rationale=body.rationale,
        )
    )
