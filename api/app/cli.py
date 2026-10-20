import argparse
import os
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.core.security import password_policy_violation
from app.db.roles import RoleProvisioningError, provision_app_role
from app.db.session import get_engine
from app.domain.enums import Role
from app.models import AppUser, EvidenceSource, Faskes
from app.models.base import utcnow
from app.seed import (
    SIM_SOURCES,
    create_sim_faskes,
    create_user,
    ensure_catalog,
    seed_demo_claims,
)


@dataclass(frozen=True)
class SeedResult:
    faskes_id: uuid.UUID
    emails: dict[str, str]
    claims: int
    rule_versions: int


def _password(env_name: str) -> str:
    value = os.environ.get(env_name, "")
    violation = password_policy_violation(value) if value else f"variabel {env_name} belum diisi"
    if violation:
        raise SystemExit(f"Kata sandi tidak dapat dipakai: {violation}")
    return value


def seed_sim(session: Session, password: str) -> SeedResult:
    catalog = ensure_catalog(session)
    existing = session.exec(select(Faskes).where(Faskes.name == "RS Simulasi Nusantara (SIMULASI)")).first()
    if existing is not None:
        raise SystemExit("Data simulasi sudah ada. Gunakan docker compose down -v bila ingin mengulang dari awal.")
    sim = create_sim_faskes(session, name="RS Simulasi Nusantara", slug="sim", password=password)
    governance = create_sim_faskes(
        session, name="Pengelola Aturan", slug="gov", password=password, with_sources=False
    )
    gov_emails: dict[str, str] = {}
    for key, role in (("rule-admin", Role.RULE_ADMIN), ("rule-approver", Role.RULE_APPROVER)):
        email = f"{key}.sim@example.com"
        create_user(
            session,
            governance.faskes_id,
            name=key.replace("-", " ").title(),
            email=email,
            role=role,
            password=password,
        )
        gov_emails[key] = email
    claims = seed_demo_claims(session, sim)
    session.commit()
    return SeedResult(
        faskes_id=sim.faskes_id,
        emails={**sim.emails, **gov_emails},
        claims=len(claims),
        rule_versions=len(catalog.rule_version_ids),
    )


def sync_sim(session: Session) -> int:
    now = utcnow()
    refs = [ref for _, ref in SIM_SOURCES]
    sources = session.exec(select(EvidenceSource).where(col(EvidenceSource.system_ref).in_(refs))).all()
    for source in sources:
        source.last_synced_at = now
        source.last_health_check_at = now
        source.health_status = "healthy"
        session.add(source)
    session.commit()
    return len(sources)


def create_ops_user(
    session: Session, *, faskes_id: uuid.UUID, name: str, email: str, role: Role, password: str
) -> uuid.UUID:
    if session.get(Faskes, faskes_id) is None:
        raise SystemExit("Faskes tidak ditemukan")
    taken = session.exec(select(func.count()).select_from(AppUser).where(func.lower(AppUser.email) == email.lower())).one()
    if taken:
        raise SystemExit("Email sudah terdaftar")
    user = create_user(session, faskes_id, name=name, email=email, role=role, password=password)
    session.commit()
    return user.id


def provision_from_env(role_env: str, password_env: str) -> None:
    role = os.environ.get(role_env, "")
    password = os.environ.get(password_env, "")
    if not role and not password:
        print("Dilewati: variabel role aplikasi belum diisi, layanan tetap memakai role pemilik skema")
        return
    if not role or not password:
        raise SystemExit(f"Isi {role_env} dan {password_env} bersamaan, atau kosongkan keduanya")
    try:
        tables = provision_app_role(get_settings(), role=role, password=password)
    except RoleProvisioningError as exc:
        raise SystemExit(f"Provisioning role gagal: {exc}") from exc
    print(f"Role {role} siap. Tabel append-only tanpa hak UPDATE: {', '.join(tables)}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Perintah operasional JAGA-KLAIM")
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed-sim", help="Isi data simulasi (faskes, akun, sumber, klaim sintetis)")
    seed.add_argument("--password-env", default="SEED_PASSWORD", help="nama variabel lingkungan berisi kata sandi akun simulasi")

    commands.add_parser("sync-sim", help="Perbarui waktu sinkronisasi sumber simulasi")

    user = commands.add_parser("create-user", help="Buat akun, termasuk peran tata kelola aturan")
    user.add_argument("--faskes-id", type=uuid.UUID, required=True)
    user.add_argument("--name", required=True)
    user.add_argument("--email", required=True)
    user.add_argument("--role", choices=[r.value for r in Role], required=True)
    user.add_argument("--password-env", default="NEW_USER_PASSWORD")

    provision = commands.add_parser(
        "provision-app-role", help="Buat atau perbarui role database aplikasi dengan hak minimum"
    )
    provision.add_argument("--role-env", default="APP_DB_USER")
    provision.add_argument("--password-env", default="APP_DB_PASSWORD")

    args = parser.parse_args(argv)
    if args.command == "provision-app-role":
        provision_from_env(args.role_env, args.password_env)
        return
    with Session(get_engine()) as session:
        if args.command == "seed-sim":
            result = seed_sim(session, _password(args.password_env))
            print(f"Faskes simulasi: {result.faskes_id}")
            print(f"Klaim sintetis: {result.claims}; versi aturan aktif: {result.rule_versions}")
            for key, email in sorted(result.emails.items()):
                print(f"  {key:14s} {email}")
        elif args.command == "sync-sim":
            print(f"{sync_sim(session)} sumber simulasi disegarkan")
        elif args.command == "create-user":
            created = create_ops_user(
                session,
                faskes_id=args.faskes_id,
                name=args.name,
                email=args.email,
                role=Role(args.role),
                password=_password(args.password_env),
            )
            print(f"Akun dibuat: {created}")


if __name__ == "__main__":
    main()
