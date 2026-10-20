import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require
from app.api.schemas.governance import (
    ApprovalBody,
    ExpectedRuleOut,
    PolicyPreviewIn,
    PolicyPreviewOut,
    PolicyRuleOut,
    PolicyVersionCreate,
    PolicyVersionOut,
    ReasonBody,
    RiskVectorOut,
    RuleSetOut,
    RuleUpdateOut,
    RuleUpdateProposal,
    RuleVersionBrief,
    RuleVersionCreate,
    RuleVersionOut,
)
from app.db.session import SessionDep
from app.domain.enums import VersionStatus
from app.domain.permissions import Permission
from app.models import PolicyRule, PolicyVersion, RuleUpdate, RuleVersion
from app.services import governance as service
from app.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["governance"])

Reader = Annotated[Principal, Depends(require(Permission.RULE_READ))]
Author = Annotated[Principal, Depends(require(Permission.RULE_WRITE))]
Approver = Annotated[Principal, Depends(require(Permission.RULE_APPROVE))]
Proposer = Annotated[Principal, Depends(require(Permission.RULE_UPDATE_PROPOSE))]


def version_brief(version: RuleVersion) -> RuleVersionBrief:
    return RuleVersionBrief.model_validate(version, from_attributes=True)


def policy_out(version: PolicyVersion, rules: list[PolicyRule]) -> PolicyVersionOut:
    return PolicyVersionOut(
        id=version.id,
        version=version.version,
        status=version.status,
        config_hash=version.config_hash,
        created_by=version.created_by,
        approved_by=version.approved_by,
        approved_at=version.approved_at,
        activated_at=version.activated_at,
        rules=[
            PolicyRuleOut(
                id=r.id,
                code=r.code,
                tier=r.tier,
                priority=r.priority,
                condition=r.condition_spec,
                is_active=r.is_active,
            )
            for r in rules
        ],
    )


def update_out(update: RuleUpdate, basis: list[uuid.UUID]) -> RuleUpdateOut:
    return RuleUpdateOut(
        id=update.id,
        status=update.status,
        basis_verdict_ids=basis,
        base_rule_version_id=update.base_rule_version_id,
        result_rule_version_id=update.result_rule_version_id,
        proposed_by=update.proposed_by,
        decided_by=update.decided_by,
        proposed_change=update.proposed_change,
        evaluation=update.evaluation,
        created_at=update.created_at,
        evaluated_at=update.evaluated_at,
        decided_at=update.decided_at,
    )


def rule_version_out(session: SessionDep, version_id: uuid.UUID) -> RuleVersionOut:
    version, rule_set, vector, rules = service.get_rule_version(session, version_id)
    return RuleVersionOut(
        **version_brief(version).model_dump(),
        rule_set_id=rule_set.id,
        rule_set_name=rule_set.name,
        vector_code=vector.code,
        expected_rules=[
            ExpectedRuleOut(id=r.id, code_pattern=r.code_pattern, spec=r.expected_evidence_spec, is_active=r.is_active)
            for r in rules
        ],
    )


@router.get("/risk-vectors", response_model=list[RiskVectorOut])
def list_vectors(session: SessionDep, _: Reader) -> list[RiskVectorOut]:
    return [RiskVectorOut.model_validate(v, from_attributes=True) for v in service.list_vectors(session)]


@router.get("/rule-sets", response_model=list[RuleSetOut])
def list_rule_sets(session: SessionDep, _: Reader) -> list[RuleSetOut]:
    return [
        RuleSetOut(
            id=view.rule_set.id,
            name=view.rule_set.name,
            description=view.rule_set.description,
            vector=RiskVectorOut.model_validate(view.vector, from_attributes=True),
            active_version_id=next(
                (v.id for v in view.versions if v.status == VersionStatus.ACTIVE.value), None
            ),
            versions=[version_brief(v) for v in view.versions],
        )
        for view in service.list_rule_sets(session)
    ]


@router.get("/rule-versions/{version_id}", response_model=RuleVersionOut)
def get_rule_version(version_id: uuid.UUID, session: SessionDep, _: Reader) -> RuleVersionOut:
    return rule_version_out(session, version_id)


@router.post("/rule-versions", response_model=RuleVersionOut, status_code=201)
def create_rule_version(body: RuleVersionCreate, session: SessionDep, principal: Author) -> RuleVersionOut:
    version = service.create_rule_version(
        session,
        principal,
        rule_set_id=body.rule_set_id,
        version=body.version,
        validation_status=body.validation_status,
        base_version_id=body.base_version_id,
        expected_rules=[(r.code_pattern, r.spec) for r in body.expected_rules],
    )
    return rule_version_out(session, version.id)


@router.post("/rule-versions/{version_id}/submit", response_model=RuleVersionOut)
def submit_rule_version(version_id: uuid.UUID, session: SessionDep, principal: Author) -> RuleVersionOut:
    service.submit_rule_version(session, principal, version_id)
    return rule_version_out(session, version_id)


@router.post("/rule-versions/{version_id}/approve", response_model=RuleVersionOut)
def approve_rule_version(
    version_id: uuid.UUID, body: ApprovalBody, session: SessionDep, principal: Approver
) -> RuleVersionOut:
    service.approve_rule_version(
        session,
        principal,
        version_id,
        validation_status=body.validation_status,
        expert_validation_confirmed=body.expert_validation_confirmed,
        note=body.note,
    )
    return rule_version_out(session, version_id)


@router.post("/rule-versions/{version_id}/reject", response_model=RuleVersionOut)
def reject_rule_version(
    version_id: uuid.UUID, body: ReasonBody, session: SessionDep, principal: Approver
) -> RuleVersionOut:
    service.reject_rule_version(session, principal, version_id, reason=body.reason)
    return rule_version_out(session, version_id)


@router.post("/rule-versions/{version_id}/activate", response_model=RuleVersionOut)
def activate_rule_version(version_id: uuid.UUID, session: SessionDep, principal: Approver) -> RuleVersionOut:
    service.activate_rule_version(session, principal, version_id)
    return rule_version_out(session, version_id)


@router.post("/rule-versions/{version_id}/retire", response_model=RuleVersionOut)
def retire_rule_version(version_id: uuid.UUID, session: SessionDep, principal: Approver) -> RuleVersionOut:
    service.retire_rule_version(session, principal, version_id)
    return rule_version_out(session, version_id)


@router.get("/policy-versions", response_model=list[PolicyVersionOut])
def list_policy_versions(session: SessionDep, _: Reader) -> list[PolicyVersionOut]:
    return [policy_out(*service.get_policy_version(session, v.id)) for v in service.list_policy_versions(session)]


@router.get("/policy-versions/{version_id}", response_model=PolicyVersionOut)
def get_policy_version(version_id: uuid.UUID, session: SessionDep, _: Reader) -> PolicyVersionOut:
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions", response_model=PolicyVersionOut, status_code=201)
def create_policy_version(body: PolicyVersionCreate, session: SessionDep, principal: Author) -> PolicyVersionOut:
    version = service.create_policy_version(
        session,
        principal,
        version=body.version,
        rules=[
            {"code": r.code, "tier": r.tier.value, "priority": r.priority, "condition": r.condition}
            for r in body.rules
        ],
    )
    return policy_out(*service.get_policy_version(session, version.id))


@router.post("/policy-versions/{version_id}/submit", response_model=PolicyVersionOut)
def submit_policy_version(version_id: uuid.UUID, session: SessionDep, principal: Author) -> PolicyVersionOut:
    service.submit_policy_version(session, principal, version_id)
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions/{version_id}/approve", response_model=PolicyVersionOut)
def approve_policy_version(version_id: uuid.UUID, session: SessionDep, principal: Approver) -> PolicyVersionOut:
    service.approve_policy_version(session, principal, version_id)
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions/{version_id}/reject", response_model=PolicyVersionOut)
def reject_policy_version(
    version_id: uuid.UUID, body: ReasonBody, session: SessionDep, principal: Approver
) -> PolicyVersionOut:
    service.reject_policy_version(session, principal, version_id, reason=body.reason)
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions/{version_id}/activate", response_model=PolicyVersionOut)
def activate_policy_version(version_id: uuid.UUID, session: SessionDep, principal: Approver) -> PolicyVersionOut:
    service.activate_policy_version(session, principal, version_id)
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions/{version_id}/retire", response_model=PolicyVersionOut)
def retire_policy_version(version_id: uuid.UUID, session: SessionDep, principal: Approver) -> PolicyVersionOut:
    service.retire_policy_version(session, principal, version_id)
    return policy_out(*service.get_policy_version(session, version_id))


@router.post("/policy-versions/{version_id}/preview", response_model=PolicyPreviewOut)
def preview_policy(
    version_id: uuid.UUID, body: PolicyPreviewIn, session: SessionDep, _: Reader
) -> PolicyPreviewOut:
    return PolicyPreviewOut(**service.preview_policy(session, version_id, body.facts))


@router.get("/rule-updates", response_model=list[RuleUpdateOut])
def list_rule_updates(session: SessionDep, principal: Reader) -> list[RuleUpdateOut]:
    return [update_out(*service.get_rule_update(session, principal, u.id)) for u in service.list_rule_updates(session, principal)]


@router.get("/rule-updates/{update_id}", response_model=RuleUpdateOut)
def get_rule_update(update_id: uuid.UUID, session: SessionDep, principal: Reader) -> RuleUpdateOut:
    return update_out(*service.get_rule_update(session, principal, update_id))


@router.post("/rule-updates", response_model=RuleUpdateOut, status_code=201)
def propose_rule_update(body: RuleUpdateProposal, session: SessionDep, principal: Proposer) -> RuleUpdateOut:
    update = service.propose_rule_update(
        session,
        principal,
        basis_verdict_ids=body.basis_verdict_ids,
        base_rule_version_id=body.base_rule_version_id,
        expected_rule_id=body.expected_rule_id,
        spec_patch=body.spec_patch,
        rationale=body.rationale,
    )
    return update_out(*service.get_rule_update(session, principal, update.id))


@router.post("/rule-updates/{update_id}/evaluate", response_model=RuleUpdateOut)
def evaluate_rule_update(update_id: uuid.UUID, session: SessionDep, principal: Author) -> RuleUpdateOut:
    service.evaluate_rule_update(session, principal, update_id)
    return update_out(*service.get_rule_update(session, principal, update_id))


@router.post("/rule-updates/{update_id}/approve", response_model=RuleUpdateOut)
def approve_rule_update(
    update_id: uuid.UUID, body: ApprovalBody, session: SessionDep, principal: Approver
) -> RuleUpdateOut:
    service.decide_rule_update(
        session,
        principal,
        update_id,
        approve=True,
        validation_status=body.validation_status,
        expert_validation_confirmed=body.expert_validation_confirmed,
        note=body.note,
    )
    return update_out(*service.get_rule_update(session, principal, update_id))


@router.post("/rule-updates/{update_id}/reject", response_model=RuleUpdateOut)
def reject_rule_update(
    update_id: uuid.UUID, body: ReasonBody, session: SessionDep, principal: Approver
) -> RuleUpdateOut:
    service.decide_rule_update(
        session,
        principal,
        update_id,
        approve=False,
        validation_status=None,
        expert_validation_confirmed=False,
        note=body.reason,
    )
    return update_out(*service.get_rule_update(session, principal, update_id))


@router.post("/rule-updates/{update_id}/activate", response_model=RuleUpdateOut)
def activate_rule_update(update_id: uuid.UUID, session: SessionDep, principal: Approver) -> RuleUpdateOut:
    service.activate_rule_update(session, principal, update_id)
    return update_out(*service.get_rule_update(session, principal, update_id))


@router.post("/rule-updates/{update_id}/rollback", response_model=RuleUpdateOut)
def rollback_rule_update(update_id: uuid.UUID, session: SessionDep, principal: Approver) -> RuleUpdateOut:
    service.rollback_rule_update(session, principal, update_id)
    return update_out(*service.get_rule_update(session, principal, update_id))
