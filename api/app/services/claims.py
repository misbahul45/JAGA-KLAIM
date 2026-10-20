import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, func, or_
from sqlmodel import Session, col, select

from app.core.errors import conflict, not_found, unprocessable
from app.domain.enums import ClaimStatus, JobEvent, JobStatus, RunStatus
from app.domain.states import JOB_TRANSITIONS, ensure_transition
from app.models import (
    Claim,
    ClaimCode,
    EvidenceItem,
    Intervention,
    InvestigationJob,
    InvestigationRun,
    RiskVector,
    RuleSet,
    RuleVersion,
)
from app.models.base import utcnow
from app.services import audit
from app.services.auth import Principal
from app.services.claim_state import (
    REVIEW_TIERS,
    current_run_ids,
    desired_status,
    has_stale_evidence,
    open_review_count,
    transition_claim,
)
from app.services.investigation import (
    count_jobs,
    enqueue_job,
    get_job_by_key,
    latest_job_for_claim,
)

EDITABLE_STATUSES = frozenset(
    {ClaimStatus.DRAFT, ClaimStatus.RETURNED_TO_CODER, ClaimStatus.NEEDS_CLARIFICATION}
)
SUBMITTABLE_STATUSES = frozenset({ClaimStatus.DRAFT, ClaimStatus.NEEDS_CLARIFICATION})
RERUNNABLE_STATUSES = frozenset(
    {ClaimStatus.CODING_SUBMITTED, ClaimStatus.UNDER_REVIEW, ClaimStatus.READY_TO_LOCK}
)
IDENTITY_NUMBER = re.compile(r"^\d{12,20}$")
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:\-]{8,128}$")
SORT_COLUMNS = {
    "updated_at": Claim.updated_at,
    "created_at": Claim.created_at,
    "episode_no": Claim.episode_no,
    "status": Claim.status,
}


@dataclass(frozen=True)
class CodeSpec:
    code_type: str
    code: str
    position: str | None = None
    description: str | None = None

    @property
    def identity(self) -> tuple[str, str, str | None]:
        return (self.code_type, self.code, self.position)


@dataclass(frozen=True)
class ClaimListRow:
    claim: Claim
    code_count: int
    open_review_count: int
    highest_open_tier: str | None


def get_claim(
    session: Session, principal: Principal, claim_id: uuid.UUID, *, for_update: bool = False
) -> Claim:
    query = select(Claim).where(Claim.id == claim_id, Claim.faskes_id == principal.faskes_id)
    if for_update:
        query = query.with_for_update()
    claim = session.exec(query).first()
    if claim is None:
        raise not_found("Klaim")
    return claim


def current_codes(session: Session, claim_id: uuid.UUID) -> list[ClaimCode]:
    return list(
        session.exec(
            select(ClaimCode)
            .where(ClaimCode.claim_id == claim_id, col(ClaimCode.superseded_at).is_(None))
            .order_by(col(ClaimCode.created_at), col(ClaimCode.code))
        )
    )


def _validate_pseudonym(value: str) -> None:
    if IDENTITY_NUMBER.match(value):
        raise unprocessable(
            "pseudonym_looks_like_identity",
            "patient_pseudonym tidak boleh berupa nomor identitas; gunakan pseudonim buram",
        )


def create_claim(
    session: Session,
    principal: Principal,
    *,
    episode_no: str,
    patient_pseudonym: str,
    codes: list[CodeSpec],
    episode_start: datetime | None,
    episode_end: datetime | None,
) -> Claim:
    _validate_pseudonym(patient_pseudonym)
    if episode_start and episode_end and episode_end < episode_start:
        raise unprocessable("invalid_episode_period", "Akhir episode tidak boleh sebelum awal episode")
    identities = [c.identity for c in codes]
    if len(identities) != len(set(identities)):
        raise unprocessable("duplicate_codes", "Terdapat kode yang sama lebih dari sekali")
    duplicate = session.exec(
        select(Claim.id).where(
            Claim.faskes_id == principal.faskes_id, Claim.episode_no == episode_no
        )
    ).first()
    if duplicate is not None:
        raise conflict("episode_exists", "Nomor episode sudah memiliki klaim")
    claim = Claim(
        faskes_id=principal.faskes_id,
        episode_no=episode_no,
        patient_pseudonym=patient_pseudonym,
        status=ClaimStatus.DRAFT.value,
        episode_start=episode_start,
        episode_end=episode_end,
    )
    session.add(claim)
    session.flush()
    for spec in codes:
        session.add(
            ClaimCode(
                claim_id=claim.id,
                code_type=spec.code_type,
                code=spec.code,
                position=spec.position,
                description=spec.description,
            )
        )
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="claim",
        entity_id=claim.id,
        event_type="claim.created",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"episode_no": episode_no, "codes": len(codes)},
    )
    session.commit()
    return claim


def _invalidate_results(session: Session, claim: Claim, principal: Principal, now: datetime) -> int:
    marked = 0
    for run in session.exec(
        select(InvestigationRun).where(
            InvestigationRun.claim_id == claim.id, col(InvestigationRun.stale_at).is_(None)
        )
    ):
        run.stale_at = now
        session.add(run)
        marked += 1
    for job in session.exec(
        select(InvestigationJob).where(
            InvestigationJob.claim_id == claim.id,
            InvestigationJob.status == JobStatus.QUEUED.value,
        )
    ):
        ensure_transition("job investigasi", JOB_TRANSITIONS, JobStatus.QUEUED, JobStatus.CANCELLED)
        job.status = JobStatus.CANCELLED.value
        job.processed_at = now
        job.error_message = "dibatalkan karena klaim diubah"
        session.add(job)
        audit.append_event(
            session,
            faskes_id=claim.faskes_id,
            entity_type="investigation_job",
            entity_id=job.id,
            event_type="investigation.job_cancelled",
            actor_type="user",
            actor_id=principal.user_id,
            payload={"claim_id": claim.id, "reason": "claim_updated"},
        )
    return marked


def update_claim(
    session: Session,
    principal: Principal,
    claim_id: uuid.UUID,
    *,
    expected_version: int,
    codes: list[CodeSpec] | None,
    episode_start: datetime | None,
    episode_end: datetime | None,
    set_episode: bool,
) -> Claim:
    claim = get_claim(session, principal, claim_id, for_update=True)
    if claim.version != expected_version:
        raise conflict(
            "version_conflict",
            "Klaim telah diubah oleh pengguna lain. Muat ulang sebelum menyimpan.",
            {"current_version": claim.version},
        )
    status = ClaimStatus(claim.status)
    if status not in EDITABLE_STATUSES:
        raise conflict(
            "claim_not_editable",
            "Klaim pada status ini tidak dapat diubah",
            {"status": claim.status},
        )

    existing = current_codes(session, claim.id)
    existing_by_identity = {(c.code_type, c.code, c.position): c for c in existing}
    added: list[CodeSpec] = []
    removed: list[ClaimCode] = []
    if codes is not None:
        identities = [c.identity for c in codes]
        if len(identities) != len(set(identities)):
            raise unprocessable("duplicate_codes", "Terdapat kode yang sama lebih dari sekali")
        added = [c for c in codes if c.identity not in existing_by_identity]
        wanted = {c.identity for c in codes}
        removed = [c for ident, c in existing_by_identity.items() if ident not in wanted]

    new_start = episode_start if set_episode else claim.episode_start
    new_end = episode_end if set_episode else claim.episode_end
    if new_start and new_end and new_end < new_start:
        raise unprocessable("invalid_episode_period", "Akhir episode tidak boleh sebelum awal episode")
    period_changed = set_episode and (new_start != claim.episode_start or new_end != claim.episode_end)

    if not added and not removed and not period_changed:
        return claim

    now = utcnow()
    for code in removed:
        code.superseded_at = now
        session.add(code)
    for spec in added:
        session.add(
            ClaimCode(
                claim_id=claim.id,
                code_type=spec.code_type,
                code=spec.code,
                position=spec.position,
                description=spec.description,
            )
        )
    previous_version = claim.version
    claim.version += 1
    claim.episode_start = new_start
    claim.episode_end = new_end
    session.add(claim)
    invalidated = _invalidate_results(session, claim, principal, now)
    audit.append_event(
        session,
        faskes_id=claim.faskes_id,
        entity_type="claim",
        entity_id=claim.id,
        event_type="claim.updated",
        actor_type="user",
        actor_id=principal.user_id,
        payload={
            "version_from": previous_version,
            "version_to": claim.version,
            "codes_added": [c.code for c in added],
            "codes_removed": [c.code for c in removed],
            "period_changed": period_changed,
            "runs_marked_stale": invalidated,
        },
    )
    if status is not ClaimStatus.DRAFT:
        transition_claim(
            session,
            claim,
            ClaimStatus.DRAFT,
            actor_type="user",
            actor_id=principal.user_id,
            reason="klaim diubah oleh koder",
        )
    session.commit()
    return claim


def list_claims(
    session: Session,
    principal: Principal,
    *,
    status: str | None,
    q: str | None,
    tier: str | None,
    vector: str | None,
    updated_from: datetime | None,
    updated_to: datetime | None,
    sort: str,
    descending: bool,
    page: int,
    page_size: int,
) -> tuple[list[ClaimListRow], int]:
    conditions: list[ColumnElement[bool]] = [col(Claim.faskes_id) == principal.faskes_id]
    if status:
        conditions.append(col(Claim.status) == status)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(
            or_(
                col(Claim.episode_no).ilike(f"%{escaped}%", escape="\\"),
                col(Claim.patient_pseudonym).ilike(f"%{escaped}%", escape="\\"),
            )
        )
    if updated_from:
        conditions.append(col(Claim.updated_at) >= updated_from)
    if updated_to:
        conditions.append(col(Claim.updated_at) <= updated_to)

    if tier or vector:
        subquery = (
            select(InvestigationRun.claim_id)
            .join(Intervention, col(Intervention.run_id) == col(InvestigationRun.id))
            .where(
                col(InvestigationRun.stale_at).is_(None),
                InvestigationRun.faskes_id == principal.faskes_id,
            )
        )
        if tier:
            subquery = subquery.where(Intervention.tier == tier)
        if vector:
            subquery = (
                subquery.join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
                .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
                .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
                .where(RiskVector.code == vector)
            )
        conditions.append(col(Claim.id).in_(subquery))

    total = session.exec(select(func.count()).select_from(Claim).where(*conditions)).one()
    column = SORT_COLUMNS.get(sort, Claim.updated_at)
    ordering = col(column).desc() if descending else col(column).asc()
    claims = list(
        session.exec(
            select(Claim)
            .where(*conditions)
            .order_by(ordering, col(Claim.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    ids = [c.id for c in claims]
    code_counts: dict[uuid.UUID, int] = {}
    open_tiers: dict[uuid.UUID, list[str]] = {}
    if ids:
        code_counts = dict(
            session.exec(
                select(ClaimCode.claim_id, func.count())
                .where(col(ClaimCode.claim_id).in_(ids), col(ClaimCode.superseded_at).is_(None))
                .group_by(col(ClaimCode.claim_id))
            ).all()
        )
        for claim_id, tier_value in session.exec(
            select(InvestigationRun.claim_id, Intervention.tier)
            .join(Intervention, col(Intervention.run_id) == col(InvestigationRun.id))
            .where(
                col(InvestigationRun.claim_id).in_(ids),
                col(InvestigationRun.stale_at).is_(None),
                col(Intervention.tier).in_(REVIEW_TIERS),
                col(Intervention.resolved_at).is_(None),
            )
        ):
            open_tiers.setdefault(claim_id, []).append(tier_value)
    rows = [
        ClaimListRow(
            claim=c,
            code_count=code_counts.get(c.id, 0),
            open_review_count=len(open_tiers.get(c.id, [])),
            highest_open_tier=max(open_tiers[c.id]) if c.id in open_tiers else None,
        )
        for c in claims
    ]
    return rows, total


def _check_key(key: str | None) -> str | None:
    if key is None:
        return None
    if not IDEMPOTENCY_KEY.match(key):
        raise unprocessable(
            "invalid_idempotency_key",
            "Idempotency-Key harus 8-128 karakter alfanumerik, titik, titik dua, garis bawah, atau tanda hubung",
        )
    return f"client:{key}"


def _replayed_job(
    session: Session, claim: Claim, client_key: str, event: JobEvent
) -> InvestigationJob | None:
    existing = get_job_by_key(session, claim.faskes_id, client_key)
    if existing is None:
        return None
    if existing.claim_id != claim.id or existing.event_type != event.value:
        raise conflict(
            "idempotency_key_conflict",
            "Idempotency-Key ini sudah dipakai untuk permintaan lain",
        )
    return existing


def submit_coding(
    session: Session, principal: Principal, claim_id: uuid.UUID, *, idempotency_key: str | None
) -> tuple[InvestigationJob, bool]:
    claim = get_claim(session, principal, claim_id, for_update=True)
    client_key = _check_key(idempotency_key)

    if client_key:
        replay = _replayed_job(session, claim, client_key, JobEvent.CODING_SUBMITTED)
        if replay is not None:
            return replay, True

    status = ClaimStatus(claim.status)
    if status is ClaimStatus.CODING_SUBMITTED:
        pending = latest_job_for_claim(session, claim, event=JobEvent.CODING_SUBMITTED)
        if pending is not None:
            return pending, True
    if status not in SUBMITTABLE_STATUSES:
        raise conflict(
            "claim_not_submittable",
            "Klaim pada status ini tidak dapat dikirim untuk pemeriksaan",
            {"status": claim.status},
        )
    if not current_codes(session, claim.id):
        raise unprocessable("no_codes", "Klaim belum memiliki kode")

    key = client_key or (
        f"coding.submitted:{claim.id}:v{claim.version}:n{count_jobs(session, claim, JobEvent.CODING_SUBMITTED)}"
    )
    job, created = enqueue_job(
        session,
        claim,
        event=JobEvent.CODING_SUBMITTED,
        idempotency_key=key,
        requested_by=principal.user_id,
    )
    if not created:
        session.commit()
        return job, True
    claim.submitted_by = principal.user_id
    claim.submitted_at = utcnow()
    session.add(claim)
    transition_claim(
        session,
        claim,
        ClaimStatus.CODING_SUBMITTED,
        actor_type="user",
        actor_id=principal.user_id,
        reason="coding.submitted",
    )
    session.commit()
    return job, False


def request_rerun(
    session: Session,
    principal: Principal,
    claim_id: uuid.UUID,
    *,
    reason: str,
    idempotency_key: str | None,
) -> tuple[InvestigationJob, bool]:
    claim = get_claim(session, principal, claim_id, for_update=True)
    client_key = _check_key(idempotency_key)
    if client_key:
        replay = _replayed_job(session, claim, client_key, JobEvent.MANUAL_RERUN)
        if replay is not None:
            return replay, True
    if ClaimStatus(claim.status) not in RERUNNABLE_STATUSES:
        raise conflict(
            "claim_not_rerunnable",
            "Pemeriksaan ulang hanya dapat diminta untuk klaim yang sudah dikirim dan belum dikunci",
            {"status": claim.status},
        )
    open_job = session.exec(
        select(InvestigationJob).where(
            InvestigationJob.claim_id == claim.id,
            InvestigationJob.claim_version == claim.version,
            col(InvestigationJob.status).in_([JobStatus.QUEUED.value, JobStatus.PROCESSING.value]),
        )
    ).first()
    if open_job is not None:
        return open_job, True
    key = client_key or (
        f"manual.rerun:{claim.id}:v{claim.version}:n{count_jobs(session, claim, JobEvent.MANUAL_RERUN)}"
    )
    job, created = enqueue_job(
        session,
        claim,
        event=JobEvent.MANUAL_RERUN,
        idempotency_key=key,
        requested_by=principal.user_id,
        reason=reason,
    )
    session.commit()
    return job, not created


def cancel_job(session: Session, principal: Principal, job_id: uuid.UUID) -> InvestigationJob:
    job = session.exec(
        select(InvestigationJob)
        .where(InvestigationJob.id == job_id, InvestigationJob.faskes_id == principal.faskes_id)
        .with_for_update()
    ).first()
    if job is None:
        raise not_found("Job pemeriksaan")
    if job.status != JobStatus.QUEUED.value:
        raise conflict(
            "job_not_cancellable",
            "Hanya job yang masih mengantre yang dapat dibatalkan",
            {"status": job.status},
        )
    claim = get_claim(session, principal, job.claim_id, for_update=True)
    ensure_transition("job investigasi", JOB_TRANSITIONS, JobStatus.QUEUED, JobStatus.CANCELLED)
    job.status = JobStatus.CANCELLED.value
    job.processed_at = utcnow()
    session.add(job)
    audit.append_event(
        session,
        faskes_id=job.faskes_id,
        entity_type="investigation_job",
        entity_id=job.id,
        event_type="investigation.job_cancelled",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"claim_id": job.claim_id, "reason": "user_request"},
    )
    if (
        job.event_type == JobEvent.CODING_SUBMITTED.value
        and claim.status == ClaimStatus.CODING_SUBMITTED.value
        and claim.version == job.claim_version
    ):
        transition_claim(
            session,
            claim,
            ClaimStatus.DRAFT,
            actor_type="user",
            actor_id=principal.user_id,
            reason="pengiriman dibatalkan",
        )
    session.commit()
    return job


def get_job(session: Session, principal: Principal, job_id: uuid.UUID) -> InvestigationJob:
    job = session.exec(
        select(InvestigationJob).where(
            InvestigationJob.id == job_id, InvestigationJob.faskes_id == principal.faskes_id
        )
    ).first()
    if job is None:
        raise not_found("Job pemeriksaan")
    return job


def lock_claim(
    session: Session,
    principal: Principal,
    claim_id: uuid.UUID,
    *,
    acknowledge_limitations: bool,
) -> Claim:
    claim = get_claim(session, principal, claim_id, for_update=True)
    if claim.status != ClaimStatus.READY_TO_LOCK.value:
        raise conflict(
            "claim_not_lockable",
            "Klaim hanya dapat dikunci setelah semua tinjauan selesai",
            {"status": claim.status},
        )
    if desired_status(session, claim) is not ClaimStatus.READY_TO_LOCK or open_review_count(session, claim):
        raise conflict("review_incomplete", "Masih ada tinjauan yang belum selesai")
    if has_stale_evidence(session, claim):
        raise conflict(
            "evidence_updated_after_run",
            "Bukti diperbarui setelah pemeriksaan terakhir. Jalankan pemeriksaan ulang.",
        )
    runs = list(
        session.exec(
            select(InvestigationRun).where(col(InvestigationRun.id).in_(current_run_ids(session, claim)))
        )
    )
    if not runs:
        raise conflict("not_investigated", "Klaim belum memiliki hasil pemeriksaan yang berlaku")
    if any(r.status == RunStatus.PARTIAL.value for r in runs) and not acknowledge_limitations:
        raise conflict(
            "limitations_not_acknowledged",
            "Sebagian pemeriksaan abstain atau tidak lengkap. Konfirmasi bahwa Anda telah meninjau keterbatasannya.",
            {"partial_runs": [str(r.id) for r in runs if r.status == RunStatus.PARTIAL.value]},
        )
    claim.locked_by = principal.user_id
    claim.locked_at = utcnow()
    session.add(claim)
    transition_claim(
        session,
        claim,
        ClaimStatus.LOCKED,
        actor_type="user",
        actor_id=principal.user_id,
        reason="dikunci oleh verifikator",
    )
    session.commit()
    return claim


@dataclass(frozen=True)
class RunSummary:
    run: InvestigationRun
    vector_code: str
    rule_version_label: str
    tier_counts: dict[str, int]
    stale: bool


@dataclass(frozen=True)
class ClaimDetail:
    claim: Claim
    codes: list[ClaimCode]
    evidence_count: int
    quarantined_count: int
    open_review_count: int
    evidence_updated_after_run: bool
    runs: list[RunSummary]
    latest_job: InvestigationJob | None


def claim_detail(session: Session, principal: Principal, claim_id: uuid.UUID) -> ClaimDetail:
    claim = get_claim(session, principal, claim_id)
    evidence_count, quarantined = session.exec(
        select(
            func.count(),
            func.count().filter(col(EvidenceItem.injection_suspected).is_(True)),
        ).where(EvidenceItem.claim_id == claim.id)
    ).one()
    rows = session.exec(
        select(InvestigationRun, RiskVector.code, RuleVersion.version)
        .join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(InvestigationRun.claim_id == claim.id)
        .order_by(col(InvestigationRun.started_at).desc())
    ).all()
    tier_rows = session.exec(
        select(Intervention.run_id, Intervention.tier, func.count())
        .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
        .where(InvestigationRun.claim_id == claim.id)
        .group_by(col(Intervention.run_id), col(Intervention.tier))
    ).all()
    tiers: dict[uuid.UUID, dict[str, int]] = {}
    for run_id, tier_value, count in tier_rows:
        tiers.setdefault(run_id, {})[tier_value] = count
    runs = [
        RunSummary(
            run=run,
            vector_code=vector_code,
            rule_version_label=version,
            tier_counts=tiers.get(run.id, {}),
            stale=run.stale_at is not None or run.claim_version != claim.version,
        )
        for run, vector_code, version in rows
    ]
    return ClaimDetail(
        claim=claim,
        codes=current_codes(session, claim.id),
        evidence_count=evidence_count,
        quarantined_count=quarantined,
        open_review_count=open_review_count(session, claim),
        evidence_updated_after_run=has_stale_evidence(session, claim),
        runs=runs,
        latest_job=latest_job_for_claim(session, claim),
    )
