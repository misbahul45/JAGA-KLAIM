import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import CognitiveAssessment, EvidenceSource, HumanVerdict, Intervention
from tests.builders import PASSWORD, World
from tests.integration.helpers import (
    Actors,
    make_claim,
    new_client,
    sign_in,
    submit_and_process,
)

RESUME_ONLY = [("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik.")]


@pytest.fixture
def reviewed_claim(session: Session, world: World, team_a: Actors):
    claim = make_claim(
        session, world.a, episode_no="EP-300", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY
    )
    submit_and_process(session, team_a.coder, claim)
    [item] = team_a.verifier.get("/v1/interventions").json()["items"]
    detail = team_a.verifier.get(f"/v1/interventions/{item['intervention_id']}").json()
    return claim, item["intervention_id"], detail


def test_other_tenant_cannot_read_or_touch_a_claim(world: World, team_a: Actors, team_b: Actors, session: Session, reviewed_claim):
    claim, intervention_id, detail = reviewed_claim
    run_id = detail["run"]["id"]
    evidence_id = detail["evidence"][0]["id"]
    job_id = team_a.coder.get(f"/v1/claims/{claim.id}").json()["latest_job"]["id"]

    for client in (team_b.coder, team_b.verifier, team_b.admin):
        assert client.get(f"/v1/claims/{claim.id}").status_code == 404
        assert client.get(f"/v1/claims/{claim.id}/evidence").status_code == 404
        assert client.get(f"/v1/investigations/{run_id}").status_code == 404
        assert client.get(f"/v1/jobs/{job_id}").status_code == 404
        assert client.get(f"/v1/interventions/{intervention_id}").status_code == 404

    assert team_b.coder.post(f"/v1/claims/{claim.id}/submit-coding").status_code == 404
    assert team_b.coder.patch(
        f"/v1/claims/{claim.id}",
        json={"expected_version": 1, "codes": [{"code_type": "procedure", "code": "SIM-PROC-999"}]},
    ).status_code == 404
    assert team_b.verifier.post(f"/v1/claims/{claim.id}/lock", json={}).status_code == 404
    assert team_b.verifier.post(
        f"/v1/interventions/{intervention_id}/assessment", json={"self_verdict": "supports_finding"}
    ).status_code == 404
    assert team_b.verifier.post(
        f"/v1/interventions/{intervention_id}/verdict",
        json={"verdict": "supports_finding", "rationale": "Mencoba menulis lintas faskes"},
    ).status_code == 404
    assert team_b.admin.post(
        f"/v1/claims/{claim.id}/evidence",
        json={
            "source_id": str(world.b.source_ids["emr"]),
            "recorded_at": claim.episode_start.isoformat(),
            "kind": "resume_medis",
            "content_text": "Bukti yang disusupkan lintas faskes",
        },
    ).status_code == 404
    assert evidence_id


def test_other_tenant_lists_are_empty_and_dashboards_are_isolated(world: World, team_a: Actors, team_b: Actors, reviewed_claim):
    assert team_b.coder.get("/v1/claims").json()["total"] == 0
    assert team_b.verifier.get("/v1/interventions").json()["total"] == 0
    assert team_a.verifier.get("/v1/interventions").json()["total"] == 1
    assert team_b.admin.get("/v1/audit-log").json()["total"] > 0
    entries_a = {e["entity_id"] for e in team_a.admin.get("/v1/audit-log", params={"page_size": 100}).json()["items"]}
    entries_b = {e["entity_id"] for e in team_b.admin.get("/v1/audit-log", params={"page_size": 100}).json()["items"]}
    assert not entries_a & entries_b
    assert team_b.admin.get("/v1/dashboard").json()["claims_by_status"] == {}
    assert team_a.admin.get("/v1/dashboard").json()["claims_by_status"] == {"under_review": 1}
    assert {s["id"] for s in team_b.admin.get("/v1/evidence-sources").json()}.isdisjoint(
        {s["id"] for s in team_a.admin.get("/v1/evidence-sources").json()}
    )


def test_source_of_another_tenant_cannot_be_used_for_ingestion(world: World, team_a: Actors, session: Session):
    claim = make_claim(session, world.a, episode_no="EP-301", codes=[("procedure", "SIM-PROC-101")])
    response = team_a.admin.post(
        f"/v1/claims/{claim.id}/evidence",
        json={
            "source_id": str(world.b.source_ids["emr"]),
            "recorded_at": claim.episode_start.isoformat(),
            "kind": "resume_medis",
            "content_text": "Mencoba memakai sumber milik faskes lain",
        },
    )
    assert response.status_code == 404
    assert team_a.admin.patch(
        f"/v1/evidence-sources/{world.b.source_ids['emr']}", json={"health_status": "down"}
    ).status_code == 404


def test_metrics_and_audit_verification_are_tenant_scoped(world: World, team_a: Actors, team_b: Actors, reviewed_claim):
    metrics_b = {m["code"]: m for m in team_b.admin.get("/v1/metrics").json()}
    assert metrics_b["abstention_rate"]["sample_size"] == 0
    metrics_a = {m["code"]: m for m in team_a.admin.get("/v1/metrics").json()}
    assert metrics_a["abstention_rate"]["sample_size"] == 3
    assert team_a.admin.get("/v1/audit-log/verify").json()["valid"] is True
    assert team_b.admin.get("/v1/audit-log/verify").json()["valid"] is True


@pytest.mark.parametrize(
    ("actor", "method", "path", "body"),
    [
        ("verifier", "post", "/v1/claims", {"episode_no": "EP-X", "patient_pseudonym": "PSEUDO-X", "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}]}),
        ("admin", "post", "/v1/claims", {"episode_no": "EP-X", "patient_pseudonym": "PSEUDO-X", "codes": [{"code_type": "procedure", "code": "SIM-PROC-101"}]}),
        ("coder", "post", "/v1/evidence-sources", {"source_type": "emr", "system_ref": "NEW-EMR"}),
        ("verifier", "post", "/v1/evidence-sources", {"source_type": "emr", "system_ref": "NEW-EMR"}),
        ("coder", "get", "/v1/audit-log", None),
        ("verifier", "get", "/v1/audit-log", None),
        ("coder", "get", "/v1/metrics", None),
        ("coder", "get", "/v1/users", None),
        ("verifier", "get", "/v1/users", None),
    ],
)
def test_roles_are_enforced_in_the_backend(world: World, team_a: Actors, session: Session, actor, method, path, body):
    client: TestClient = getattr(team_a, actor)
    response = client.request(method.upper(), path, json=body) if body is not None else client.request(method.upper(), path)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_coder_and_admin_cannot_record_assessments_or_verdicts(team_a: Actors, reviewed_claim):
    _, intervention_id, _ = reviewed_claim
    for client in (team_a.coder, team_a.admin):
        assert client.post(f"/v1/interventions/{intervention_id}/assessment", json={"self_verdict": "supports_finding"}).status_code == 403
        assert client.post(
            f"/v1/interventions/{intervention_id}/verdict",
            json={"verdict": "supports_finding", "rationale": "Tidak berwenang mencatat verdict"},
        ).status_code == 403


def test_auditor_is_read_only(world: World, team_a: Actors, session: Session, reviewed_claim):
    claim, intervention_id, _ = reviewed_claim
    auditor = sign_in(new_client(team_a.coder.app), world.a.emails["auditor"])
    assert auditor.get(f"/v1/claims/{claim.id}").status_code == 200
    assert auditor.get("/v1/audit-log").status_code == 200
    assert auditor.get("/v1/metrics").status_code == 200
    assert auditor.post(f"/v1/claims/{claim.id}/submit-coding").status_code == 403
    assert auditor.post(f"/v1/claims/{claim.id}/lock", json={}).status_code == 403
    assert auditor.post(f"/v1/interventions/{intervention_id}/assessment", json={"self_verdict": "supports_finding"}).status_code == 403
    evidence = auditor.get(f"/v1/claims/{claim.id}/evidence").json()
    assert evidence and all(item["content_text"] is None for item in evidence)


def test_unauthenticated_requests_are_rejected_everywhere(client: TestClient):
    for path in ("/v1/claims", "/v1/interventions", "/v1/evidence-sources", "/v1/audit-log", "/v1/metrics", "/v1/dashboard", "/v1/users"):
        response = client.get(path)
        assert response.status_code == 401, path
    assert client.get("/health/live").status_code == 200


def test_investigation_detail_is_gated_for_verifier_but_open_for_coder(team_a: Actors, reviewed_claim):
    _, intervention_id, detail = reviewed_claim
    run_id = detail["run"]["id"]
    coder_view = team_a.coder.get(f"/v1/investigations/{run_id}").json()
    assert coder_view["findings"][0]["revealed"] is True
    assert coder_view["findings"][0]["mismatch_desc"]

    before = team_a.verifier.get(f"/v1/investigations/{run_id}").json()
    assert before["findings"][0]["revealed"] is False
    assert before["findings"][0]["mismatch_desc"] is None
    assert before["findings"][0]["delta"] is None
    assert before["findings"][0]["citations"] == []

    team_a.verifier.post(f"/v1/interventions/{intervention_id}/assessment", json={"self_verdict": "supports_finding"})
    after = team_a.verifier.get(f"/v1/investigations/{run_id}").json()
    assert after["findings"][0]["revealed"] is True
    assert after["findings"][0]["citations"]


def test_assessment_is_unique_and_immutable_per_verifier(team_a: Actors, session: Session, reviewed_claim):
    _, intervention_id, _ = reviewed_claim
    url = f"/v1/interventions/{intervention_id}/assessment"
    assert team_a.verifier.post(url, json={"self_verdict": "supports_finding"}).status_code == 201
    again = team_a.verifier.post(url, json={"self_verdict": "does_not_support_finding"})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "assessment_exists"
    stored = session.exec(select(CognitiveAssessment)).one()
    assert stored.self_verdict == "supports_finding"


def test_verdict_is_append_only_with_correction_chain(team_a: Actors, session: Session, reviewed_claim):
    claim, intervention_id, _ = reviewed_claim
    team_a.verifier.post(f"/v1/interventions/{intervention_id}/assessment", json={"self_verdict": "supports_finding"})
    verdict_url = f"/v1/interventions/{intervention_id}/verdict"
    first = team_a.verifier.post(verdict_url, json={"verdict": "supports_finding", "rationale": "Bukti tindakan tidak ditemukan"})
    assert first.status_code == 201
    duplicate = team_a.verifier.post(verdict_url, json={"verdict": "does_not_support_finding", "rationale": "Mengubah keputusan diam-diam"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "verdict_exists"

    too_short = team_a.verifier.post(f"{verdict_url}/correction", json={"verdict": "does_not_support_finding", "rationale": "singkat"})
    assert too_short.status_code == 422

    corrected = team_a.verifier.post(
        f"{verdict_url}/correction",
        json={"verdict": "does_not_support_finding", "rationale": "Catatan tindakan ditemukan di dokumen lain"},
    )
    assert corrected.status_code == 201
    assert corrected.json()["supersedes_verdict_id"] == first.json()["id"]
    assert len(session.exec(select(HumanVerdict)).all()) == 2
    detail = team_a.verifier.get(f"/v1/interventions/{intervention_id}").json()
    assert [v["verdict"] for v in detail["verdicts"]] == ["supports_finding", "does_not_support_finding"]

    second_correction_of_same = team_a.verifier.post(
        f"{verdict_url}/correction",
        json={"verdict": "insufficient_evidence", "rationale": "Koreksi berikutnya atas verdict terbaru"},
    )
    assert second_correction_of_same.status_code == 201
    assert team_a.coder.get(f"/v1/claims/{claim.id}").json()["status"] == "ready_to_lock"


def test_t0_and_t1_interventions_do_not_accept_assessment(world: World, team_a: Actors, session: Session):
    source = session.get(EvidenceSource, world.a.source_ids["emr"])
    source.health_status = "down"
    session.add(source)
    session.commit()
    claim = make_claim(session, world.a, episode_no="EP-302", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    [t0] = session.exec(select(Intervention).where(Intervention.tier == "T0")).all()
    response = team_a.verifier.post(f"/v1/interventions/{t0.id}/assessment", json={"self_verdict": "supports_finding"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "review_not_required"
    detail = team_a.verifier.get(f"/v1/interventions/{t0.id}").json()
    assert detail["gate"]["required"] is False
    assert detail["recommendation"]["abstain_reason"]


def test_claim_list_filters_sorting_and_pagination(world: World, team_a: Actors, session: Session):
    for index in range(5):
        make_claim(session, world.a, episode_no=f"EP-40{index}", codes=[("procedure", "SIM-PROC-102")])
    page = team_a.coder.get("/v1/claims", params={"page_size": 2, "sort": "episode_no", "order": "asc"}).json()
    assert page["total"] == 5 and [i["episode_no"] for i in page["items"]] == ["EP-400", "EP-401"]
    assert team_a.coder.get("/v1/claims", params={"q": "EP-403"}).json()["total"] == 1
    assert team_a.coder.get("/v1/claims", params={"q": "%"}).json()["total"] == 0
    assert team_a.coder.get("/v1/claims", params={"status": "draft"}).json()["total"] == 5
    assert team_a.coder.get("/v1/claims", params={"status": "locked"}).json()["total"] == 0
    assert team_a.coder.get("/v1/claims", params={"page_size": 500}).status_code == 422
    assert team_a.coder.get("/v1/claims", params={"sort": "patient_pseudonym"}).status_code == 422
    assert team_a.coder.get("/v1/claims", params={"tier": "T9"}).status_code == 422


def test_claim_list_can_filter_by_open_tier(world: World, team_a: Actors, session: Session):
    flagged = make_claim(session, world.a, episode_no="EP-410", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    make_claim(session, world.a, episode_no="EP-411", codes=[("procedure", "SIM-PROC-102")], evidence=[
        *RESUME_ONLY,
        ("emr", "catatan_tindakan", "Catatan sintetis: tindakan prosedur dilakukan."),
    ])
    submit_and_process(session, team_a.coder, flagged)
    result = team_a.coder.get("/v1/claims", params={"tier": "T3"}).json()
    assert [i["episode_no"] for i in result["items"]] == ["EP-410"]
    assert result["items"][0]["highest_open_tier"] == "T3"
    assert team_a.coder.get("/v1/claims", params={"vector": "phantom_billing"}).json()["total"] == 1
    assert team_a.coder.get("/v1/claims", params={"vector": "upcoding"}).json()["total"] == 0


def test_auth_me_exposes_no_credential_material(team_a: Actors, world: World):
    body = team_a.verifier.get("/v1/auth/me").json()
    assert set(body) == {"user_id", "faskes_id", "name", "email", "role", "permissions"}
    assert uuid.UUID(body["user_id"]) == world.a.user_ids["verifier"]
    assert PASSWORD not in str(body)
