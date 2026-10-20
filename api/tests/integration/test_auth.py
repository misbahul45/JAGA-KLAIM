from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models import AppUser, AuditLog, AuthSession, UserCredential
from app.services.audit import verify_chain
from tests.builders import PASSWORD, build_world, login, login_as

NEW_USER = {
    "name": "Koder Baru",
    "email": "koder.baru@example.com",
    "role": "coder",
    "password": "kata-sandi-baru-123",
}


def test_login_sets_httponly_session_cookie_and_returns_permissions(
    client: TestClient, session: Session
):
    world = build_world(session)
    response = login(client, world.a.emails["verifier"])
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "verifier"
    assert "review:verdict" in body["permissions"]
    assert "claim:write" not in body["permissions"]
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert get_settings().session_cookie_name in cookie


def test_session_token_is_stored_only_as_hash(client: TestClient, session: Session):
    world = build_world(session)
    login(client, world.a.emails["coder"])
    token = client.cookies.get(get_settings().session_cookie_name)
    stored = session.exec(select(AuthSession)).all()
    assert token and stored
    assert all(row.token_hash != token for row in stored)


def test_me_requires_authentication(client: TestClient):
    response = client.get("/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_password_and_unknown_user_are_indistinguishable(
    client: TestClient, session: Session
):
    world = build_world(session)
    wrong = login(client, world.a.emails["coder"], "salah-sekali-123")
    unknown = login(client, "tidak.ada@example.com", "salah-sekali-123")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_account_locks_after_repeated_failures(client: TestClient, session: Session):
    world = build_world(session)
    email = world.a.emails["coder"]
    limit = get_settings().login_max_failed_attempts
    for _ in range(limit):
        assert login(client, email, "salah-sekali-123").status_code == 401
    locked = login(client, email, PASSWORD)
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "too_many_attempts"


def test_successful_login_resets_failure_counter(client: TestClient, session: Session):
    world = build_world(session)
    email = world.a.emails["coder"]
    login(client, email, "salah-sekali-123")
    assert login(client, email).status_code == 200
    user = session.exec(select(AppUser).where(AppUser.email == email)).one()
    assert session.get(UserCredential, user.id).failed_attempts == 0


def test_inactive_user_cannot_login(client: TestClient, session: Session):
    world = build_world(session)
    user = session.get(AppUser, world.a.user_ids["coder"])
    user.is_active = False
    session.add(user)
    session.commit()
    assert login(client, world.a.emails["coder"]).status_code == 401


def test_logout_revokes_the_session(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["coder"])
    assert client.get("/v1/auth/me").status_code == 200
    assert client.post("/v1/auth/logout").status_code == 200
    assert client.get("/v1/auth/me").status_code == 401


def test_post_with_foreign_origin_is_rejected(client: TestClient, session: Session):
    world = build_world(session)
    response = client.post(
        "/v1/auth/login",
        json={"email": world.a.emails["coder"], "password": PASSWORD},
        headers={"Origin": "https://penyerang.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


def test_cookie_authenticated_post_without_origin_is_rejected(
    client: TestClient, session: Session
):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    client.headers.pop("Origin")
    response = client.post("/v1/users", json=NEW_USER)
    assert response.status_code == 403


def test_admin_creates_user_in_own_faskes_only(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    created = client.post("/v1/users", json=NEW_USER)
    assert created.status_code == 201
    user = session.get(AppUser, created.json()["id"])
    assert user.faskes_id == world.a.faskes_id
    assert session.get(UserCredential, user.id).password_hash.startswith("scrypt$")


def test_coder_cannot_manage_users(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["coder"])
    assert client.post("/v1/users", json=NEW_USER).status_code == 403
    assert client.get("/v1/users").status_code == 403


def test_admin_cannot_grant_rule_governance_roles(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    response = client.post("/v1/users", json={**NEW_USER, "role": "rule_approver"})
    assert response.status_code == 403


def test_weak_password_is_rejected(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    response = client.post("/v1/users", json={**NEW_USER, "password": "pendek"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


def test_duplicate_email_is_rejected(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    duplicate = {**NEW_USER, "email": world.a.emails["coder"].upper()}
    assert client.post("/v1/users", json=duplicate).status_code == 409


def test_admin_of_one_faskes_cannot_touch_users_of_another(
    client: TestClient, session: Session
):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    other_user = world.b.user_ids["coder"]
    response = client.patch(f"/v1/users/{other_user}", json={"is_active": False})
    assert response.status_code == 404
    assert session.get(AppUser, other_user).is_active is True


def test_user_list_never_leaks_other_tenants(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    emails = {u["email"] for u in client.get("/v1/users").json()}
    assert emails == set(world.a.emails.values())


def test_deactivating_user_revokes_open_sessions(client: TestClient, session: Session):
    world = build_world(session)
    login_as(client, world.a.emails["admin"])
    victim = world.a.user_ids["coder"]
    other = TestClient(client.app, headers={"Origin": "http://localhost:8080"})
    login_as(other, world.a.emails["coder"])
    assert other.get("/v1/auth/me").status_code == 200
    assert client.patch(f"/v1/users/{victim}", json={"is_active": False}).status_code == 200
    assert other.get("/v1/auth/me").status_code == 401


def test_auth_events_are_audited_and_chain_verifies(client: TestClient, session: Session):
    world = build_world(session)
    login(client, world.a.emails["coder"], "salah-sekali-123")
    login_as(client, world.a.emails["coder"])
    client.post("/v1/auth/logout")
    events = [
        row.event_type
        for row in session.exec(
            select(AuditLog).where(AuditLog.faskes_id == world.a.faskes_id).order_by(AuditLog.seq)
        )
    ]
    assert events == ["auth.login_failed", "auth.login", "auth.logout"]
    result = verify_chain(session, world.a.faskes_id)
    assert result.valid and result.checked == 3


def test_error_responses_share_one_shape(client: TestClient):
    response = client.post("/v1/auth/login", json={"email": "x"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["fields"]
