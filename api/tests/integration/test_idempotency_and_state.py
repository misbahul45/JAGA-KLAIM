import uuid
from datetime import timedelta

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models import Claim, InvestigationJob, InvestigationRun
from app.models.base import utcnow
from app.services.investigation import run_job
from app.worker import claim_next_job, process_one, recover_stuck_jobs
from tests.builders import World
from tests.integration.helpers import (
    Actors,
    make_claim,
    process_all_jobs,
    runs_by_vector,
    submit_and_process,
)

RESUME_ONLY = [("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik.")]


def jobs_for(session: Session, claim: Claim) -> list[InvestigationJob]:
    session.expire_all()
    return list(session.exec(select(InvestigationJob).where(InvestigationJob.claim_id == claim.id)))


def test_double_submit_creates_exactly_one_job(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-200", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    first = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding")
    second = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding")
    assert first.status_code == 202 and first.json()["idempotent_replay"] is False
    assert second.status_code == 200 and second.json()["idempotent_replay"] is True
    assert first.json()["id"] == second.json()["id"]
    assert len(jobs_for(session, claim)) == 1


def test_client_idempotency_key_replays_even_after_processing(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-201", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    headers = {"Idempotency-Key": "submit-ep-201-attempt-1"}
    first = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers=headers)
    process_all_jobs(session)
    again = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers=headers)
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
    assert len(jobs_for(session, claim)) == 1


def test_malformed_idempotency_key_is_rejected(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-202", codes=[("procedure", "SIM-PROC-101")])
    response = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers={"Idempotency-Key": "x"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_idempotency_key"


def test_submit_requires_codes_and_valid_state(session: Session, world: World, team_a: Actors):
    created = team_a.coder.post(
        "/v1/claims",
        json={
            "episode_no": "EP-203",
            "patient_pseudonym": "PSEUDO-203",
            "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}],
        },
    )
    assert created.status_code == 201
    claim_id = created.json()["id"]
    assert team_a.coder.post(f"/v1/claims/{claim_id}/submit-coding").status_code == 202
    process_all_jobs(session)
    session.expire_all()
    status = team_a.coder.get(f"/v1/claims/{claim_id}").json()["status"]
    assert status in {"under_review", "ready_to_lock"}
    resubmit = team_a.coder.post(f"/v1/claims/{claim_id}/submit-coding")
    assert resubmit.status_code == 409
    assert resubmit.json()["error"]["code"] == "claim_not_submittable"


def test_claim_creation_rejects_identity_numbers_and_duplicates(world: World, team_a: Actors):
    body = {
        "episode_no": "EP-204",
        "patient_pseudonym": "PSEUDO-204",
        "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}],
    }
    assert team_a.coder.post("/v1/claims", json=body).status_code == 201
    duplicate = team_a.coder.post("/v1/claims", json=body)
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "episode_exists"
    nik = team_a.coder.post("/v1/claims", json={**body, "episode_no": "EP-205", "patient_pseudonym": "3201234567890001"})
    assert nik.status_code == 422
    assert nik.json()["error"]["code"] == "validation_error" or nik.json()["error"]["code"] == "pseudonym_looks_like_identity"
    no_codes = team_a.coder.post("/v1/claims", json={**body, "episode_no": "EP-206", "codes": []})
    assert no_codes.status_code == 422


def test_editing_after_review_invalidates_results_and_requires_a_new_run(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(session, world.a, episode_no="EP-210", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    [item] = team_a.verifier.get("/v1/interventions").json()["items"]
    team_a.verifier.post(f"/v1/interventions/{item['intervention_id']}/assessment", json={"self_verdict": "supports_finding"})
    returned = team_a.verifier.post(
        f"/v1/interventions/{item['intervention_id']}/verdict",
        json={
            "verdict": "supports_finding",
            "follow_up": "return_to_coder",
            "rationale": "Kode tindakan perlu ditinjau ulang oleh koder",
        },
    )
    assert returned.status_code == 201
    assert team_a.coder.get(f"/v1/claims/{claim.id}").json()["status"] == "returned_to_coder"

    stale_version = team_a.coder.patch(
        f"/v1/claims/{claim.id}",
        json={"expected_version": 99, "codes": [{"code_type": "procedure", "code": "SIM-PROC-102"}]},
    )
    assert stale_version.status_code == 409
    assert stale_version.json()["error"]["code"] == "version_conflict"
    assert stale_version.json()["error"]["details"]["current_version"] == 1

    edited = team_a.coder.patch(
        f"/v1/claims/{claim.id}",
        json={"expected_version": 1, "codes": [{"code_type": "procedure", "code": "SIM-PROC-102"}]},
    )
    assert edited.status_code == 200 and edited.json()["version"] == 2
    detail = team_a.coder.get(f"/v1/claims/{claim.id}").json()
    assert detail["status"] == "draft"
    assert [c["code"] for c in detail["codes"]] == ["SIM-PROC-102"]
    assert all(r["stale"] for r in detail["runs"])
    assert team_a.verifier.get("/v1/interventions").json()["items"] == []

    stale_verdict = team_a.verifier.post(
        f"/v1/interventions/{item['intervention_id']}/verdict/correction",
        json={"verdict": "does_not_support_finding", "rationale": "Mencoba mengubah hasil yang sudah basi"},
    )
    assert stale_verdict.status_code == 409
    assert stale_verdict.json()["error"]["code"] == "stale_result"

    submit_and_process(session, team_a.coder, claim)
    session.expire_all()
    new_runs = session.exec(
        select(InvestigationRun).where(InvestigationRun.claim_id == claim.id, InvestigationRun.claim_version == 2)
    ).all()
    assert len(new_runs) == 3
    assert all(r.rerun_of_run_id is not None for r in new_runs)
    assert all(r.stale_at is None for r in new_runs)


def test_noop_edit_does_not_bump_version(world: World, team_a: Actors):
    created = team_a.coder.post(
        "/v1/claims",
        json={
            "episode_no": "EP-211",
            "patient_pseudonym": "PSEUDO-211",
            "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}],
        },
    ).json()
    unchanged = team_a.coder.patch(
        f"/v1/claims/{created['id']}",
        json={"expected_version": 1, "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}]},
    )
    assert unchanged.status_code == 200 and unchanged.json()["version"] == 1


def test_claim_in_review_cannot_be_edited(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-212", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    response = team_a.coder.patch(
        f"/v1/claims/{claim.id}",
        json={"expected_version": 1, "codes": [{"code_type": "procedure", "code": "SIM-PROC-102"}]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "claim_not_editable"


def test_new_evidence_after_review_blocks_locking_until_rerun(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-213", codes=[("procedure", "SIM-PROC-102")], evidence=[
        *RESUME_ONLY,
        ("emr", "catatan_tindakan", "Catatan sintetis: tindakan prosedur dilakukan."),
    ])
    submit_and_process(session, team_a.coder, claim)
    assert team_a.coder.get(f"/v1/claims/{claim.id}").json()["status"] == "ready_to_lock"

    ingested = team_a.admin.post(
        f"/v1/claims/{claim.id}/evidence",
        json={
            "source_id": str(world.a.source_ids["lis"]),
            "recorded_at": claim.episode_start.isoformat(),
            "kind": "hasil_lab",
            "content_text": "Hasil lab sintetis tambahan.",
        },
    )
    assert ingested.status_code == 201
    detail = team_a.coder.get(f"/v1/claims/{claim.id}").json()
    assert detail["evidence_updated_after_run"] is True
    blocked = team_a.verifier.post(f"/v1/claims/{claim.id}/lock", json={})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "evidence_updated_after_run"

    rerun = team_a.verifier.post(f"/v1/claims/{claim.id}/investigations", json={"reason": "Bukti laboratorium baru masuk"})
    assert rerun.status_code == 202
    again = team_a.verifier.post(f"/v1/claims/{claim.id}/investigations", json={"reason": "Klik ganda pada tombol periksa ulang"})
    assert again.status_code == 200 and again.json()["id"] == rerun.json()["id"]
    process_all_jobs(session)
    session.expire_all()
    detail = team_a.coder.get(f"/v1/claims/{claim.id}").json()
    assert detail["evidence_updated_after_run"] is False
    assert len([r for r in detail["runs"] if r["stale"]]) == 3
    assert len([r for r in detail["runs"] if not r["stale"]]) == 3
    assert team_a.verifier.post(f"/v1/claims/{claim.id}/lock", json={}).status_code == 200


def test_duplicate_evidence_is_deduplicated_by_content_hash(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-214", codes=[("procedure", "SIM-PROC-101")])
    body = {
        "source_id": str(world.a.source_ids["emr"]),
        "recorded_at": claim.episode_start.isoformat(),
        "kind": "resume_medis",
        "content_text": "Resume sintetis yang sama persis.",
    }
    first = team_a.admin.post(f"/v1/claims/{claim.id}/evidence", json=body)
    second = team_a.admin.post(f"/v1/claims/{claim.id}/evidence", json=body)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(team_a.coder.get(f"/v1/claims/{claim.id}/evidence").json()) == 1


def test_queued_job_can_be_cancelled_and_returns_claim_to_draft(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-215", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    job = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").json()
    cancelled = team_a.coder.post(f"/v1/jobs/{job['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert team_a.coder.get(f"/v1/claims/{claim.id}").json()["status"] == "draft"
    assert team_a.coder.post(f"/v1/jobs/{job['id']}/cancel").status_code == 409
    assert process_all_jobs(session) == 0


def test_failed_attempts_are_retried_with_backoff_then_marked_failed(
    session: Session, world: World, team_a: Actors, monkeypatch
):
    claim = make_claim(session, world.a, episode_no="EP-220", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    job_id = uuid.UUID(team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").json()["id"])

    def explode(*_args, **_kwargs):
        raise RuntimeError("penyedia bukti tidak terjangkau")

    monkeypatch.setattr("app.worker.run_job", explode)
    settings = get_settings()
    now = utcnow()
    for attempt in range(1, settings.investigation_max_attempts + 1):
        process_one(session, settings, now=now)
        session.expire_all()
        job = session.get(InvestigationJob, job_id)
        assert job.attempt_count == attempt
        if attempt < settings.investigation_max_attempts:
            assert job.status == "queued"
            assert job.next_attempt_at > now
            assert process_one(session, settings, now=now) is None
            now = job.next_attempt_at + timedelta(seconds=1)
    assert job.status == "failed"
    assert "tidak terjangkau" in job.error_message
    assert session.get(Claim, claim.id).status == "coding_submitted"


def test_processing_job_without_progress_is_recovered(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-221", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    job_id = uuid.UUID(team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").json()["id"])
    started = utcnow() - timedelta(hours=2)
    claimed = claim_next_job(session, started)
    assert claimed is not None and claimed.status == "processing"
    settings = get_settings()
    assert recover_stuck_jobs(session, settings, utcnow()) == 1
    session.expire_all()
    job = session.get(InvestigationJob, job_id)
    assert job.status == "queued" and job.attempt_count == 1


def test_job_for_outdated_claim_version_is_marked_stale(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-222", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    job_id = uuid.UUID(team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").json()["id"])
    job = claim_next_job(session, utcnow())
    stored = session.get(Claim, claim.id)
    stored.version = 5
    session.add(stored)
    session.commit()
    assert run_job(session, job.id).value == "stale"
    session.expire_all()
    assert session.get(InvestigationJob, job_id).status == "stale"
    assert session.exec(select(InvestigationRun).where(InvestigationRun.claim_id == claim.id)).all() == []


def test_lock_requires_completed_review(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-223", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    assert team_a.coder.get(f"/v1/claims/{claim.id}").json()["status"] == "under_review"
    blocked = team_a.verifier.post(f"/v1/claims/{claim.id}/lock", json={})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "claim_not_lockable"
    assert runs_by_vector(team_a.coder, claim.id)["phantom_billing"]["tier_counts"] == {"T3": 1}


def test_rerun_supersedes_open_interventions_and_blocks_actions_on_old_ones(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(session, world.a, episode_no="EP-224", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    [old] = team_a.verifier.get("/v1/interventions").json()["items"]

    rerun = team_a.verifier.post(f"/v1/claims/{claim.id}/investigations", json={"reason": "Pemeriksaan ulang setelah sinkronisasi"})
    assert rerun.status_code == 202
    process_all_jobs(session)
    session.expire_all()

    items = team_a.verifier.get("/v1/interventions").json()["items"]
    assert len(items) == 1
    assert items[0]["intervention_id"] != old["intervention_id"]

    old_detail = team_a.verifier.get(f"/v1/interventions/{old['intervention_id']}").json()
    assert old_detail["stale"] is True
    blocked = team_a.verifier.post(
        f"/v1/interventions/{old['intervention_id']}/assessment", json={"self_verdict": "supports_finding"}
    )
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "stale_result"

    runs = session.exec(select(InvestigationRun).where(InvestigationRun.claim_id == claim.id)).all()
    fresh = [r for r in runs if r.stale_at is None]
    assert len(fresh) == 3 and all(r.rerun_of_run_id is not None for r in fresh)
    assert {r.trigger for r in fresh} == {"manual.rerun"}
