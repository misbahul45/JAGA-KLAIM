import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, func, text
from sqlmodel import Field, SQLModel

from app.models.base import (
    UUIDModel,
    check,
    created_at_field,
    timestamptz_field,
    utcnow,
)


class UserCredential(SQLModel, table=True):
    __tablename__ = "user_credential"
    __table_args__ = (check("failed_attempts_non_negative", "failed_attempts >= 0"),)

    user_id: uuid.UUID = Field(foreign_key="app_user.id", primary_key=True)
    password_hash: str
    failed_attempts: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    locked_until: datetime | None = timestamptz_field()
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class AuthSession(UUIDModel, table=True):
    __tablename__ = "auth_session"
    __table_args__ = (
        Index("ix_auth_session_user_id_expires_at", "user_id", "expires_at"),
        check("expiry_after_creation", "expires_at > created_at"),
    )

    user_id: uuid.UUID = Field(foreign_key="app_user.id")
    token_hash: str = Field(unique=True)
    created_at: datetime = created_at_field()
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    last_seen_at: datetime | None = timestamptz_field()
    revoked_at: datetime | None = timestamptz_field()
