from dataclasses import dataclass

from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session

from app.domain.enums import Role
from app.seed import Catalog, SimFaskes, create_sim_faskes, create_user, ensure_catalog

PASSWORD = "uji-coba-kata-sandi-1"


@dataclass(frozen=True)
class World:
    catalog: Catalog
    a: SimFaskes
    b: SimFaskes
    governance: dict[str, str]


def build_world(session: Session) -> World:
    catalog = ensure_catalog(session)
    a = create_sim_faskes(session, name="Faskes Uji A", slug="a", password=PASSWORD)
    b = create_sim_faskes(session, name="Faskes Uji B", slug="b", password=PASSWORD)
    pengelola = create_sim_faskes(
        session, name="Pengelola Aturan Uji", slug="g", password=PASSWORD, with_sources=False
    )
    governance: dict[str, str] = {}
    for key, role in (
        ("rule_admin", Role.RULE_ADMIN),
        ("rule_admin_2", Role.RULE_ADMIN),
        ("approver", Role.RULE_APPROVER),
        ("approver_2", Role.RULE_APPROVER),
    ):
        email = f"{key}.g@example.com"
        create_user(
            session, pengelola.faskes_id, name=key, email=email, role=role, password=PASSWORD
        )
        governance[key] = email
    session.commit()
    return World(catalog, a, b, governance)


def login(client: TestClient, email: str, password: str = PASSWORD) -> Response:
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def login_as(client: TestClient, email: str) -> TestClient:
    response = login(client, email)
    assert response.status_code == 200, response.text
    return client
