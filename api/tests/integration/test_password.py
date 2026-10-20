import json

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import AuditLog
from app.services.audit import verify_chain
from tests.builders import PASSWORD, build_world, login, login_as
from tests.integration.helpers import new_client, sign_in

NEW_PASSWORD = "kata-sandi-segar-456"


def change(client: TestClient, current: str, new: str):
    return client.post("/v1/auth/password", json={"current_password": current, "new_password": new})


def test_user_changes_own_password_and_old_one_stops_working(client: TestClient, session: Session):
    world = build_world(session)
    email = world.a.emails["coder"]
    login_as(client, email)
    assert change(client, PASSWORD, NEW_PASSWORD).status_code == 200
    assert client.post("/v1/auth/logout").status_code == 200
    assert login(client, email, PASSWORD).status_code == 401
    assert login(client, email, NEW_PASSWORD).status_code == 200


def test_other_sessions_are_revoked_but_the_current_one_survives(app, session: Session):
    world = build_world(session)
    email = world.a.emails["coder"]
    here = sign_in(new_client(app), email)
    elsewhere = sign_in(new_client(app), email)
    assert change(here, PASSWORD, NEW_PASSWORD).status_code == 200
    assert here.get("/v1/auth/me").status_code == 200
    assert elsewhere.get("/v1/auth/me").status_code == 401


def test_wrong_current_password_is_rejected_and_counts_toward_lockout(
    client: TestClient, session: Session
):
    world = build_world(session)
    login_as(client, world.a.emails["coder"])
    limit = get_settings().login_max_failed_attempts
    for _ in range(limit):
        wrong = change(client, "salah-sekali-123", NEW_PASSWORD)
        assert wrong.status_code == 422
        assert wrong.json()["error"]["code"] == "invalid_current_password"
    locked = change(client, PASSWORD, NEW_PASSWORD)
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "too_many_attempts"


def test_new_password_must_satisfy_policy_and_differ_from_current(
    client: TestClient, session: Session
):
    world = build_world(session)
    login_as(client, world.a.emails["coder"])
    weak = change(client, PASSWORD, "pendek")
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "weak_password"
    same = change(client, PASSWORD, PASSWORD)
    assert same.status_code == 422 and same.json()["error"]["code"] == "password_unchanged"


def test_password_change_requires_authentication(client: TestClient):
    assert change(client, PASSWORD, NEW_PASSWORD).status_code == 401


def test_password_events_are_audited_without_credential_material(
    client: TestClient, session: Session
):
    world = build_world(session)
    login_as(client, world.a.emails["coder"])
    change(client, "salah-sekali-123", NEW_PASSWORD)
    change(client, PASSWORD, NEW_PASSWORD)
    rows = session.exec(
        select(AuditLog).where(
            AuditLog.faskes_id == world.a.faskes_id,
            col(AuditLog.event_type).in_(["auth.password_change_failed", "auth.password_changed"]),
        )
    ).all()
    assert {r.event_type for r in rows} == {"auth.password_change_failed", "auth.password_changed"}
    serialised = json.dumps([r.payload for r in rows])
    assert PASSWORD not in serialised and NEW_PASSWORD not in serialised
    assert verify_chain(session, world.a.faskes_id).valid


def reset(client: TestClient, user_id, new: str):
    return client.post(f"/v1/users/{user_id}/password", json={"new_password": new})


def test_admin_resets_password_of_own_faskes_user_and_revokes_their_sessions(
    app, session: Session
):
    world = build_world(session)
    admin = sign_in(new_client(app), world.a.emails["admin"])
    coder = sign_in(new_client(app), world.a.emails["coder"])
    coder_id = coder.get("/v1/auth/me").json()["user_id"]

    assert reset(admin, coder_id, NEW_PASSWORD).status_code == 200
    assert coder.get("/v1/auth/me").status_code == 401
    assert login(new_client(app), world.a.emails["coder"], PASSWORD).status_code == 401
    assert login(new_client(app), world.a.emails["coder"], NEW_PASSWORD).status_code == 200


def test_admin_cannot_reset_passwords_across_tenants_or_for_governance_roles(
    app, session: Session
):
    world = build_world(session)
    admin_a = sign_in(new_client(app), world.a.emails["admin"])
    coder_b = sign_in(new_client(app), world.b.emails["coder"])
    coder_b_id = coder_b.get("/v1/auth/me").json()["user_id"]
    assert reset(admin_a, coder_b_id, NEW_PASSWORD).status_code == 404

    approver = sign_in(new_client(app), world.governance["approver"])
    approver_id = approver.get("/v1/auth/me").json()["user_id"]
    assert reset(admin_a, approver_id, NEW_PASSWORD).status_code in (403, 404)


def test_non_admins_cannot_reset_passwords_and_admin_must_use_change_for_self(
    app, session: Session
):
    world = build_world(session)
    coder = sign_in(new_client(app), world.a.emails["coder"])
    admin = sign_in(new_client(app), world.a.emails["admin"])
    coder_id = coder.get("/v1/auth/me").json()["user_id"]
    admin_id = admin.get("/v1/auth/me").json()["user_id"]
    assert reset(coder, coder_id, NEW_PASSWORD).status_code == 403
    own = reset(admin, admin_id, NEW_PASSWORD)
    assert own.status_code == 409 and own.json()["error"]["code"] == "use_change_password"
    assert reset(admin, coder_id, "pendek").status_code == 422
