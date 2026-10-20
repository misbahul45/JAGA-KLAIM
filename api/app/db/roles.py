import re

import psycopg
from psycopg import sql

from app.core.config import Settings

ROLE_NAME = re.compile(r"^[a-z_][a-z0-9_]{2,62}$")
MIN_PASSWORD_LENGTH = 16
APP_PRIVILEGES = sql.SQL("SELECT, INSERT, UPDATE")

APPEND_ONLY_QUERY = (
    "SELECT DISTINCT c.relname "
    "FROM pg_trigger t "
    "JOIN pg_class c ON c.oid = t.tgrelid "
    "JOIN pg_proc p ON p.oid = t.tgfoid "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE p.proname = 'forbid_row_mutation' AND NOT t.tgisinternal AND n.nspname = 'public' "
    "ORDER BY c.relname"
)


class RoleProvisioningError(Exception):
    pass


def provision_app_role(settings: Settings, *, role: str, password: str) -> list[str]:
    if not ROLE_NAME.match(role):
        raise RoleProvisioningError("nama role harus huruf kecil, angka, atau garis bawah (3-63 karakter)")
    if role == settings.postgres_user:
        raise RoleProvisioningError("role aplikasi harus berbeda dari role pemilik skema")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise RoleProvisioningError(f"kata sandi role minimal {MIN_PASSWORD_LENGTH} karakter")

    target = sql.Identifier(role)
    database = sql.Identifier(settings.postgres_db)
    with psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        dbname=settings.postgres_db,
    ) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        verb = sql.SQL("ALTER") if exists else sql.SQL("CREATE")
        conn.execute(
            sql.SQL(
                "{} ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(verb, target, sql.Literal(password))
        )
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, target))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(target))
        conn.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(target))
        conn.execute(
            sql.SQL("GRANT {} ON ALL TABLES IN SCHEMA public TO {}").format(APP_PRIVILEGES, target)
        )
        conn.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT {} ON TABLES TO {}"
            ).format(APP_PRIVILEGES, target)
        )
        if conn.execute("SELECT to_regclass('public.alembic_version')").fetchone() != (None,):
            conn.execute(sql.SQL("REVOKE ALL ON TABLE alembic_version FROM {}").format(target))
        append_only = [row[0] for row in conn.execute(APPEND_ONLY_QUERY).fetchall()]
        if append_only:
            conn.execute(
                sql.SQL("REVOKE UPDATE ON TABLE {} FROM {}").format(
                    sql.SQL(", ").join(sql.Identifier(name) for name in append_only), target
                )
            )
    return append_only
