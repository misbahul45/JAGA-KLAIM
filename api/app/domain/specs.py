from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import CheckType

EVIDENCE_KINDS: tuple[str, ...] = (
    "resume_medis",
    "catatan_tindakan",
    "pemberian_obat",
    "hasil_lab",
    "hasil_radiologi",
    "catatan_keperawatan",
    "lainnya",
)

SOURCE_TYPES: tuple[str, ...] = (
    "emr",
    "lis",
    "ris",
    "farmasi",
    "keperawatan",
    "manual_simulasi",
)

ASSERTIONS: tuple[str, ...] = ("supports", "negates")

MAX_KEYWORDS = 20
MAX_KEYWORD_LENGTH = 80


class Requirement(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=200)
    evidence_kinds: list[str] = Field(default_factory=list)
    keywords_any: list[str] = Field(default_factory=list, max_length=MAX_KEYWORDS)
    source_types: list[str] = Field(default_factory=list)
    min_count: int = Field(default=1, ge=1, le=20)
    window: Literal["episode", "any"] = "episode"
    window_grace_hours: int = Field(default=0, ge=0, le=24 * 30)

    @field_validator("evidence_kinds")
    @classmethod
    def kinds_known(cls, value: list[str]) -> list[str]:
        unknown = [k for k in value if k not in EVIDENCE_KINDS]
        if unknown:
            raise ValueError(f"jenis bukti tidak dikenal: {', '.join(unknown)}")
        return value

    @field_validator("source_types")
    @classmethod
    def source_types_known(cls, value: list[str]) -> list[str]:
        unknown = [k for k in value if k not in SOURCE_TYPES]
        if unknown:
            raise ValueError(f"tipe sumber tidak dikenal: {', '.join(unknown)}")
        return value

    @field_validator("keywords_any")
    @classmethod
    def keywords_bounded(cls, value: list[str]) -> list[str]:
        cleaned = [k.strip() for k in value if k.strip()]
        if any(len(k) > MAX_KEYWORD_LENGTH for k in cleaned):
            raise ValueError(f"kata kunci maksimal {MAX_KEYWORD_LENGTH} karakter")
        return cleaned

    @model_validator(mode="after")
    def needs_matcher(self) -> "Requirement":
        if not self.evidence_kinds and not self.keywords_any:
            raise ValueError("requirement wajib punya evidence_kinds atau keywords_any")
        return self


class ExpectedEvidenceSpec(BaseModel):
    check: CheckType
    requirements: list[Requirement] = Field(default_factory=list)
    conflicts_with_codes: list[str] = Field(default_factory=list)
    anchor_kinds: list[str] = Field(default_factory=lambda: ["resume_medis"])
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def consistent_with_check(self) -> "ExpectedEvidenceSpec":
        if self.check is CheckType.BUNDLING_CONFLICT:
            if not self.conflicts_with_codes:
                raise ValueError("bundling_conflict wajib punya conflicts_with_codes")
        elif not self.requirements:
            raise ValueError(f"{self.check.value} wajib punya minimal satu requirement")
        ids = [r.id for r in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("id requirement harus unik")
        unknown = [k for k in self.anchor_kinds if k not in EVIDENCE_KINDS]
        if unknown:
            raise ValueError(f"anchor_kinds tidak dikenal: {', '.join(unknown)}")
        return self
