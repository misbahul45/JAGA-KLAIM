from enum import StrEnum


class Role(StrEnum):
    CODER = "coder"
    VERIFIER = "verifier"
    FASKES_ADMIN = "faskes_admin"
    AUDITOR = "auditor"
    RULE_ADMIN = "rule_admin"
    RULE_APPROVER = "rule_approver"


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    CODING_SUBMITTED = "coding_submitted"
    UNDER_REVIEW = "under_review"
    NEEDS_CLARIFICATION = "needs_clarification"
    RETURNED_TO_CODER = "returned_to_coder"
    READY_TO_LOCK = "ready_to_lock"
    LOCKED = "locked"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunOutcome(StrEnum):
    NO_ACTION = "no_action"
    FINDINGS = "findings"
    ABSTAINED = "abstained"


class StepStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"


class VersionStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"
    REJECTED = "rejected"


class RuleUpdateStatus(StrEnum):
    PROPOSED = "proposed"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVATED = "activated"
    ROLLED_BACK = "rolled_back"


class Tier(StrEnum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class HealthStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class FindingStatus(StrEnum):
    VALID = "valid"
    DOWNGRADED = "downgraded"
    REJECTED = "rejected"


class CitationValidation(StrEnum):
    UNCHECKED = "unchecked"
    VALID = "valid"
    INVALID = "invalid"


class RuleValidation(StrEnum):
    UNVALIDATED = "belum_tervalidasi"
    SIMULATION = "simulasi"
    EXPERT_VALIDATED = "tervalidasi_pakar"


class Verdict(StrEnum):
    SUPPORTS_FINDING = "supports_finding"
    DOES_NOT_SUPPORT_FINDING = "does_not_support_finding"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FollowUp(StrEnum):
    PROCEED = "proceed"
    RETURN_TO_CODER = "return_to_coder"
    REQUEST_CLARIFICATION = "request_clarification"


class JobEvent(StrEnum):
    CODING_SUBMITTED = "coding.submitted"
    MANUAL_RERUN = "manual.rerun"


class RiskVectorCode(StrEnum):
    PHANTOM_BILLING = "phantom_billing"
    UPCODING = "upcoding"
    UNBUNDLING = "unbundling"


class CheckType(StrEnum):
    EVIDENCE_PRESENCE = "evidence_presence"
    SEVERITY_SUPPORT = "severity_support"
    BUNDLING_CONFLICT = "bundling_conflict"


def sql_values(enum_cls: type[StrEnum]) -> str:
    return ", ".join(f"'{member.value}'" for member in enum_cls)
