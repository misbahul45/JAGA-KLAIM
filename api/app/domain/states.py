from enum import StrEnum

from app.domain.enums import (
    ClaimStatus,
    JobStatus,
    RuleUpdateStatus,
    RunStatus,
    VersionStatus,
)


class InvalidTransition(Exception):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(f"{entity}: transisi {current} -> {target} tidak diizinkan")
        self.entity = entity
        self.current = current
        self.target = target


CLAIM_TRANSITIONS: dict[ClaimStatus, frozenset[ClaimStatus]] = {
    ClaimStatus.DRAFT: frozenset({ClaimStatus.CODING_SUBMITTED}),
    ClaimStatus.CODING_SUBMITTED: frozenset(
        {
            ClaimStatus.UNDER_REVIEW,
            ClaimStatus.READY_TO_LOCK,
            ClaimStatus.DRAFT,
        }
    ),
    ClaimStatus.UNDER_REVIEW: frozenset(
        {
            ClaimStatus.READY_TO_LOCK,
            ClaimStatus.NEEDS_CLARIFICATION,
            ClaimStatus.RETURNED_TO_CODER,
        }
    ),
    ClaimStatus.NEEDS_CLARIFICATION: frozenset(
        {
            ClaimStatus.DRAFT,
            ClaimStatus.CODING_SUBMITTED,
            ClaimStatus.READY_TO_LOCK,
            ClaimStatus.UNDER_REVIEW,
            ClaimStatus.RETURNED_TO_CODER,
        }
    ),
    ClaimStatus.RETURNED_TO_CODER: frozenset(
        {
            ClaimStatus.DRAFT,
            ClaimStatus.UNDER_REVIEW,
            ClaimStatus.READY_TO_LOCK,
            ClaimStatus.NEEDS_CLARIFICATION,
        }
    ),
    ClaimStatus.READY_TO_LOCK: frozenset(
        {
            ClaimStatus.LOCKED,
            ClaimStatus.DRAFT,
            ClaimStatus.UNDER_REVIEW,
            ClaimStatus.NEEDS_CLARIFICATION,
            ClaimStatus.RETURNED_TO_CODER,
        }
    ),
    ClaimStatus.LOCKED: frozenset(),
}

JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset(
        {JobStatus.PROCESSING, JobStatus.CANCELLED, JobStatus.STALE}
    ),
    JobStatus.PROCESSING: frozenset(
        {
            JobStatus.SUCCEEDED,
            JobStatus.PARTIAL,
            JobStatus.FAILED,
            JobStatus.QUEUED,
            JobStatus.STALE,
        }
    ),
    JobStatus.FAILED: frozenset({JobStatus.QUEUED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.PARTIAL: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.STALE: frozenset(),
}

RUN_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.PARTIAL: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}

VERSION_TRANSITIONS: dict[VersionStatus, frozenset[VersionStatus]] = {
    VersionStatus.DRAFT: frozenset({VersionStatus.PENDING_APPROVAL}),
    VersionStatus.PENDING_APPROVAL: frozenset(
        {VersionStatus.APPROVED, VersionStatus.REJECTED, VersionStatus.DRAFT}
    ),
    VersionStatus.APPROVED: frozenset({VersionStatus.ACTIVE}),
    VersionStatus.ACTIVE: frozenset({VersionStatus.RETIRED}),
    VersionStatus.RETIRED: frozenset(),
    VersionStatus.REJECTED: frozenset(),
}

RULE_UPDATE_TRANSITIONS: dict[RuleUpdateStatus, frozenset[RuleUpdateStatus]] = {
    RuleUpdateStatus.PROPOSED: frozenset(
        {RuleUpdateStatus.EVALUATING, RuleUpdateStatus.REJECTED}
    ),
    RuleUpdateStatus.EVALUATING: frozenset(
        {RuleUpdateStatus.EVALUATED, RuleUpdateStatus.REJECTED}
    ),
    RuleUpdateStatus.EVALUATED: frozenset(
        {RuleUpdateStatus.APPROVED, RuleUpdateStatus.REJECTED}
    ),
    RuleUpdateStatus.APPROVED: frozenset({RuleUpdateStatus.ACTIVATED}),
    RuleUpdateStatus.ACTIVATED: frozenset({RuleUpdateStatus.ROLLED_BACK}),
    RuleUpdateStatus.REJECTED: frozenset(),
    RuleUpdateStatus.ROLLED_BACK: frozenset(),
}


def ensure_transition[S: StrEnum](
    entity: str, table: dict[S, frozenset[S]], current: S, target: S
) -> None:
    if target not in table[current]:
        raise InvalidTransition(entity, current.value, target.value)
