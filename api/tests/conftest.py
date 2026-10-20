import os
from collections.abc import Iterator
from pathlib import Path

TEST_DB_NAME = os.environ.get("TEST_POSTGRES_DB", "jaga_klaim_test")
if not TEST_DB_NAME.endswith("_test"):
    raise RuntimeError("nama database uji harus berakhiran _test agar tidak menyentuh DB dev")
os.environ["POSTGRES_DB"] = TEST_DB_NAME
os.environ.setdefault("APP_ENV", "dev")
os.environ["API_CORS_ORIGINS"] = "http://localhost:8080"

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, create_engine

from alembic import command
from app.core.config import get_settings
from app.db.session import get_session

API_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_ORIGIN = "http://localhost:8080"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in str(item.path).replace("\\", "/"):
            item.add_marker(pytest.mark.db)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    settings = get_settings()
    assert settings.postgres_db == TEST_DB_NAME
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    command.upgrade(config, "head")
    test_engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    conn = engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        outer.rollback()
        conn.close()


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    with Session(connection, join_transaction_mode="create_savepoint") as db:
        yield db


@pytest.fixture
def app(session: Session) -> Iterator[FastAPI]:
    from main import app as application

    application.dependency_overrides[get_session] = lambda: session
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, headers={"Origin": ALLOWED_ORIGIN}) as test_client:
        yield test_client
