import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Claim, EvidenceSource
from app.models.base import utcnow
from app.seed import SimFaskes, add_evidence, create_claim
from app.services.investigation import run_job
from app.worker import claim_next_job
from tests.builders import PASSWORD, login

ORIGIN = "http://localhost:8080"


def new_client(app) -> TestClient:
    return TestClient(app, headers={"Origin": ORIGIN})


@dataclass
class Actors:
    coder: TestClient
    verifier: TestClient
    admin: TestClient


def sign_in(client: TestClient, email: str) -> TestClient:
    response = login(client, email, PASSWORD)
    assert response.status_code == 200, response.text
    return client


def actors_for(app, faskes: SimFaskes) -> Actors:
    return Actors(
        coder=sign_in(new_client(app), faskes.emails["coder"]),
        verifier=sign_in(new_client(app), faskes.emails["verifier"]),
        admin=sign_in(new_client(app), faskes.emails["admin"]),
    )


def process_all_jobs(session: Session) -> int:
    processed = 0
    while True:
        job = claim_next_job(session, utcnow())
        if job is None:
            return processed
        run_job(session, job.id)
        processed += 1


def make_claim(
    session: Session,
    faskes: SimFaskes,
    *,
    episode_no: str,
    codes: list[tuple[str, str]],
    evidence: list[tuple[str, str, str]] | None = None,
) -> Claim:
    claim = create_claim(
        session, faskes.faskes_id, episode_no=episode_no, pseudonym=f"PSEUDO-{episode_no}", codes=codes
    )
    for source_type, kind, text in evidence or []:
        add_evidence(session, claim, faskes.source_ids[source_type], kind=kind, text=text)
    session.commit()
    return claim


def submit_and_process(
    session: Session, coder: TestClient, claim: Claim
) -> uuid.UUID:
    response = coder.post(f"/v1/claims/{claim.id}/submit-coding")
    assert response.status_code == 202, response.text
    job_id = uuid.UUID(response.json()["id"])
    process_all_jobs(session)
    session.expire_all()
    return job_id


def set_source_health(session: Session, faskes: SimFaskes, source_type: str, health: str) -> None:
    source = session.get(EvidenceSource, faskes.source_ids[source_type])
    source.health_status = health
    session.add(source)
    session.commit()


def runs_by_vector(client: TestClient, claim_id: uuid.UUID) -> dict[str, dict]:
    detail = client.get(f"/v1/claims/{claim_id}").json()
    return {r["vector_code"]: r for r in detail["runs"] if not r["stale"]}
