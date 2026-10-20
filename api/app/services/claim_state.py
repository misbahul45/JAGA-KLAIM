import uuid

from sqlalchemy import exists, func
from sqlmodel import Session, col, select

from app.domain.enums import ClaimStatus, FollowUp, Tier
from app.domain.states import CLAIM_TRANSITIONS, ensure_transition
from app.models import Claim, EvidenceItem, HumanVerdict, Intervention, InvestigationRun
from app.services import audit

REVIEW_TIERS = (Tier.T2.value, Tier.T3.value)
RECOMPUTABLE = frozenset(
    {
        ClaimStatus.CODING_SUBMITTED,
        ClaimStatus.UNDER_REVIEW,
        ClaimStatus.READY_TO_LOCK,
        ClaimStatus.NEEDS_CLARIFICATION,
        ClaimStatus.RETURNED_TO_CODER,
    }
)


def current_run_ids(session: Session, claim: Claim) -> list[uuid.UUID]:
    return list(
        session.exec(
            select(InvestigationRun.id).where(
                InvestigationRun.claim_id == claim.id,
                InvestigationRun.claim_version == claim.version,
                col(InvestigationRun.stale_at).is_(None),
            )
        )
    )


def open_review_count(session: Session, claim: Claim) -> int:
    run_ids = current_run_ids(session, claim)
    if not run_ids:
        return 0
    return session.exec(
        select(func.count())
        .select_from(Intervention)
        .where(
            col(Intervention.run_id).in_(run_ids),
            col(Intervention.tier).in_(REVIEW_TIERS),
            col(Intervention.resolved_at).is_(None),
        )
    ).one()


def current_follow_ups(session: Session, claim: Claim) -> set[str]:
    run_ids = current_run_ids(session, claim)
    if not run_ids:
        return set()
    superseded = (
        select(HumanVerdict.supersedes_verdict_id)
        .where(col(HumanVerdict.supersedes_verdict_id).is_not(None))
        .scalar_subquery()
    )
    return set(
        session.exec(
            select(HumanVerdict.follow_up)
            .join(Intervention, col(Intervention.id) == col(HumanVerdict.intervention_id))
            .where(
                col(Intervention.run_id).in_(run_ids),
                col(HumanVerdict.id).not_in(superseded),
            )
        )
    )


def has_stale_evidence(session: Session, claim: Claim) -> bool:
    latest_run_start = session.exec(
        select(func.max(InvestigationRun.started_at)).where(
            InvestigationRun.claim_id == claim.id,
            InvestigationRun.claim_version == claim.version,
            col(InvestigationRun.stale_at).is_(None),
        )
    ).one()
    if latest_run_start is None:
        return False
    return session.exec(
        select(
            exists().where(
                col(EvidenceItem.claim_id) == claim.id,
                col(EvidenceItem.created_at) > latest_run_start,
            )
        )
    ).one()


def desired_status(session: Session, claim: Claim) -> ClaimStatus:
    follow_ups = current_follow_ups(session, claim)
    if FollowUp.RETURN_TO_CODER.value in follow_ups:
        return ClaimStatus.RETURNED_TO_CODER
    if FollowUp.REQUEST_CLARIFICATION.value in follow_ups:
        return ClaimStatus.NEEDS_CLARIFICATION
    if open_review_count(session, claim) > 0:
        return ClaimStatus.UNDER_REVIEW
    return ClaimStatus.READY_TO_LOCK


def transition_claim(
    session: Session,
    claim: Claim,
    target: ClaimStatus,
    *,
    actor_type: str,
    actor_id: uuid.UUID | None,
    reason: str,
) -> bool:
    current = ClaimStatus(claim.status)
    if current is target:
        return False
    ensure_transition("klaim", CLAIM_TRANSITIONS, current, target)
    claim.status = target.value
    session.add(claim)
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="claim",
        entity_id=claim.id,
        event_type="claim.status_changed",
        actor_type=actor_type,
        actor_id=actor_id,
        payload={"from": current.value, "to": target.value, "reason": reason, "version": claim.version},
    )
    return True


def sync_claim_status(
    session: Session,
    claim: Claim,
    *,
    actor_type: str,
    actor_id: uuid.UUID | None,
    reason: str,
) -> bool:
    if ClaimStatus(claim.status) not in RECOMPUTABLE:
        return False
    target = desired_status(session, claim)
    return transition_claim(
        session, claim, target, actor_type=actor_type, actor_id=actor_id, reason=reason
    )
