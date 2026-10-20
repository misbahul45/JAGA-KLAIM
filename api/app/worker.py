import argparse
import logging
import signal
import time
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, or_, select

from app.core.config import Settings, get_settings
from app.db.session import get_engine
from app.domain.enums import JobStatus
from app.domain.states import JOB_TRANSITIONS, ensure_transition
from app.models import InvestigationJob
from app.models.base import utcnow
from app.services import audit
from app.services.investigation import run_job

logger = logging.getLogger("jaga_klaim.worker")

stop_requested = False


def _handle_stop(_signum: int, _frame: object) -> None:
    global stop_requested
    stop_requested = True


def claim_next_job(session: Session, now: datetime) -> InvestigationJob | None:
    job = session.exec(
        select(InvestigationJob)
        .where(
            InvestigationJob.status == JobStatus.QUEUED.value,
            or_(
                col(InvestigationJob.next_attempt_at).is_(None),
                col(InvestigationJob.next_attempt_at) <= now,
            ),
        )
        .order_by(col(InvestigationJob.created_at))
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()
    if job is None:
        return None
    ensure_transition("job investigasi", JOB_TRANSITIONS, JobStatus.QUEUED, JobStatus.PROCESSING)
    job.status = JobStatus.PROCESSING.value
    job.attempt_count += 1
    job.locked_at = now
    job.next_attempt_at = None
    session.add(job)
    session.commit()
    return job


def schedule_retry_or_fail(
    session: Session, job: InvestigationJob, settings: Settings, now: datetime, error: str
) -> JobStatus:
    session.refresh(job)
    if job.status == JobStatus.FAILED.value:
        ensure_transition("job investigasi", JOB_TRANSITIONS, JobStatus.FAILED, JobStatus.QUEUED)
    elif job.status != JobStatus.PROCESSING.value:
        return JobStatus(job.status)
    if job.attempt_count < settings.investigation_max_attempts:
        job.status = JobStatus.QUEUED.value
        job.next_attempt_at = now + timedelta(
            seconds=settings.investigation_retry_backoff_seconds * job.attempt_count
        )
        job.error_message = error[:300]
        job.locked_at = None
        session.add(job)
        audit.append_event(
            session,
            faskes_id=job.faskes_id,
            entity_type="investigation_job",
            entity_id=job.id,
            event_type="investigation.job_retry_scheduled",
            actor_type="system",
            payload={"attempt": job.attempt_count, "claim_id": job.claim_id},
        )
        session.commit()
        return JobStatus.QUEUED
    if job.status != JobStatus.FAILED.value:
        job.status = JobStatus.FAILED.value
        job.error_message = error[:300]
        job.processed_at = now
        job.locked_at = None
        session.add(job)
        audit.append_event(
            session,
            faskes_id=job.faskes_id,
            entity_type="investigation_job",
            entity_id=job.id,
            event_type="investigation.job_failed",
            actor_type="system",
            payload={"attempt": job.attempt_count, "claim_id": job.claim_id},
        )
        session.commit()
    return JobStatus.FAILED


def recover_stuck_jobs(session: Session, settings: Settings, now: datetime) -> int:
    cutoff = now - timedelta(seconds=settings.job_lock_timeout_seconds)
    stuck = session.exec(
        select(InvestigationJob).where(
            InvestigationJob.status == JobStatus.PROCESSING.value,
            col(InvestigationJob.locked_at) < cutoff,
        )
    ).all()
    for job in stuck:
        schedule_retry_or_fail(session, job, settings, now, "worker berhenti sebelum pemeriksaan selesai")
    return len(stuck)


def process_one(session: Session, settings: Settings, now: datetime | None = None) -> JobStatus | None:
    current = now or utcnow()
    job = claim_next_job(session, current)
    if job is None:
        return None
    try:
        outcome = run_job(session, job.id, now=current)
    except Exception as exc:
        logger.exception("job %s gagal tak terduga", job.id)
        session.rollback()
        return schedule_retry_or_fail(session, job, settings, current, str(exc))
    if outcome is JobStatus.FAILED:
        return schedule_retry_or_fail(
            session, job, settings, current, job.error_message or "pemeriksaan gagal"
        )
    return outcome


def drain(session: Session, settings: Settings) -> int:
    processed = 0
    while process_one(session, settings) is not None:
        processed += 1
    return processed


def check_database() -> int:
    try:
        with Session(get_engine()) as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker investigasi JAGA-KLAIM")
    parser.add_argument("--once", action="store_true", help="proses antrean sampai kosong lalu berhenti")
    parser.add_argument("--check", action="store_true", help="periksa koneksi database lalu keluar dengan kode 0 atau 1")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    if args.check:
        raise SystemExit(check_database())

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    settings = get_settings()

    while not stop_requested:
        with Session(get_engine()) as session:
            recovered = recover_stuck_jobs(session, settings, utcnow())
            if recovered:
                logger.warning("memulihkan %s job yang tertahan", recovered)
            processed = drain(session, settings)
        if processed:
            logger.info("memproses %s job", processed)
        if args.once:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
