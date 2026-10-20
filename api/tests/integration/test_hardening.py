from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Claim, InvestigationJob
from tests.builders import World
from tests.integration.helpers import Actors, make_claim, process_all_jobs

RESUME_ONLY = [("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik.")]


def test_idempotency_key_cannot_be_reused_for_a_different_claim(
    session: Session, world: World, team_a: Actors
):
    first = make_claim(
        session, world.a, episode_no="EP-710", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    second = make_claim(
        session, world.a, episode_no="EP-711", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    headers = {"Idempotency-Key": "kunci-bersama-710-711"}
    accepted = team_a.coder.post(f"/v1/claims/{first.id}/submit-coding", headers=headers)
    assert accepted.status_code == 202

    reused = team_a.coder.post(f"/v1/claims/{second.id}/submit-coding", headers=headers)
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "idempotency_key_conflict"

    session.expire_all()
    assert session.get(Claim, second.id).status == "draft"
    jobs = session.exec(
        select(func.count()).select_from(InvestigationJob).where(InvestigationJob.claim_id == second.id)
    ).one()
    assert jobs == 0


def test_idempotency_key_cannot_be_reused_for_a_different_action(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(
        session, world.a, episode_no="EP-712", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    headers = {"Idempotency-Key": "kunci-aksi-712"}
    assert team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers=headers).status_code == 202
    process_all_jobs(session)
    session.expire_all()

    rerun = team_a.coder.post(
        f"/v1/claims/{claim.id}/investigations", json={"reason": "uji kunci idempotensi"}, headers=headers
    )
    assert rerun.status_code == 409
    assert rerun.json()["error"]["code"] == "idempotency_key_conflict"


def test_same_key_on_same_claim_and_action_still_replays(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(
        session, world.a, episode_no="EP-713", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    headers = {"Idempotency-Key": "kunci-ulang-713"}
    first = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers=headers)
    again = team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding", headers=headers)
    assert first.status_code == 202
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert again.json()["idempotent_replay"] is True


class AccusatorySynthesizer:
    def synthesize(self, comparison):
        from app.domain.synthesis import SynthesizedFinding

        return SynthesizedFinding(
            mismatch_desc="Terindikasi fraud oleh faskes, klaim akan ditolak.",
            proposed_actions=["tolak_klaim", "tinjau_kode", "tinjau_kode"],
            limitations=["Ini penipuan yang disengaja."],
            safety_flags=[],
        )


class SilentSynthesizer:
    def synthesize(self, comparison):
        from app.domain.synthesis import SynthesizedFinding

        return SynthesizedFinding(mismatch_desc="  ", proposed_actions=[], limitations=[], safety_flags=[])


def run_with(session: Session, claim: Claim, synthesizer) -> None:
    from app.models import InvestigationJob as Job
    from app.models.base import utcnow
    from app.services.investigation import run_job
    from app.worker import claim_next_job

    while (job := claim_next_job(session, utcnow())) is not None:
        run_job(session, job.id, synthesizer=synthesizer)
    session.expire_all()
    total = session.exec(select(func.count()).select_from(Job).where(Job.claim_id == claim.id)).one()
    assert total >= 1


def finding_payload(coder, session: Session, claim: Claim) -> dict:
    detail = coder.get(f"/v1/claims/{claim.id}").json()
    run = next(r for r in detail["runs"] if r["vector_code"] == "phantom_billing" and not r["stale"])
    return coder.get(f"/v1/investigations/{run['id']}").json()["findings"][0]


def test_untrusted_synthesizer_output_is_neutralised_before_it_is_stored(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(
        session, world.a, episode_no="EP-720", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    assert team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").status_code == 202
    run_with(session, claim, AccusatorySynthesizer())

    finding = finding_payload(team_a.coder, session, claim)
    text = finding["mismatch_desc"].lower()
    assert "fraud" not in text and "ditolak" not in text
    assert "ketidaksesuaian" in text
    delta = finding["delta"]
    action_codes = [a["code"] for a in delta["proposed_actions"]]
    assert action_codes == ["tinjau_kode"]
    assert any("aksi_tidak_diizinkan" in flag for flag in delta["safety_flags"])
    joined_limits = " ".join(delta["limitations"]).lower()
    assert "penipuan" not in joined_limits
    assert "tidak membuktikan" in joined_limits
    assert "bukan probabilitas" in joined_limits


def test_empty_synthesizer_output_falls_back_to_safe_wording_and_default_action(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(
        session, world.a, episode_no="EP-721", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    assert team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").status_code == 202
    run_with(session, claim, SilentSynthesizer())

    finding = finding_payload(team_a.coder, session, claim)
    assert finding["mismatch_desc"].strip()
    assert [a["code"] for a in finding["delta"]["proposed_actions"]] == ["periksa_dokumentasi"]


def test_intervention_detail_exposes_the_rule_version_needed_to_propose_an_update(
    session: Session, world: World, team_a: Actors
):
    claim = make_claim(
        session, world.a, episode_no="EP-730", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    assert team_a.coder.post(f"/v1/claims/{claim.id}/submit-coding").status_code == 202
    process_all_jobs(session)
    session.expire_all()

    queue = team_a.verifier.get("/v1/interventions").json()
    detail = team_a.verifier.get(f"/v1/interventions/{queue['items'][0]['intervention_id']}").json()
    run = detail["run"]

    rule_sets = team_a.verifier.get("/v1/rule-sets").json()
    active = {
        rs["vector"]["code"]: rs["active_version_id"] for rs in rule_sets
    }
    assert run["rule_version_id"] == active[detail["vector_code"]]

    version = team_a.verifier.get(f"/v1/rule-versions/{run['rule_version_id']}")
    assert version.status_code == 200
    assert version.json()["expected_rules"]
