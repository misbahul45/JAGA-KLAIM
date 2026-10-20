import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.security import hash_password
from app.domain.default_policy import (
    DEFAULT_POLICY_RULES,
    POLICY_CONFIG,
    POLICY_VERSION_LABEL,
)
from app.domain.enums import (
    RiskVectorCode,
    Role,
    RuleValidation,
    VersionStatus,
)
from app.domain.hashing import config_hash, content_hash
from app.models import (
    AppUser,
    Claim,
    ClaimCode,
    EvidenceItem,
    EvidenceSource,
    ExpectedRule,
    Faskes,
    PolicyRule,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleVersion,
    UserCredential,
)
from app.models.base import utcnow

SIMULATION_NOTICE = "SIMULASI: bukan aturan klinis resmi dan belum divalidasi pakar casemix/RMIK"
SIMULATION_FRESHNESS_SECONDS = 365 * 24 * 3600

CATALOG: list[dict[str, Any]] = [
    {
        "vector": RiskVectorCode.PHANTOM_BILLING,
        "name": "Phantom billing",
        "description": "Bukti layanan yang diharapkan tidak ditemukan atau tidak cukup mendukung layanan yang ditagihkan.",
        "rule_set": "Kesesuaian bukti tindakan (simulasi)",
        "pattern": "SIM-PROC-1*",
        "spec": {
            "check": "evidence_presence",
            "note": SIMULATION_NOTICE,
            "requirements": [
                {
                    "id": "R1",
                    "label": "Catatan tindakan prosedur",
                    "evidence_kinds": ["catatan_tindakan"],
                    "keywords_any": ["tindakan prosedur"],
                    "source_types": ["emr"],
                    "window": "episode",
                    "window_grace_hours": 72,
                }
            ],
        },
    },
    {
        "vector": RiskVectorCode.UPCODING,
        "name": "Upcoding",
        "description": "Tingkat diagnosis, severity, atau tindakan yang dikodekan tidak selaras dengan bukti.",
        "rule_set": "Dukungan bukti tingkat keparahan (simulasi)",
        "pattern": "SIM-DX-2*",
        "spec": {
            "check": "severity_support",
            "note": SIMULATION_NOTICE,
            "requirements": [
                {
                    "id": "R1",
                    "label": "Hasil laboratorium pendukung komplikasi",
                    "evidence_kinds": ["hasil_lab"],
                    "keywords_any": ["komplikasi"],
                    "source_types": ["lis"],
                    "window": "episode",
                    "window_grace_hours": 72,
                },
                {
                    "id": "R2",
                    "label": "Catatan keperawatan pendukung komplikasi",
                    "evidence_kinds": ["catatan_keperawatan"],
                    "keywords_any": ["komplikasi"],
                    "source_types": ["keperawatan"],
                    "window": "episode",
                    "window_grace_hours": 72,
                },
            ],
        },
    },
    {
        "vector": RiskVectorCode.UNBUNDLING,
        "name": "Unbundling",
        "description": "Kode atau komponen layanan terpisah yang berpotensi tidak sesuai aturan pengelompokan.",
        "rule_set": "Kombinasi kode yang perlu diperiksa (simulasi)",
        "pattern": "SIM-PROC-3*",
        "spec": {
            "check": "bundling_conflict",
            "note": SIMULATION_NOTICE,
            "conflicts_with_codes": ["SIM-PROC-390"],
        },
    },
]

SIM_SOURCES: list[tuple[str, str]] = [
    ("emr", "SIM-EMR"),
    ("lis", "SIM-LIS"),
    ("keperawatan", "SIM-KEPERAWATAN"),
]


@dataclass(frozen=True)
class Catalog:
    rule_version_ids: dict[str, uuid.UUID]
    policy_version_id: uuid.UUID


def ensure_catalog(session: Session) -> Catalog:
    now = utcnow()
    rule_version_ids: dict[str, uuid.UUID] = {}
    for entry in CATALOG:
        vector_code = entry["vector"].value
        vector = session.exec(select(RiskVector).where(RiskVector.code == vector_code)).first()
        if vector is None:
            vector = RiskVector(
                code=vector_code, name=entry["name"], description=entry["description"]
            )
            session.add(vector)
            session.flush()
        rule_set = session.exec(
            select(RuleSet).where(RuleSet.vector_id == vector.id, RuleSet.name == entry["rule_set"])
        ).first()
        if rule_set is None:
            rule_set = RuleSet(
                vector_id=vector.id, name=entry["rule_set"], description=SIMULATION_NOTICE
            )
            session.add(rule_set)
            session.flush()
        version = session.exec(
            select(RuleVersion).where(
                RuleVersion.rule_set_id == rule_set.id,
                RuleVersion.status == VersionStatus.ACTIVE.value,
            )
        ).first()
        if version is None:
            version = RuleVersion(
                rule_set_id=rule_set.id,
                version="sim-1.0",
                status=VersionStatus.ACTIVE.value,
                validation_status=RuleValidation.SIMULATION.value,
                approved_at=now,
                activated_at=now,
            )
            session.add(version)
            session.flush()
            session.add(
                ExpectedRule(
                    rule_version_id=version.id,
                    code_pattern=entry["pattern"],
                    expected_evidence_spec=entry["spec"],
                )
            )
        rule_version_ids[vector_code] = version.id

    policy = session.exec(
        select(PolicyVersion).where(PolicyVersion.status == VersionStatus.ACTIVE.value)
    ).first()
    if policy is None:
        serialized_rules = [
            {
                "code": r["code"],
                "tier": r["tier"].value,
                "priority": r["priority"],
                "condition": r["condition"],
            }
            for r in DEFAULT_POLICY_RULES
        ]
        policy = PolicyVersion(
            version=POLICY_VERSION_LABEL,
            status=VersionStatus.ACTIVE.value,
            config=POLICY_CONFIG,
            config_hash=config_hash({"config": POLICY_CONFIG, "rules": serialized_rules}),
            approved_at=now,
            activated_at=now,
        )
        session.add(policy)
        session.flush()
        for r in DEFAULT_POLICY_RULES:
            session.add(
                PolicyRule(
                    policy_version_id=policy.id,
                    code=r["code"],
                    tier=r["tier"].value,
                    priority=r["priority"],
                    condition_spec=r["condition"],
                )
            )
    session.flush()
    return Catalog(rule_version_ids, policy.id)


@dataclass(frozen=True)
class SimFaskes:
    faskes_id: uuid.UUID
    user_ids: dict[str, uuid.UUID]
    source_ids: dict[str, uuid.UUID]
    emails: dict[str, str]


def create_user(
    session: Session, faskes_id: uuid.UUID, *, name: str, email: str, role: Role, password: str
) -> AppUser:
    user = AppUser(faskes_id=faskes_id, name=name, email=email.lower(), role=role.value)
    session.add(user)
    session.flush()
    session.add(UserCredential(user_id=user.id, password_hash=hash_password(password)))
    return user


def create_sim_faskes(
    session: Session, *, name: str, slug: str, password: str, with_sources: bool = True
) -> SimFaskes:
    faskes = Faskes(
        name=f"{name} (SIMULASI)", type="rumah_sakit", integration_mode="manual_simulasi"
    )
    session.add(faskes)
    session.flush()
    roles = {
        "coder": Role.CODER,
        "verifier": Role.VERIFIER,
        "admin": Role.FASKES_ADMIN,
        "auditor": Role.AUDITOR,
    }
    user_ids: dict[str, uuid.UUID] = {}
    emails: dict[str, str] = {}
    for key, role in roles.items():
        email = f"{key}.{slug}@example.com"
        user = create_user(
            session,
            faskes.id,
            name=f"{key.capitalize()} {name}",
            email=email,
            role=role,
            password=password,
        )
        user_ids[key] = user.id
        emails[key] = email
    source_ids: dict[str, uuid.UUID] = {}
    if with_sources:
        now = utcnow()
        for source_type, ref in SIM_SOURCES:
            source = EvidenceSource(
                faskes_id=faskes.id,
                source_type=source_type,
                system_ref=ref,
                health_status="healthy",
                last_health_check_at=now,
                last_synced_at=now,
                freshness_sla_seconds=SIMULATION_FRESHNESS_SECONDS,
                config={"mode": "manual_simulasi"},
            )
            session.add(source)
            session.flush()
            source_ids[source_type] = source.id
    session.flush()
    return SimFaskes(faskes.id, user_ids, source_ids, emails)


def create_claim(
    session: Session,
    faskes_id: uuid.UUID,
    *,
    episode_no: str,
    pseudonym: str,
    codes: list[tuple[str, str]],
    status: str = "draft",
    episode_days_ago: int = 5,
    episode_length_days: int = 3,
    submitted_by: uuid.UUID | None = None,
) -> Claim:
    start = utcnow() - timedelta(days=episode_days_ago)
    claim = Claim(
        faskes_id=faskes_id,
        episode_no=episode_no,
        patient_pseudonym=pseudonym,
        status=status,
        episode_start=start,
        episode_end=start + timedelta(days=episode_length_days),
        inacbgb_result={"simulasi": True},
        submitted_by=submitted_by,
    )
    session.add(claim)
    session.flush()
    for index, (code_type, code) in enumerate(codes):
        session.add(
            ClaimCode(
                claim_id=claim.id,
                code_type=code_type,
                code=code,
                position="primary" if index == 0 else "secondary",
            )
        )
    session.flush()
    return claim


def add_evidence(
    session: Session,
    claim: Claim,
    source_id: uuid.UUID,
    *,
    kind: str,
    text: str,
    assertion: str = "supports",
    day_offset: float = 1.0,
) -> EvidenceItem:
    item = EvidenceItem(
        faskes_id=claim.faskes_id,
        source_id=source_id,
        claim_id=claim.id,
        recorded_at=(claim.episode_start or utcnow()) + timedelta(days=day_offset),
        content_text=text,
        content_ref={"kind": kind, "assertion": assertion},
        content_hash=content_hash(text),
    )
    session.add(item)
    session.flush()
    return item


DEMO_CLAIMS: list[dict[str, Any]] = [
    {
        "episode_no": "SIM-EP-0001",
        "pseudonym": "PSEUDO-SIM-0001",
        "codes": [("procedure", "SIM-PROC-101")],
        "evidence": [("emr", "resume_medis", "Resume sintetis: pasien dirawat, kondisi membaik, pulang atas persetujuan dokter.")],
        "scenario": "Bukti tindakan belum ditemukan (diharapkan T3 pada aturan simulasi)",
    },
    {
        "episode_no": "SIM-EP-0002",
        "pseudonym": "PSEUDO-SIM-0002",
        "codes": [("procedure", "SIM-PROC-102")],
        "evidence": [
            ("emr", "resume_medis", "Resume sintetis: pasien menjalani prosedur terjadwal tanpa kendala."),
            ("emr", "catatan_tindakan", "Catatan sintetis: tindakan prosedur dilakukan oleh dokter pelaksana, durasi 45 menit."),
        ],
        "scenario": "Bukti lengkap (diharapkan No Action)",
    },
    {
        "episode_no": "SIM-EP-0003",
        "pseudonym": "PSEUDO-SIM-0003",
        "codes": [("diagnosis", "SIM-DX-201")],
        "evidence": [
            ("emr", "resume_medis", "Resume sintetis: pasien dirawat dengan penyulit."),
            ("lis", "hasil_lab", "Hasil lab sintetis: indikator komplikasi terdeteksi pada hari ke-2."),
        ],
        "scenario": "Dukungan keparahan hanya sebagian (diharapkan T2)",
    },
    {
        "episode_no": "SIM-EP-0004",
        "pseudonym": "PSEUDO-SIM-0004",
        "codes": [("procedure", "SIM-PROC-301"), ("procedure", "SIM-PROC-390")],
        "evidence": [("emr", "resume_medis", "Resume sintetis: dua tindakan dicatat pada episode yang sama.")],
        "scenario": "Kombinasi kode ditandai aturan pengelompokan (diharapkan T3)",
    },
]


def seed_demo_claims(session: Session, sim: SimFaskes) -> list[Claim]:
    claims: list[Claim] = []
    for spec in DEMO_CLAIMS:
        existing = session.exec(
            select(Claim).where(
                Claim.faskes_id == sim.faskes_id, Claim.episode_no == spec["episode_no"]
            )
        ).first()
        if existing is not None:
            claims.append(existing)
            continue
        claim = create_claim(
            session,
            sim.faskes_id,
            episode_no=spec["episode_no"],
            pseudonym=spec["pseudonym"],
            codes=spec["codes"],
        )
        for source_type, kind, text in spec["evidence"]:
            add_evidence(session, claim, sim.source_ids[source_type], kind=kind, text=text)
        claims.append(claim)
    session.flush()
    return claims
