import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.assessment import abstained, assess, surfaced
from app.domain.citations import EvidenceRecord
from app.domain.comparator import (
    ClaimView,
    CodeView,
    EvidenceView,
    RuleView,
    SourceView,
)
from app.domain.hashing import content_hash
from app.domain.policy import PolicyRuleView
from app.domain.synthesis import TemplateSynthesizer
from app.domain.tools import StepRecorder
from app.evaluation.cases import (
    CASES,
    EVALUATION_SET_LABEL,
    HEALTHY,
    EvalCase,
    Expected,
)

REFERENCE_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
ENGINE_FAMILY = "deterministic-comparator/1.0.0"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    vector: str
    expected: Expected
    actual: Expected
    tiers: tuple[str, ...]
    citations_valid: int
    citations_total: int

    @property
    def correct(self) -> bool:
        return self.expected == self.actual


@dataclass
class VectorMetrics:
    cases: int = 0
    correct: int = 0
    flagged: int = 0
    flagged_correct: int = 0
    expected_flags: int = 0
    expected_flags_found: int = 0
    abstained: int = 0
    citations_valid: int = 0
    citations_total: int = 0

    def as_dict(self) -> dict[str, Any]:
        def ratio(numerator: int, denominator: int) -> float | None:
            return round(numerator / denominator, 4) if denominator else None

        return {
            "cases": self.cases,
            "accuracy": ratio(self.correct, self.cases),
            "flag_precision": ratio(self.flagged_correct, self.flagged),
            "flag_recall": ratio(self.expected_flags_found, self.expected_flags),
            "abstention_rate": ratio(self.abstained, self.cases),
            "citation_fidelity": ratio(self.citations_valid, self.citations_total),
            "flagged": self.flagged,
            "expected_flags": self.expected_flags,
        }


@dataclass
class EvaluationReport:
    results: list[CaseResult]
    per_vector: dict[str, VectorMetrics] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        overall = VectorMetrics()
        for metrics in self.per_vector.values():
            for name in overall.__dataclass_fields__:
                setattr(overall, name, getattr(overall, name) + getattr(metrics, name))
        return {
            "engine": ENGINE_FAMILY,
            "validation_set": EVALUATION_SET_LABEL,
            "overall": overall.as_dict(),
            "per_vector": {v: m.as_dict() for v, m in sorted(self.per_vector.items())},
            "cases": [
                {
                    "id": r.case_id,
                    "vector": r.vector,
                    "expected": r.expected,
                    "actual": r.actual,
                    "correct": r.correct,
                    "tiers": list(r.tiers),
                }
                for r in self.results
            ],
        }


def _views(case: EvalCase) -> tuple[ClaimView, list[EvidenceView], list[SourceView], uuid.UUID]:
    faskes_id = uuid.uuid4()
    episode_end = REFERENCE_NOW - timedelta(hours=case.episode_end_hours_ago)
    episode_start = episode_end - timedelta(days=3)
    claim = ClaimView(
        id=uuid.uuid4(),
        episode_start=episode_start,
        episode_end=episode_end,
        codes=tuple(CodeView(uuid.uuid4(), "procedure", code, None) for code in case.codes),
    )
    source_specs = HEALTHY if case.sources is None else case.sources
    sources = [
        SourceView(
            id=uuid.uuid4(),
            source_type=s.source_type,
            system_ref=f"EVAL-{s.source_type.upper()}",
            is_enabled=s.enabled,
            health_status=s.health,
            last_synced_at=REFERENCE_NOW - timedelta(hours=s.synced_hours_ago),
            freshness_sla_seconds=365 * 24 * 3600,
        )
        for s in source_specs
    ]
    by_type = {s.source_type: s for s in sources}
    evidence: list[EvidenceView] = []
    for item in case.evidence:
        source = by_type.get(item.source_type) or SourceView(
            uuid.uuid4(), item.source_type, f"EVAL-{item.source_type.upper()}", True, "healthy", REFERENCE_NOW, 1
        )
        evidence.append(
            EvidenceView(
                id=uuid.uuid4(),
                source_id=source.id,
                source_type=item.source_type,
                recorded_at=episode_start + timedelta(days=item.day_offset),
                kind=item.kind,
                assertion=item.assertion,
                text=item.text,
                content_hash=content_hash(item.text),
                quarantined=item.quarantined,
            )
        )
    return claim, evidence, sources, faskes_id


def run_case(
    case: EvalCase, rules: list[RuleView], policy_rules: list[PolicyRuleView]
) -> CaseResult:
    claim, evidence, sources, faskes_id = _views(case)
    records = {
        e.id: EvidenceRecord(e.id, faskes_id, claim.id, e.text, e.content_hash) for e in evidence
    }
    relevant = [r for r in rules if r.vector_code == case.vector]
    assessed = assess(
        faskes_id=faskes_id,
        claim=claim,
        rules=relevant,
        policy_rules=policy_rules,
        evidence=evidence,
        sources=sources,
        now=REFERENCE_NOW,
        records_provider=lambda ids: {i: records[i] for i in ids if i in records},
        synthesizer=TemplateSynthesizer(),
        recorder=StepRecorder(),
    )
    flags = surfaced(assessed)
    abstains = abstained(assessed)
    actual: Expected = "flag" if flags else "abstain" if abstains else "no_action"
    valid = sum(len(a.valid_citations) for a in assessed)
    total = sum(len(a.verdicts) for a in assessed)
    tiers = tuple(sorted(a.final_tier.value for a in assessed if a.final_tier))
    return CaseResult(case.id, case.vector, case.expected, actual, tiers, valid, total)


def evaluate(
    rules: list[RuleView],
    policy_rules: list[PolicyRuleView],
    cases: tuple[EvalCase, ...] = CASES,
) -> EvaluationReport:
    report = EvaluationReport(results=[])
    for case in cases:
        result = run_case(case, rules, policy_rules)
        report.results.append(result)
        metrics = report.per_vector.setdefault(case.vector, VectorMetrics())
        metrics.cases += 1
        metrics.correct += 1 if result.correct else 0
        if result.actual == "flag":
            metrics.flagged += 1
            metrics.flagged_correct += 1 if result.expected == "flag" else 0
            metrics.citations_valid += result.citations_valid
            metrics.citations_total += result.citations_total
        if result.expected == "flag":
            metrics.expected_flags += 1
            metrics.expected_flags_found += 1 if result.actual == "flag" else 0
        if result.actual == "abstain":
            metrics.abstained += 1
    return report


def compare_reports(baseline: EvaluationReport, candidate: EvaluationReport) -> dict[str, Any]:
    base = {r.case_id: r for r in baseline.results}
    regressions: list[str] = []
    improvements: list[str] = []
    changed: list[dict[str, Any]] = []
    for result in candidate.results:
        before = base[result.case_id]
        if before.actual != result.actual:
            changed.append(
                {"id": result.case_id, "from": before.actual, "to": result.actual, "expected": result.expected}
            )
        if before.correct and not result.correct:
            regressions.append(result.case_id)
        elif not before.correct and result.correct:
            improvements.append(result.case_id)
    return {
        "regressions": regressions,
        "improvements": improvements,
        "changed_cases": changed,
        "baseline": baseline.as_dict(),
        "candidate": candidate.as_dict(),
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
    }
