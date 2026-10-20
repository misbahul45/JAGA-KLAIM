import uuid
from typing import TYPE_CHECKING

from sqlalchemy import true
from sqlmodel import Field, Relationship

from app.domain.enums import Role, sql_values
from app.models.base import TimestampedModel, check

if TYPE_CHECKING:
    from app.models.claims import Claim


class Faskes(TimestampedModel, table=True):
    __tablename__ = "faskes"

    name: str
    type: str
    integration_mode: str
    region: str | None = None

    users: list["AppUser"] = Relationship(back_populates="faskes")
    claims: list["Claim"] = Relationship(back_populates="faskes")


class AppUser(TimestampedModel, table=True):
    __tablename__ = "app_user"
    __table_args__ = (check("role_valid", f"role IN ({sql_values(Role)})"),)

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id", index=True)
    name: str
    email: str = Field(unique=True)
    role: str
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})

    faskes: "Faskes" = Relationship(back_populates="users")
