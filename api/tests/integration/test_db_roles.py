import secrets
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors as pg_errors
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.config import get_settings
from app.db.roles import APPEND_ONLY_QUERY, RoleProvisioningError, provision_app_role
from app.db.session import get_session
from tests.builders import build_world
from tests.integration.helpers import (
    actors_for,
    make_claim,
    submit_and_process,
)

ROLE = "jk_app_uji"


def connect(user: str, password: str) -> psycopg.Connection:
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=user,
        password=password,
        dbname=settings.postgres_db,
        autocommit=True,
    )


def owner_connection() -> psycopg.Connection:
    settings = get_settings()
    return connect(settings.postgres_user, settings.postgres_password.get_secret_value())


def drop_role() -> None:
    with owner_connection() as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)).fetchone()
        if exists:
            conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(ROLE)))
            conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(ROLE)))


@pytest.fixture
def app_role(engine: Engine) -> Iterator[str]:
    drop_role()
    password = secrets.token_urlsafe(24)
    provision_app_role(get_settings(), role=ROLE, password=password)
    try:
        yield password
    finally:
        drop_role()


def denied(conn: psycopg.Connection, statement: str) -> None:
    with pytest.raises(pg_errors.InsufficientPrivilege):
        conn.execute(statement)


def test_app_role_is_not_privileged_and_cannot_change_schema(app_role: str):
    with connect(ROLE, app_role) as conn:
        flags = conn.execute(
            "SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        assert flags == (False, False, False, False, False)
        denied(conn, "CREATE TABLE tabel_liar (id int)")
        denied(conn, "DROP TABLE claim")
        denied(conn, "ALTER TABLE audit_log DISABLE TRIGGER ALL")
        denied(conn, "ALTER TABLE claim ADD COLUMN liar int")
        denied(conn, "SELECT * FROM alembic_version")


def test_app_role_can_read_and_write_but_never_delete_or_truncate(app_role: str):
    with connect(ROLE, app_role) as conn:
        assert conn.execute("SELECT count(*) FROM claim").fetchone() is not None
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO faskes (id, name, type, integration_mode) "
            "VALUES (gen_random_uuid(), 'Uji Peran', 'uji', 'uji')"
        )
        conn.execute("UPDATE faskes SET region = 'uji' WHERE name = 'Uji Peran'")
        conn.execute("ROLLBACK")
        denied(conn, "DELETE FROM faskes WHERE false")
        denied(conn, "TRUNCATE claim")


def test_append_only_tables_cannot_be_updated_even_before_the_trigger_fires(app_role: str):
    with owner_connection() as owner:
        tables = [row[0] for row in owner.execute(APPEND_ONLY_QUERY).fetchall()]
    assert {"audit_log", "human_verdict", "cognitive_assessment"} <= set(tables)
    with connect(ROLE, app_role) as conn:
        for table in tables:
            allowed = conn.execute(
                "SELECT has_table_privilege(current_user, %s, 'INSERT'), "
                "has_table_privilege(current_user, %s, 'UPDATE')",
                (table, table),
            ).fetchone()
            assert allowed == (True, False), table
        denied(conn, "UPDATE audit_log SET payload = '{}'::jsonb")


def test_provisioning_is_idempotent_and_rotates_the_password(app_role: str):
    new_password = secrets.token_urlsafe(24)
    provision_app_role(get_settings(), role=ROLE, password=new_password)
    with connect(ROLE, new_password) as conn:
        assert conn.execute("SELECT 1").fetchone() == (1,)
    with pytest.raises(psycopg.OperationalError):
        connect(ROLE, app_role)


def test_provisioning_rejects_unsafe_input():
    settings = get_settings()
    good = secrets.token_urlsafe(24)
    with pytest.raises(RoleProvisioningError):
        provision_app_role(settings, role="Bad Role; DROP", password=good)
    with pytest.raises(RoleProvisioningError):
        provision_app_role(settings, role=settings.postgres_user, password=good)
    with pytest.raises(RoleProvisioningError):
        provision_app_role(settings, role=ROLE, password="pendek")


def test_whole_claim_to_verdict_flow_works_with_the_restricted_role(engine: Engine, app_role: str):
    settings = get_settings()
    restricted: Engine = create_engine(
        f"postgresql+psycopg://{ROLE}:{app_role}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
        pool_pre_ping=True,
    )
    connection = restricted.connect()
    outer = connection.begin()
    session = Session(connection, join_transaction_mode="create_savepoint")
    from main import app as application

    application.dependency_overrides[get_session] = lambda: session
    try:
        assert session.execute(text("SELECT current_user")).scalar_one() == ROLE
        world = build_world(session)
        team = actors_for(application, world.a)
        claim = make_claim(
            session,
            world.a,
            episode_no="EP-ROLE-1",
            codes=[("procedure", "SIM-PROC-101")],
            evidence=[("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik.")],
        )
        submit_and_process(session, team.coder, claim)
        queue = team.verifier.get("/v1/interventions").json()
        assert queue["total"] >= 1
        item = queue["items"][0]["intervention_id"]
        assessed = team.verifier.post(
            f"/v1/interventions/{item}/assessment", json={"self_verdict": "supports_finding"}
        )
        assert assessed.status_code == 201, assessed.text
        verdict = team.verifier.post(
            f"/v1/interventions/{item}/verdict",
            json={
                "verdict": "supports_finding",
                "follow_up": "proceed",
                "rationale": "Bukti memang belum tercatat pada sumber yang diperiksa.",
            },
        )
        assert verdict.status_code == 201, verdict.text
        verified: TestClient = team.admin
        assert verified.get("/v1/audit-log/verify").json()["valid"] is True
    finally:
        application.dependency_overrides.clear()
        session.close()
        outer.rollback()
        connection.close()
        restricted.dispose()
