import uuid
from datetime import UTC, datetime, timedelta

from app.domain.comparator import (
    ClaimView,
    CodeView,
    EvidenceView,
    RuleView,
    SourceView,
)
from app.domain.enums import RuleValidation
from app.domain.hashing import content_hash
from app.domain.specs import ExpectedEvidenceSpec

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
EPISODE_START = NOW - timedelta(days=5)
EPISODE_END = NOW - timedelta(days=2)


def code(value: str, code_type: str = "procedure", position: str | None = None) -> CodeView:
    return CodeView(uuid.uuid4(), code_type, value, position)


def claim(*codes: CodeView) -> ClaimView:
    return ClaimView(uuid.uuid4(), EPISODE_START, EPISODE_END, tuple(codes))


def source(
    source_type: str = "emr",
    *,
    health: str = "healthy",
    synced: datetime | None = NOW - timedelta(hours=1),
    enabled: bool = True,
    sla: int = 86400,
    ref: str | None = None,
) -> SourceView:
    return SourceView(
        id=uuid.uuid4(),
        source_type=source_type,
        system_ref=ref or f"SIM-{source_type.upper()}",
        is_enabled=enabled,
        health_status=health,
        last_synced_at=synced,
        freshness_sla_seconds=sla,
    )


def evidence(
    src: SourceView,
    text: str,
    *,
    kind: str = "resume_medis",
    assertion: str = "supports",
    recorded_at: datetime | None = None,
    quarantined: bool = False,
) -> EvidenceView:
    return EvidenceView(
        id=uuid.uuid4(),
        source_id=src.id,
        source_type=src.source_type,
        recorded_at=recorded_at or (EPISODE_START + timedelta(days=1)),
        kind=kind,
        assertion=assertion,
        text=text,
        content_hash=content_hash(text),
        quarantined=quarantined,
    )


def rule(
    spec: dict,
    *,
    pattern: str = "SIM-PROC-*",
    vector: str = "phantom_billing",
    validation: str = RuleValidation.SIMULATION.value,
) -> RuleView:
    return RuleView(
        id=uuid.uuid4(),
        rule_version_id=uuid.uuid4(),
        vector_code=vector,
        code_pattern=pattern,
        spec=ExpectedEvidenceSpec.model_validate(spec),
        validation_status=validation,
    )


PRESENCE_SPEC: dict = {
    "check": "evidence_presence",
    "requirements": [
        {
            "id": "R1",
            "label": "Catatan tindakan prosedur",
            "evidence_kinds": ["catatan_tindakan"],
            "keywords_any": ["tindakan prosedur"],
            "source_types": ["emr"],
        }
    ],
}

SEVERITY_SPEC: dict = {
    "check": "severity_support",
    "requirements": [
        {
            "id": "R1",
            "label": "Hasil lab pendukung komplikasi",
            "evidence_kinds": ["hasil_lab"],
            "keywords_any": ["komplikasi"],
            "source_types": ["lis"],
        },
        {
            "id": "R2",
            "label": "Catatan keperawatan pendukung",
            "evidence_kinds": ["catatan_keperawatan"],
            "keywords_any": ["komplikasi"],
            "source_types": ["keperawatan"],
        },
    ],
}

BUNDLING_SPEC: dict = {
    "check": "bundling_conflict",
    "conflicts_with_codes": ["SIM-PROC-900"],
}
