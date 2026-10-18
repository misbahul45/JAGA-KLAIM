import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

EMBEDDING_DIM = 1024


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_field() -> Any:
    return Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )


def timestamptz_field() -> Any:
    return Field(default=None, sa_type=DateTime(timezone=True))


def required_timestamptz_field() -> Any:
    return Field(sa_type=DateTime(timezone=True))


def jsonb_object_field() -> Any:
    return Field(
        default_factory=dict,
        sa_type=JSONB,
        sa_column_kwargs={"server_default": text("'{}'::jsonb")},
    )


def jsonb_optional_field() -> Any:
    return Field(default=None, sa_type=JSONB)


def jsonb_required_field() -> Any:
    return Field(sa_type=JSONB)


class UUIDModel(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class TimestampedModel(UUIDModel):
    created_at: datetime = created_at_field()
