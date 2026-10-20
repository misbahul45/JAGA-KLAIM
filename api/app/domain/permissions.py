from enum import StrEnum

from app.domain.enums import Role


class Permission(StrEnum):
    CLAIM_READ = "claim:read"
    CLAIM_WRITE = "claim:write"
    CLAIM_SUBMIT = "claim:submit"
    CLAIM_LOCK = "claim:lock"
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_CONTENT = "evidence:content"
    EVIDENCE_INGEST = "evidence:ingest"
    SOURCE_READ = "source:read"
    SOURCE_MANAGE = "source:manage"
    INVESTIGATION_READ = "investigation:read"
    INVESTIGATION_TRIGGER = "investigation:trigger"
    REVIEW_READ = "review:read"
    REVIEW_ASSESS = "review:assess"
    REVIEW_VERDICT = "review:verdict"
    RULE_READ = "rule:read"
    RULE_WRITE = "rule:write"
    RULE_APPROVE = "rule:approve"
    RULE_UPDATE_PROPOSE = "rule_update:propose"
    AUDIT_READ = "audit:read"
    METRICS_READ = "metrics:read"
    USER_MANAGE = "user:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.CODER: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.CLAIM_WRITE,
            Permission.CLAIM_SUBMIT,
            Permission.EVIDENCE_READ,
            Permission.EVIDENCE_CONTENT,
            Permission.SOURCE_READ,
            Permission.INVESTIGATION_READ,
            Permission.INVESTIGATION_TRIGGER,
            Permission.REVIEW_READ,
            Permission.RULE_READ,
        }
    ),
    Role.VERIFIER: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.CLAIM_LOCK,
            Permission.EVIDENCE_READ,
            Permission.EVIDENCE_CONTENT,
            Permission.SOURCE_READ,
            Permission.INVESTIGATION_READ,
            Permission.INVESTIGATION_TRIGGER,
            Permission.REVIEW_READ,
            Permission.REVIEW_ASSESS,
            Permission.REVIEW_VERDICT,
            Permission.RULE_READ,
            Permission.RULE_UPDATE_PROPOSE,
            Permission.METRICS_READ,
        }
    ),
    Role.FASKES_ADMIN: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.EVIDENCE_READ,
            Permission.EVIDENCE_INGEST,
            Permission.SOURCE_READ,
            Permission.SOURCE_MANAGE,
            Permission.INVESTIGATION_READ,
            Permission.REVIEW_READ,
            Permission.RULE_READ,
            Permission.AUDIT_READ,
            Permission.METRICS_READ,
            Permission.USER_MANAGE,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.EVIDENCE_READ,
            Permission.SOURCE_READ,
            Permission.INVESTIGATION_READ,
            Permission.REVIEW_READ,
            Permission.RULE_READ,
            Permission.AUDIT_READ,
            Permission.METRICS_READ,
        }
    ),
    Role.RULE_ADMIN: frozenset(
        {
            Permission.RULE_READ,
            Permission.RULE_WRITE,
            Permission.METRICS_READ,
        }
    ),
    Role.RULE_APPROVER: frozenset(
        {
            Permission.RULE_READ,
            Permission.RULE_APPROVE,
            Permission.AUDIT_READ,
            Permission.METRICS_READ,
        }
    ),
}

FASKES_ASSIGNABLE_ROLES: frozenset[Role] = frozenset(
    {Role.CODER, Role.VERIFIER, Role.FASKES_ADMIN, Role.AUDITOR}
)


def permissions_for(role: str) -> frozenset[Permission]:
    try:
        return ROLE_PERMISSIONS[Role(role)]
    except ValueError:
        return frozenset()
