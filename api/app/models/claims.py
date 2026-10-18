import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Index, Text, func
from sqlmodel import Field, Relationship

from app.models.base import (
    TimestampedModel,
    jsonb_optional_field,
    timestamptz_field,
    utcnow,
)

if TYPE_CHECKING:
    from app.models.evidence import EvidenceItem
    from app.models.investigation import Finding, InvestigationJob, InvestigationRun
    from app.models.tenancy import AppUser, Faskes


class Claim(TimestampedModel, table=True):
    __tablename__ = "claim"
    __table_args__ = (Index("ix_claim_faskes_id_episode_no", "faskes_id", "episode_no"),)

    faskes_id: uuid.UUID = Field(foreign_key="faskes.id")
    episode_no: str
    patient_pseudonym: str
    inacbgb_result: dict[str, Any] | None = jsonb_optional_field()
    status: str
    submitted_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    submitted_at: datetime | None = timestamptz_field()
    locked_by: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    locked_at: datetime | None = timestamptz_field()
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )

    faskes: "Faskes" = Relationship(back_populates="claims")
    submitter: Optional["AppUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Claim.submitted_by]"}
    )
    locker: Optional["AppUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Claim.locked_by]"}
    )
    codes: list["ClaimCode"] = Relationship(back_populates="claim")
    evidence_items: list["EvidenceItem"] = Relationship(back_populates="claim")
    jobs: list["InvestigationJob"] = Relationship(back_populates="claim")
    runs: list["InvestigationRun"] = Relationship(back_populates="claim")


class ClaimCode(TimestampedModel, table=True):
    __tablename__ = "claim_code"

    claim_id: uuid.UUID = Field(foreign_key="claim.id", index=True)
    code_type: str
    code: str = Field(index=True)
    position: str | None = None
    description: str | None = Field(default=None, sa_type=Text)

    claim: "Claim" = Relationship(back_populates="codes")
    findings: list["Finding"] = Relationship(back_populates="claim_code")
