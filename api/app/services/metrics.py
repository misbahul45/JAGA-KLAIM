from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, literal_column
from sqlmodel import Session, col, select

from app.domain.enums import RuleUpdateStatus, RunStatus, Tier, Verdict
from app.models import (
    Claim,
    CognitiveAssessment,
    EvidenceCitation,
    EvidenceSource,
    Finding,
    HumanVerdict,
    Intervention,
    InvestigationJob,
    InvestigationRun,
    RiskVector,
    RuleSet,
    RuleUpdate,
    RuleUpdateBasis,
    RuleVersion,
)
from app.models.base import utcnow
from app.services.auth import Principal

DEFAULT_WINDOW = timedelta(days=30)
REVIEW_TIER_VALUES = (Tier.T2.value, Tier.T3.value)


@dataclass
class Metric:
    code: str
    label: str
    definition: str
    unit: str
    target: str | None
    window_start: datetime
    window_end: datetime
    value: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    sample_size: int = 0
    status: str = "no_data"
    note: str | None = None
    breakdown: dict[str, Any] = field(default_factory=dict)


def _ratio(metric: Metric, numerator: int, denominator: int) -> Metric:
    metric.numerator = float(numerator)
    metric.denominator = float(denominator)
    metric.sample_size = denominator
    if denominator > 0:
        metric.value = round(numerator / denominator, 4)
        metric.status = "ok"
    return metric


def _superseded_ids():
    return (
        select(HumanVerdict.supersedes_verdict_id)
        .where(col(HumanVerdict.supersedes_verdict_id).is_not(None))
        .scalar_subquery()
    )


def compute_metrics(
    session: Session,
    principal: Principal,
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> list[Metric]:
    end = window_end or utcnow()
    start = window_start or (end - DEFAULT_WINDOW)
    faskes_id = principal.faskes_id
    hours = max((end - start).total_seconds() / 3600, 1e-9)

    def new(code: str, label: str, definition: str, unit: str, target: str | None) -> Metric:
        return Metric(code, label, definition, unit, target, start, end)

    metrics: list[Metric] = []

    completed = [RunStatus.SUCCEEDED.value, RunStatus.PARTIAL.value]
    run_filter = (
        InvestigationRun.faskes_id == faskes_id,
        col(InvestigationRun.status).in_(completed),
        InvestigationRun.started_at >= start,
        InvestigationRun.started_at <= end,
    )
    total_runs = session.exec(select(func.count()).select_from(InvestigationRun).where(*run_filter)).one()
    abstained_runs = session.exec(
        select(func.count())
        .select_from(InvestigationRun)
        .where(*run_filter, InvestigationRun.outcome == "abstained")
    ).one()
    metrics.append(
        _ratio(
            new(
                "abstention_rate",
                "System Abstention Rate (T0)",
                "Proporsi run investigasi (satu per vektor risiko) yang seluruh hasilnya abstain karena bukti tidak memadai.",
                "ratio",
                "Target awal ≤ 5% — belum divalidasi; dibaca bersama Precision agar abstain tidak dipakai sebagai jalan pintas.",
            ),
            abstained_runs,
            total_runs,
        )
    )

    valid_citations, all_citations = session.exec(
        select(
            func.count().filter(col(EvidenceCitation.validation_status) == "valid"),
            func.count(),
        )
        .select_from(EvidenceCitation)
        .join(Finding, col(Finding.id) == col(EvidenceCitation.finding_id))
        .where(
            Finding.faskes_id == faskes_id,
            EvidenceCitation.cited_at >= start,
            EvidenceCitation.cited_at <= end,
        )
    ).one()
    fidelity = _ratio(
        new(
            "citation_fidelity",
            "Citation Fidelity",
            "Proporsi sitasi yang lolos validasi (bukti ada, satu tenant dan klaim, hash cocok, kutipan sama dengan isi).",
            "ratio",
            "Target ≥ 0,80 tahun pertama — belum divalidasi; belum dipilah per kompleksitas kasus.",
        ),
        valid_citations,
        all_citations,
    )
    fidelity.note = "Mengukur integritas teknis sitasi, bukan kebenaran klinis temuan."
    metrics.append(fidelity)

    verdict_rows = session.exec(
        select(Intervention.tier, RiskVector.code, HumanVerdict.verdict, HumanVerdict.time_to_decision_ms)
        .join(Intervention, col(Intervention.id) == col(HumanVerdict.intervention_id))
        .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
        .join(RuleVersion, col(RuleVersion.id) == col(InvestigationRun.rule_version_id))
        .join(RuleSet, col(RuleSet.id) == col(RuleVersion.rule_set_id))
        .join(RiskVector, col(RiskVector.id) == col(RuleSet.vector_id))
        .where(
            Intervention.faskes_id == faskes_id,
            col(HumanVerdict.id).not_in(_superseded_ids()),
            HumanVerdict.created_at >= start,
            HumanVerdict.created_at <= end,
        )
    ).all()

    for tier in REVIEW_TIER_VALUES:
        tier_rows = [r for r in verdict_rows if r[0] == tier]
        accepted = sum(1 for r in tier_rows if r[2] == Verdict.SUPPORTS_FINDING.value)
        metric = _ratio(
            new(
                f"alert_acceptance_rate_{tier}",
                f"Alert Acceptance Rate {tier}",
                f"Proporsi verdict final pada intervensi {tier} yang menyatakan temuan didukung (supports_finding).",
                "ratio",
                "Diukur per tier; parameter pilot, tanpa ambang awal.",
            ),
            accepted,
            len(tier_rows),
        )
        metrics.append(metric)

    by_vector: dict[str, list[str]] = {}
    for _, vector_code, verdict, _ in verdict_rows:
        by_vector.setdefault(vector_code, []).append(verdict)
    flagged = len(verdict_rows)
    supported = sum(1 for r in verdict_rows if r[2] == Verdict.SUPPORTS_FINDING.value)
    precision = _ratio(
        new(
            "precision_of_flag_proxy",
            "Precision of Flag (proksi)",
            "Proporsi flag T2-T3 yang dinyatakan didukung oleh verifikator internal.",
            "ratio",
            "Target proposal ≥ 85% jangka menengah — belum tercapai/terbukti; ini proksi, bukan verifikasi ahli.",
        ),
        supported,
        flagged,
    )
    precision.breakdown = {
        vector: {
            "supported": sum(1 for v in verdicts if v == Verdict.SUPPORTS_FINDING.value),
            "total": len(verdicts),
        }
        for vector, verdicts in sorted(by_vector.items())
    }
    precision.note = (
        "Hanya keputusan verifikator internal; presisi sebenarnya memerlukan penilaian ahli casemix/RMIK."
    )
    metrics.append(precision)

    durations = sorted(r[3] for r in verdict_rows if r[3] is not None)
    time_metric = new(
        "time_to_verifier_decision",
        "Time to Verifier Decision",
        "Selang waktu dari intervensi dibuat sampai verdict pertama dicatat (median dan rata-rata).",
        "seconds",
        "Target awal < 180 detik — belum divalidasi; dihitung sejak intervensi dibuat, bukan sejak dibuka.",
    )
    if durations:
        middle = durations[len(durations) // 2]
        time_metric.value = round(middle / 1000, 2)
        time_metric.sample_size = len(durations)
        time_metric.status = "ok"
        time_metric.breakdown = {
            "mean_seconds": round(sum(durations) / len(durations) / 1000, 2),
            "max_seconds": round(durations[-1] / 1000, 2),
        }
    metrics.append(time_metric)

    hour_bucket = func.date_trunc(literal_column("'hour'"), Intervention.created_at)
    review_created = session.exec(
        select(hour_bucket, func.count())
        .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
        .where(
            Intervention.faskes_id == faskes_id,
            col(Intervention.tier).in_(REVIEW_TIER_VALUES),
            Intervention.created_at >= start,
            Intervention.created_at <= end,
        )
        .group_by(hour_bucket)
    ).all()
    load = new(
        "interruption_load",
        "Interruption Load",
        "Rata-rata jumlah intervensi T2-T3 per jam pada jendela waktu, beserta puncak per jam.",
        "alerts_per_hour",
        "Target awal < 15 alert/jam — belum divalidasi.",
    )
    total_alerts = sum(c for _, c in review_created)
    load.sample_size = total_alerts
    load.numerator = float(total_alerts)
    load.denominator = round(hours, 2)
    if total_alerts:
        load.value = round(total_alerts / hours, 4)
        load.status = "ok"
        load.breakdown = {"peak_alerts_in_one_hour": max(c for _, c in review_created)}
    metrics.append(load)

    assessments = session.exec(
        select(CognitiveAssessment.self_verdict)
        .join(Intervention, col(Intervention.id) == col(CognitiveAssessment.intervention_id))
        .where(
            Intervention.faskes_id == faskes_id,
            CognitiveAssessment.submitted_at >= start,
            CognitiveAssessment.submitted_at <= end,
        )
    ).all()
    agreement = _ratio(
        new(
            "independent_judgment_agreement",
            "Verifier Independent-Judgment Agreement Rate",
            "Proporsi penilaian mandiri verifikator (sebelum rekomendasi dibuka) yang sejalan dengan sikap sistem pada T2-T3, yaitu supports_finding.",
            "ratio",
            "Dipantau tanpa ambang awal; indikator dini automation bias.",
        ),
        sum(1 for s in assessments if s == Verdict.SUPPORTS_FINDING.value),
        len(assessments),
    )
    metrics.append(agreement)

    activated = session.exec(
        select(RuleUpdate.id)
        .join(HumanVerdict, col(HumanVerdict.id) == col(RuleUpdate.verdict_id))
        .join(Intervention, col(Intervention.id) == col(HumanVerdict.intervention_id))
        .where(
            Intervention.faskes_id == faskes_id,
            RuleUpdate.status == RuleUpdateStatus.ACTIVATED.value,
        )
    ).all()
    traced = 0
    if activated:
        traced = session.exec(
            select(func.count(func.distinct(RuleUpdateBasis.rule_update_id))).where(
                col(RuleUpdateBasis.rule_update_id).in_(activated)
            )
        ).one()
    metrics.append(
        _ratio(
            new(
                "verdict_to_update_traceability",
                "Verdict-to-Update Traceability",
                "Proporsi pembaruan rule yang diaktifkan dan tertelusur ke minimal satu human verdict.",
                "ratio",
                "Syarat minimum 100%.",
            ),
            traced,
            len(activated),
        )
    )

    for code, label, definition in (
        (
            "context_recall",
            "Context Recall",
            "Proporsi bukti relevan yang berhasil diambil; diukur terpisah dari faithfulness.",
        ),
        (
            "precision_drift",
            "Precision Drift Across Iterations",
            "Perubahan Precision antar-siklus pembaruan rule-set.",
        ),
    ):
        metric = new(code, label, definition, "ratio", "Dipantau tanpa ambang awal.")
        metric.status = "not_measured"
        metric.note = (
            "Belum diukur: memerlukan set validasi beranotasi pakar domain."
            if code == "context_recall"
            else "Belum diukur: memerlukan lebih dari satu siklus pembaruan rule-set yang tervalidasi."
        )
        metrics.append(metric)
    return metrics


@dataclass
class Dashboard:
    claims_by_status: dict[str, int]
    jobs_by_status: dict[str, int]
    open_review_by_tier: dict[str, int]
    run_outcomes_30d: dict[str, int]
    sources: list[dict[str, Any]]
    generated_at: datetime


def dashboard(session: Session, principal: Principal) -> Dashboard:
    faskes_id = principal.faskes_id
    claims = dict(
        session.exec(
            select(Claim.status, func.count()).where(Claim.faskes_id == faskes_id).group_by(Claim.status)
        ).all()
    )
    jobs = dict(
        session.exec(
            select(InvestigationJob.status, func.count())
            .where(InvestigationJob.faskes_id == faskes_id)
            .group_by(InvestigationJob.status)
        ).all()
    )
    open_review = dict(
        session.exec(
            select(Intervention.tier, func.count())
            .join(InvestigationRun, col(InvestigationRun.id) == col(Intervention.run_id))
            .join(Claim, col(Claim.id) == col(InvestigationRun.claim_id))
            .where(
                Intervention.faskes_id == faskes_id,
                col(Intervention.tier).in_(REVIEW_TIER_VALUES),
                col(Intervention.resolved_at).is_(None),
                col(InvestigationRun.stale_at).is_(None),
                InvestigationRun.claim_version == Claim.version,
            )
            .group_by(Intervention.tier)
        ).all()
    )
    since = utcnow() - DEFAULT_WINDOW
    outcomes = {
        outcome: count
        for outcome, count in session.exec(
            select(InvestigationRun.outcome, func.count())
            .where(
                InvestigationRun.faskes_id == faskes_id,
                InvestigationRun.started_at >= since,
                col(InvestigationRun.outcome).is_not(None),
            )
            .group_by(InvestigationRun.outcome)
        ).all()
        if outcome is not None
    }
    sources = [
        {
            "id": str(s.id),
            "source_type": s.source_type,
            "system_ref": s.system_ref,
            "health_status": s.health_status,
            "is_enabled": s.is_enabled,
            "last_synced_at": s.last_synced_at,
        }
        for s in session.exec(select(EvidenceSource).where(EvidenceSource.faskes_id == faskes_id))
    ]
    return Dashboard(claims, jobs, open_review, outcomes, sources, utcnow())
