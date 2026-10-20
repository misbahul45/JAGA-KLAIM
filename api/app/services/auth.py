import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.config import Settings
from app.core.errors import (
    ApiError,
    conflict,
    forbidden,
    not_found,
    unauthorized,
    unprocessable,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_session_token,
    new_session_token,
    password_policy_violation,
    verify_password,
)
from app.domain.enums import Role
from app.domain.permissions import FASKES_ASSIGNABLE_ROLES, Permission, permissions_for
from app.models import AppUser, AuthSession, UserCredential
from app.models.base import utcnow
from app.services import audit

LAST_SEEN_REFRESH = timedelta(minutes=1)
GENERIC_LOGIN_ERROR = "Email atau kata sandi salah"


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    faskes_id: uuid.UUID
    name: str
    email: str
    role: Role
    permissions: frozenset[Permission]
    session_id: uuid.UUID | None = None

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions


def _principal(user: AppUser, session_id: uuid.UUID | None) -> Principal:
    return Principal(
        user_id=user.id,
        faskes_id=user.faskes_id,
        name=user.name,
        email=user.email,
        role=Role(user.role),
        permissions=permissions_for(user.role),
        session_id=session_id,
    )


def _register_failure(
    session: Session,
    credential: UserCredential,
    *,
    faskes_id: uuid.UUID,
    user_id: uuid.UUID,
    settings: Settings,
    now: datetime,
    event_type: str,
) -> None:
    credential.failed_attempts += 1
    locked = credential.failed_attempts >= settings.login_max_failed_attempts
    if locked:
        credential.locked_until = now + timedelta(seconds=settings.login_lockout_seconds)
        credential.failed_attempts = 0
    session.add(credential)
    audit.append_event(
        session,
        faskes_id=faskes_id,
        entity_type="user",
        entity_id=user_id,
        event_type=event_type,
        actor_type="user",
        actor_id=user_id,
        payload={"locked": locked},
    )


def _revoke_sessions(
    session: Session, user_id: uuid.UUID, now: datetime, *, keep: uuid.UUID | None = None
) -> int:
    revoked = 0
    for open_session in session.exec(
        select(AuthSession).where(
            AuthSession.user_id == user_id, col(AuthSession.revoked_at).is_(None)
        )
    ):
        if keep is not None and open_session.id == keep:
            continue
        open_session.revoked_at = now
        session.add(open_session)
        revoked += 1
    return revoked


def login(
    session: Session, *, email: str, password: str, settings: Settings
) -> tuple[str, datetime, Principal]:
    now = utcnow()
    user = session.exec(
        select(AppUser).where(func.lower(AppUser.email) == email.strip().lower())
    ).first()
    credential = session.get(UserCredential, user.id) if user else None

    if user is None or credential is None or not user.is_active:
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise unauthorized(GENERIC_LOGIN_ERROR)

    if credential.locked_until is not None and credential.locked_until > now:
        raise ApiError(
            429,
            "too_many_attempts",
            "Terlalu banyak percobaan masuk. Coba lagi beberapa saat lagi.",
        )

    if not verify_password(password, credential.password_hash):
        _register_failure(
            session,
            credential,
            faskes_id=user.faskes_id,
            user_id=user.id,
            settings=settings,
            now=now,
            event_type="auth.login_failed",
        )
        session.commit()
        raise unauthorized(GENERIC_LOGIN_ERROR)

    credential.failed_attempts = 0
    credential.locked_until = None
    session.add(credential)

    token = new_session_token()
    expires_at = now + timedelta(seconds=settings.session_ttl_seconds)
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
    )
    session.add(auth_session)
    session.flush()
    audit.append_event(
        session,
        faskes_id=user.faskes_id,
        entity_type="user",
        entity_id=user.id,
        event_type="auth.login",
        actor_type="user",
        actor_id=user.id,
        payload={"session_id": auth_session.id},
    )
    session.commit()
    return token, expires_at, _principal(user, auth_session.id)


def resolve_session(session: Session, token: str) -> Principal | None:
    now = utcnow()
    row = session.exec(
        select(AuthSession, AppUser)
        .join(AppUser, col(AppUser.id) == col(AuthSession.user_id))
        .where(
            AuthSession.token_hash == hash_session_token(token),
            col(AuthSession.revoked_at).is_(None),
            AuthSession.expires_at > now,
            col(AppUser.is_active).is_(True),
        )
    ).first()
    if row is None:
        return None
    auth_session, user = row
    if auth_session.last_seen_at is None or now - auth_session.last_seen_at > LAST_SEEN_REFRESH:
        auth_session.last_seen_at = now
        session.add(auth_session)
        session.commit()
    return _principal(user, auth_session.id)


def logout(session: Session, principal: Principal) -> None:
    if principal.session_id is None:
        return
    auth_session = session.get(AuthSession, principal.session_id)
    if auth_session is None or auth_session.revoked_at is not None:
        return
    auth_session.revoked_at = utcnow()
    session.add(auth_session)
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="user",
        entity_id=principal.user_id,
        event_type="auth.logout",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"session_id": principal.session_id},
    )
    session.commit()


def change_password(
    session: Session,
    principal: Principal,
    *,
    current_password: str,
    new_password: str,
    settings: Settings,
) -> int:
    credential = session.get(UserCredential, principal.user_id)
    if credential is None:
        raise unauthorized()
    now = utcnow()
    if credential.locked_until is not None and credential.locked_until > now:
        raise ApiError(
            429,
            "too_many_attempts",
            "Terlalu banyak percobaan. Coba lagi beberapa saat lagi.",
        )
    if not verify_password(current_password, credential.password_hash):
        _register_failure(
            session,
            credential,
            faskes_id=principal.faskes_id,
            user_id=principal.user_id,
            settings=settings,
            now=now,
            event_type="auth.password_change_failed",
        )
        session.commit()
        raise unprocessable("invalid_current_password", "Kata sandi saat ini salah")
    violation = password_policy_violation(new_password)
    if violation:
        raise unprocessable("weak_password", violation)
    if verify_password(new_password, credential.password_hash):
        raise unprocessable("password_unchanged", "Kata sandi baru harus berbeda dari yang lama")
    credential.password_hash = hash_password(new_password)
    credential.failed_attempts = 0
    credential.locked_until = None
    session.add(credential)
    revoked = _revoke_sessions(session, principal.user_id, now, keep=principal.session_id)
    audit.append_event(
        session,
        faskes_id=principal.faskes_id,
        entity_type="user",
        entity_id=principal.user_id,
        event_type="auth.password_changed",
        actor_type="user",
        actor_id=principal.user_id,
        payload={"sessions_revoked": revoked},
    )
    session.commit()
    return revoked


def reset_password(
    session: Session, *, actor: Principal, user_id: uuid.UUID, new_password: str
) -> int:
    user = session.get(AppUser, user_id)
    if user is None or user.faskes_id != actor.faskes_id:
        raise not_found("Pengguna")
    if user.id == actor.user_id:
        raise conflict("use_change_password", "Gunakan fitur ganti kata sandi untuk akun Anda sendiri")
    if Role(user.role) not in FASKES_ASSIGNABLE_ROLES:
        raise forbidden("Akun dengan peran tata kelola aturan tidak dapat diubah oleh admin faskes")
    violation = password_policy_violation(new_password)
    if violation:
        raise unprocessable("weak_password", violation)
    credential = session.get(UserCredential, user.id)
    if credential is None:
        raise not_found("Kredensial pengguna")
    now = utcnow()
    credential.password_hash = hash_password(new_password)
    credential.failed_attempts = 0
    credential.locked_until = None
    session.add(credential)
    revoked = _revoke_sessions(session, user.id, now)
    audit.append_event(
        session,
        faskes_id=actor.faskes_id,
        entity_type="user",
        entity_id=user.id,
        event_type="user.password_reset",
        actor_type="user",
        actor_id=actor.user_id,
        payload={"sessions_revoked": revoked},
    )
    session.commit()
    return revoked


def create_user(
    session: Session,
    *,
    actor: Principal,
    name: str,
    email: str,
    role: Role,
    password: str,
) -> AppUser:
    if role not in FASKES_ASSIGNABLE_ROLES:
        raise forbidden("Peran ini tidak dapat diberikan oleh admin faskes")
    violation = password_policy_violation(password)
    if violation:
        raise unprocessable("weak_password", violation)
    normalized = email.strip().lower()
    taken = session.exec(select(AppUser).where(func.lower(AppUser.email) == normalized)).first()
    if taken is not None:
        raise conflict("email_taken", "Email sudah terdaftar")
    user = AppUser(
        faskes_id=actor.faskes_id,
        name=name.strip(),
        email=normalized,
        role=role.value,
    )
    session.add(user)
    session.flush()
    session.add(UserCredential(user_id=user.id, password_hash=hash_password(password)))
    audit.append_event(
        session,
        faskes_id=actor.faskes_id,
        entity_type="user",
        entity_id=user.id,
        event_type="user.created",
        actor_type="user",
        actor_id=actor.user_id,
        payload={"role": role.value},
    )
    session.commit()
    return user


def list_users(session: Session, actor: Principal) -> list[AppUser]:
    return list(
        session.exec(
            select(AppUser)
            .where(AppUser.faskes_id == actor.faskes_id)
            .order_by(col(AppUser.name))
        )
    )


def update_user(
    session: Session,
    *,
    actor: Principal,
    user_id: uuid.UUID,
    role: Role | None,
    is_active: bool | None,
) -> AppUser:
    user = session.get(AppUser, user_id)
    if user is None or user.faskes_id != actor.faskes_id:
        raise not_found("Pengguna")
    if Role(user.role) not in FASKES_ASSIGNABLE_ROLES:
        raise forbidden("Akun dengan peran tata kelola aturan tidak dapat diubah oleh admin faskes")
    if role is not None and role not in FASKES_ASSIGNABLE_ROLES:
        raise forbidden("Peran ini tidak dapat diberikan oleh admin faskes")
    if user.id == actor.user_id and is_active is False:
        raise conflict("self_deactivation", "Anda tidak dapat menonaktifkan akun sendiri")
    changes: dict[str, object] = {}
    if role is not None and role.value != user.role:
        changes["role"] = {"from": user.role, "to": role.value}
        user.role = role.value
    if is_active is not None and is_active != user.is_active:
        changes["is_active"] = is_active
        user.is_active = is_active
        if not is_active:
            _revoke_sessions(session, user.id, utcnow())
    if changes:
        session.add(user)
        audit.append_event(
            session,
            faskes_id=actor.faskes_id,
            entity_type="user",
            entity_id=user.id,
            event_type="user.updated",
            actor_type="user",
            actor_id=actor.user_id,
            payload=changes,
        )
        session.commit()
    return user
