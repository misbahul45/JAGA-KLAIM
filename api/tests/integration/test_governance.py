import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domain.default_policy import DEFAULT_POLICY_RULES
from app.models import AppUser, RuleVersion
from tests.builders import World
from tests.integration.helpers import (
    Actors,
    make_claim,
    new_client,
    process_all_jobs,
    sign_in,
    submit_and_process,
)

PHRASE_VARIANT = [
    ("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik."),
    ("emr", "catatan_tindakan", "Catatan sintetis: prosedur dilakukan oleh dokter pelaksana tanpa penyulit."),
]
RESUME_ONLY = [PHRASE_VARIANT[0]]


@pytest.fixture
def gov(app: FastAPI, world: World) -> dict[str, TestClient]:
    return {key: sign_in(new_client(app), email) for key, email in world.governance.items()}


def policy_payload(version: str) -> dict:
    return {
        "version": version,
        "rules": [
            {
                "code": r["code"],
                "tier": r["tier"].value,
                "priority": r["priority"],
                "condition": r["condition"],
            }
            for r in DEFAULT_POLICY_RULES
        ],
    }


def active_rule_set(client: TestClient, vector: str) -> dict:
    return next(s for s in client.get("/v1/rule-sets").json() if s["vector"]["code"] == vector)


def flag_false_positive(session: Session, team: Actors, world: World, episode: str) -> tuple[str, str]:
    claim = make_claim(
        session, world.a, episode_no=episode, codes=[("procedure", "SIM-PROC-101")], evidence=PHRASE_VARIANT
    )
    submit_and_process(session, team.coder, claim)
    [item] = team.verifier.get("/v1/interventions").json()["items"]
    base = f"/v1/interventions/{item['intervention_id']}"
    team.verifier.post(f"{base}/assessment", json={"self_verdict": "does_not_support_finding"})
    verdict = team.verifier.post(
        f"{base}/verdict",
        json={
            "verdict": "does_not_support_finding",
            "rationale": "Dokumentasi tindakan ada dengan frasa berbeda dari kata kunci aturan",
        },
    ).json()
    return verdict["id"], item["intervention_id"]


def propose(team: Actors, gov_view: dict, verdict_id: str, patch: dict) -> dict:
    rule_set = active_rule_set(team.verifier, "phantom_billing")
    version = team.verifier.get(f"/v1/rule-versions/{rule_set['active_version_id']}").json()
    response = team.verifier.post(
        "/v1/rule-updates",
        json={
            "basis_verdict_ids": [verdict_id],
            "base_rule_version_id": version["id"],
            "expected_rule_id": version["expected_rules"][0]["id"],
            "spec_patch": patch,
            "rationale": "Frasa dokumentasi yang sah belum dikenali oleh kata kunci aturan",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


GOOD_PATCH = {
    "requirements": [
        {
            "id": "R1",
            "label": "Catatan tindakan prosedur",
            "evidence_kinds": ["catatan_tindakan"],
            "keywords_any": ["tindakan prosedur", "prosedur dilakukan"],
            "source_types": ["emr"],
            "window": "episode",
            "window_grace_hours": 72,
        }
    ]
}
BAD_PATCH = {
    "requirements": [
        {
            "id": "R1",
            "label": "Catatan tindakan prosedur",
            "evidence_kinds": ["catatan_tindakan"],
            "keywords_any": ["kata kunci yang tidak pernah muncul"],
            "source_types": ["emr"],
        }
    ]
}


def test_rule_version_lifecycle_activates_one_version_at_a_time(world: World, gov, session: Session):
    admin, approver = gov["rule_admin"], gov["approver"]
    rule_set = active_rule_set(admin, "phantom_billing")
    previous = rule_set["active_version_id"]

    created = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-1.1", "base_version_id": previous, "validation_status": "simulasi"},
    )
    assert created.status_code == 201 and created.json()["status"] == "draft"
    version_id = created.json()["id"]
    assert len(created.json()["expected_rules"]) == 1

    assert approver.post(f"/v1/rule-versions/{version_id}/approve", json={}).status_code == 409
    assert admin.post(f"/v1/rule-versions/{version_id}/submit").json()["status"] == "pending_approval"
    assert admin.post(f"/v1/rule-versions/{version_id}/approve", json={}).status_code == 403
    assert approver.post(f"/v1/rule-versions/{version_id}/approve", json={}).json()["status"] == "approved"
    activated = approver.post(f"/v1/rule-versions/{version_id}/activate")
    assert activated.status_code == 200 and activated.json()["status"] == "active"

    refreshed = active_rule_set(admin, "phantom_billing")
    assert refreshed["active_version_id"] == version_id
    statuses = {v["id"]: v["status"] for v in refreshed["versions"]}
    assert statuses[previous] == "retired"
    assert sum(1 for s in statuses.values() if s == "active") == 1


def test_author_cannot_approve_own_rule_version(world: World, gov, session: Session):
    admin = gov["rule_admin"]
    rule_set = active_rule_set(admin, "upcoding")
    version_id = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-1.2", "base_version_id": rule_set["active_version_id"], "validation_status": "simulasi"},
    ).json()["id"]
    admin.post(f"/v1/rule-versions/{version_id}/submit")
    author = session.exec(select(AppUser).where(AppUser.email == world.governance["rule_admin"])).one()
    author.role = "rule_approver"
    session.add(author)
    session.commit()
    refused = admin.post(f"/v1/rule-versions/{version_id}/approve", json={})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "separation_of_duties"


def test_expert_validation_needs_explicit_confirmation_and_note(world: World, gov):
    admin, approver = gov["rule_admin"], gov["approver"]
    rule_set = active_rule_set(admin, "unbundling")
    version_id = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-1.3", "base_version_id": rule_set["active_version_id"]},
    ).json()["id"]
    admin.post(f"/v1/rule-versions/{version_id}/submit")
    url = f"/v1/rule-versions/{version_id}/approve"
    assert approver.post(url, json={"validation_status": "tervalidasi_pakar"}).status_code == 422
    assert approver.post(url, json={"validation_status": "tervalidasi_pakar", "expert_validation_confirmed": True, "note": "ok"}).status_code == 422
    ok = approver.post(
        url,
        json={
            "validation_status": "tervalidasi_pakar",
            "expert_validation_confirmed": True,
            "note": "Divalidasi panel casemix internal, notulen rapat 2026-10",
        },
    )
    assert ok.status_code == 200 and ok.json()["validation_status"] == "tervalidasi_pakar"
    forged = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-1.4", "validation_status": "tervalidasi_pakar", "expected_rules": []},
    )
    assert forged.status_code == 422


def test_invalid_expected_rule_spec_is_rejected(world: World, gov):
    admin = gov["rule_admin"]
    rule_set = active_rule_set(admin, "phantom_billing")
    response = admin.post(
        "/v1/rule-versions",
        json={
            "rule_set_id": rule_set["id"],
            "version": "sim-bad",
            "expected_rules": [{"code_pattern": "SIM-*", "spec": {"check": "evidence_presence", "requirements": [{"id": "R1", "label": "x"}]}}],
        },
    )
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_spec"


def test_policy_version_lifecycle_validates_and_replaces_active(world: World, gov):
    admin, approver = gov["rule_admin"], gov["approver"]
    created = admin.post("/v1/policy-versions", json=policy_payload("policy-sim-2.0"))
    assert created.status_code == 201
    policy_id = created.json()["id"]
    assert len(created.json()["config_hash"]) == 64

    preview = admin.post(f"/v1/policy-versions/{policy_id}/preview", json={"facts": {
        "delta_present": True, "coverage_adequate": True, "unresolved_conflict": False,
        "citation_valid_count": 1, "rule_validation": "simulasi", "missing_ratio": 1.0,
        "only_out_of_window_matches": False,
    }})
    assert preview.json() == {"tier": "T3", "rule": "T3_FULL_DELTA", "priority": 60}

    assert admin.post(f"/v1/policy-versions/{policy_id}/submit").json()["status"] == "pending_approval"
    assert approver.post(f"/v1/policy-versions/{policy_id}/approve").json()["status"] == "approved"
    assert approver.post(f"/v1/policy-versions/{policy_id}/activate").json()["status"] == "active"
    versions = {v["version"]: v["status"] for v in admin.get("/v1/policy-versions").json()}
    assert versions["policy-sim-2.0"] == "active" and versions["policy-sim-1.0"] == "retired"


def test_invalid_policy_is_rejected_before_it_can_be_submitted(world: World, gov):
    admin = gov["rule_admin"]
    payload = policy_payload("policy-sim-bad")
    payload["rules"] = [r for r in payload["rules"] if r["code"] != "T1_MINOR_DELTA"]
    policy_id = admin.post("/v1/policy-versions", json=payload).json()["id"]
    submitted = admin.post(f"/v1/policy-versions/{policy_id}/submit")
    assert submitted.status_code == 422
    assert any("penampung" in p for p in submitted.json()["error"]["details"]["problems"])

    no_abstain_first = policy_payload("policy-sim-bad-2")
    for rule in no_abstain_first["rules"]:
        if rule["code"] == "T0_CITATION_UNVERIFIED":
            rule["priority"] = 65
    second_id = admin.post("/v1/policy-versions", json=no_abstain_first).json()["id"]
    assert admin.post(f"/v1/policy-versions/{second_id}/submit").status_code == 422


def test_cannot_skip_states_when_activating(world: World, gov):
    admin, approver = gov["rule_admin"], gov["approver"]
    rule_set = active_rule_set(admin, "phantom_billing")
    version_id = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-skip", "base_version_id": rule_set["active_version_id"]},
    ).json()["id"]
    assert approver.post(f"/v1/rule-versions/{version_id}/activate").status_code == 409
    assert admin.post(f"/v1/rule-versions/{version_id}/activate").status_code == 403


def test_verdict_grounded_update_is_evaluated_approved_activated_and_rolled_back(
    session: Session, world: World, team_a: Actors, gov
):
    verdict_id, _ = flag_false_positive(session, team_a, world, "EP-GOV-1")
    update = propose(team_a, gov, verdict_id, GOOD_PATCH)
    assert update["status"] == "proposed" and update["basis_verdict_ids"] == [verdict_id]
    base_version_id = update["base_rule_version_id"]

    assert team_a.verifier.post(f"/v1/rule-updates/{update['id']}/evaluate").status_code == 403
    evaluated = gov["rule_admin"].post(f"/v1/rule-updates/{update['id']}/evaluate").json()
    assert evaluated["status"] == "evaluated"
    report = evaluated["evaluation"]
    assert report["regression_count"] == 0
    assert "P11" in report["improvements"]
    assert "sintetis" in report["candidate"]["validation_set"]
    assert "bukan anotasi pakar" in report["candidate"]["validation_set"]
    assert evaluated["result_rule_version_id"] != base_version_id

    assert team_a.verifier.post(f"/v1/rule-updates/{update['id']}/approve", json={}).status_code == 403
    approved = gov["approver"].post(f"/v1/rule-updates/{update['id']}/approve", json={})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert approved.json()["decided_by"] != approved.json()["proposed_by"]

    activated = gov["approver"].post(f"/v1/rule-updates/{update['id']}/activate")
    assert activated.json()["status"] == "activated"
    refreshed = active_rule_set(gov["rule_admin"], "phantom_billing")
    assert refreshed["active_version_id"] == evaluated["result_rule_version_id"]
    candidate = gov["rule_admin"].get(f"/v1/rule-versions/{refreshed['active_version_id']}").json()
    assert candidate["validation_status"] == "simulasi"

    claim = make_claim(session, world.a, episode_no="EP-GOV-2", codes=[("procedure", "SIM-PROC-101")], evidence=PHRASE_VARIANT)
    submit_and_process(session, team_a.coder, claim)
    detail = team_a.coder.get(f"/v1/claims/{claim.id}").json()
    phantom = next(r for r in detail["runs"] if r["vector_code"] == "phantom_billing" and not r["stale"])
    assert phantom["outcome"] == "no_action"
    assert phantom["rule_version"] == candidate["version"]

    metrics = {m["code"]: m for m in team_a.admin.get("/v1/metrics").json()}
    assert metrics["verdict_to_update_traceability"]["value"] == 1.0

    rolled = gov["approver"].post(f"/v1/rule-updates/{update['id']}/rollback")
    assert rolled.json()["status"] == "rolled_back"
    after = active_rule_set(gov["rule_admin"], "phantom_billing")
    assert after["active_version_id"] not in (evaluated["result_rule_version_id"], base_version_id)
    restored = gov["rule_admin"].get(f"/v1/rule-versions/{after['active_version_id']}").json()
    assert restored["version"].startswith("sim-1.0-rb")
    statuses = {v["id"]: v["status"] for v in after["versions"]}
    assert statuses[evaluated["result_rule_version_id"]] == "retired"
    assert sum(1 for s in statuses.values() if s == "active") == 1


def test_update_with_regression_cannot_be_approved(session: Session, world: World, team_a: Actors, gov):
    verdict_id, _ = flag_false_positive(session, team_a, world, "EP-GOV-3")
    update = propose(team_a, gov, verdict_id, BAD_PATCH)
    evaluated = gov["rule_admin"].post(f"/v1/rule-updates/{update['id']}/evaluate").json()
    assert evaluated["evaluation"]["regression_count"] > 0
    assert "P01" in evaluated["evaluation"]["regressions"]
    blocked = gov["approver"].post(f"/v1/rule-updates/{update['id']}/approve", json={})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "regression_detected"
    rejected = gov["approver"].post(f"/v1/rule-updates/{update['id']}/reject", json={"reason": "Regresi pada kasus uji P01"})
    assert rejected.json()["status"] == "rejected"
    rule_set = active_rule_set(gov["rule_admin"], "phantom_billing")
    assert rule_set["active_version_id"] != evaluated["result_rule_version_id"]


def test_updates_cannot_skip_evaluation_or_be_decided_twice(session: Session, world: World, team_a: Actors, gov):
    verdict_id, _ = flag_false_positive(session, team_a, world, "EP-GOV-4")
    update = propose(team_a, gov, verdict_id, GOOD_PATCH)
    skip = gov["approver"].post(f"/v1/rule-updates/{update['id']}/approve", json={})
    assert skip.status_code == 409 and skip.json()["error"]["code"] == "invalid_state"
    assert gov["approver"].post(f"/v1/rule-updates/{update['id']}/activate").status_code == 409
    gov["rule_admin"].post(f"/v1/rule-updates/{update['id']}/evaluate")
    assert gov["rule_admin_2"].post(f"/v1/rule-updates/{update['id']}/evaluate").status_code == 409
    gov["approver"].post(f"/v1/rule-updates/{update['id']}/approve", json={})
    assert gov["approver_2"].post(f"/v1/rule-updates/{update['id']}/approve", json={}).status_code == 409


def test_only_eligible_own_tenant_verdicts_can_ground_an_update(
    session: Session, world: World, team_a: Actors, team_b: Actors, gov
):
    claim = make_claim(session, world.a, episode_no="EP-GOV-5", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    [item] = team_a.verifier.get("/v1/interventions").json()["items"]
    base = f"/v1/interventions/{item['intervention_id']}"
    team_a.verifier.post(f"{base}/assessment", json={"self_verdict": "supports_finding"})
    supporting = team_a.verifier.post(
        f"{base}/verdict", json={"verdict": "supports_finding", "rationale": "Temuan didukung oleh bukti yang ada"}
    ).json()

    rule_set = active_rule_set(team_a.verifier, "phantom_billing")
    version = team_a.verifier.get(f"/v1/rule-versions/{rule_set['active_version_id']}").json()
    body = {
        "basis_verdict_ids": [supporting["id"]],
        "base_rule_version_id": version["id"],
        "expected_rule_id": version["expected_rules"][0]["id"],
        "spec_patch": GOOD_PATCH,
        "rationale": "Mencoba mengubah aturan dari verdict yang mendukung temuan",
    }
    ineligible = team_a.verifier.post("/v1/rule-updates", json=body)
    assert ineligible.status_code == 422 and ineligible.json()["error"]["code"] == "verdict_not_eligible"
    foreign = team_b.verifier.post("/v1/rule-updates", json=body)
    assert foreign.status_code == 404
    assert team_a.coder.post("/v1/rule-updates", json=body).status_code == 403
    mismatch = team_a.verifier.post("/v1/rule-updates", json={**body, "spec_patch": {"requirements": []}})
    assert mismatch.status_code == 422


def test_rule_update_visibility_is_tenant_scoped_for_verifiers(
    session: Session, world: World, team_a: Actors, team_b: Actors, gov
):
    verdict_id, _ = flag_false_positive(session, team_a, world, "EP-GOV-6")
    update = propose(team_a, gov, verdict_id, GOOD_PATCH)
    assert [u["id"] for u in team_a.verifier.get("/v1/rule-updates").json()] == [update["id"]]
    assert team_b.verifier.get("/v1/rule-updates").json() == []
    assert team_b.verifier.get(f"/v1/rule-updates/{update['id']}").status_code == 404
    assert [u["id"] for u in gov["approver"].get("/v1/rule-updates").json()] == [update["id"]]


def test_governance_changes_are_audited_and_chain_stays_valid(session: Session, world: World, gov):
    admin, approver = gov["rule_admin"], gov["approver"]
    rule_set = active_rule_set(admin, "upcoding")
    version_id = admin.post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-audit", "base_version_id": rule_set["active_version_id"]},
    ).json()["id"]
    admin.post(f"/v1/rule-versions/{version_id}/submit")
    approver.post(f"/v1/rule-versions/{version_id}/approve", json={})
    approver.post(f"/v1/rule-versions/{version_id}/activate")
    events = [e["event_type"] for e in approver.get("/v1/audit-log", params={"page_size": 100}).json()["items"]]
    assert {"rule_version.approved", "rule_version.activated", "rule_version.retired"} <= set(events)
    assert approver.get("/v1/audit-log/verify").json()["valid"] is True
    assert session.get(RuleVersion, uuid.UUID(version_id)).approved_by is not None


def test_new_runs_after_activation_record_the_rule_version_they_used(session: Session, world: World, team_a: Actors, gov):
    claim = make_claim(session, world.a, episode_no="EP-GOV-7", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    first = team_a.coder.get(f"/v1/claims/{claim.id}").json()["runs"]
    old_labels = {r["vector_code"]: r["rule_version"] for r in first}
    rule_set = active_rule_set(gov["rule_admin"], "phantom_billing")
    version_id = gov["rule_admin"].post(
        "/v1/rule-versions",
        json={"rule_set_id": rule_set["id"], "version": "sim-2.0", "base_version_id": rule_set["active_version_id"], "validation_status": "simulasi"},
    ).json()["id"]
    gov["rule_admin"].post(f"/v1/rule-versions/{version_id}/submit")
    gov["approver"].post(f"/v1/rule-versions/{version_id}/approve", json={})
    gov["approver"].post(f"/v1/rule-versions/{version_id}/activate")
    team_a.verifier.post(f"/v1/claims/{claim.id}/investigations", json={"reason": "Aturan baru diaktifkan"})
    process_all_jobs(session)
    session.expire_all()
    runs = team_a.coder.get(f"/v1/claims/{claim.id}").json()["runs"]
    fresh = {r["vector_code"]: r["rule_version"] for r in runs if not r["stale"]}
    stale = {r["vector_code"]: r["rule_version"] for r in runs if r["stale"]}
    assert fresh["phantom_billing"] == "sim-2.0"
    assert stale["phantom_billing"] == old_labels["phantom_billing"] == "sim-1.0"
