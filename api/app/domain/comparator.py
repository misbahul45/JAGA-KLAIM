import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fnmatch import fnmatchcase
from typing import Any

from app.domain.enums import CheckType, HealthStatus
from app.domain.specs import ExpectedEvidenceSpec, Requirement


@dataclass(frozen=True)
class CodeView:
    id: uuid.UUID
    code_type: str
    code: str
    position: str | None


@dataclass(frozen=True)
class SourceView:
    id: uuid.UUID
    source_type: str
    system_ref: str
    is_enabled: bool
    health_status: str
    last_synced_at: datetime | None
    freshness_sla_seconds: int


@dataclass(frozen=True)
class EvidenceView:
    id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    recorded_at: datetime
    kind: str
    assertion: str
    text: str
    content_hash: str
    quarantined: bool


@dataclass(frozen=True)
class ClaimView:
    id: uuid.UUID
    episode_start: datetime | None
    episode_end: datetime | None
    codes: tuple[CodeView, ...]


@dataclass(frozen=True)
class RuleView:
    id: uuid.UUID
    rule_version_id: uuid.UUID
    vector_code: str
    code_pattern: str
    spec: ExpectedEvidenceSpec
    validation_status: str


@dataclass
class RequirementOutcome:
    requirement: Requirement
    satisfied: bool
    supporting_ids: list[uuid.UUID] = field(default_factory=list)
    negating_ids: list[uuid.UUID] = field(default_factory=list)
    out_of_window_ids: list[uuid.UUID] = field(default_factory=list)
    quarantined_ids: list[uuid.UUID] = field(default_factory=list)
    coverage_adequate: bool = True
    coverage_gaps: list[str] = field(default_factory=list)
    searched_source_ids: list[uuid.UUID] = field(default_factory=list)
    unresolved_conflict: bool = False


@dataclass
class Comparison:
    rule: RuleView
    code: CodeView
    outcomes: list[RequirementOutcome]
    conflicting_codes: list[CodeView]

    @property
    def check(self) -> CheckType:
        return self.rule.spec.check

    @property
    def unmet(self) -> list[RequirementOutcome]:
        return [o for o in self.outcomes if not o.satisfied]

    @property
    def delta_present(self) -> bool:
        if self.check is CheckType.BUNDLING_CONFLICT:
            return bool(self.conflicting_codes)
        return bool(self.unmet)

    @property
    def coverage_adequate(self) -> bool:
        return all(o.coverage_adequate for o in self.unmet)

    @property
    def unresolved_conflict(self) -> bool:
        return any(o.unresolved_conflict for o in self.outcomes)

    @property
    def coverage_gaps(self) -> list[str]:
        gaps: list[str] = []
        for outcome in self.unmet:
            for gap in outcome.coverage_gaps:
                if gap not in gaps:
                    gaps.append(gap)
        return gaps

    @property
    def needs_decision(self) -> bool:
        return self.delta_present or not self.coverage_adequate or self.unresolved_conflict


def _source_gaps(source: SourceView, claim: ClaimView, now: datetime) -> list[str]:
    gaps: list[str] = []
    if source.health_status != HealthStatus.HEALTHY.value:
        gaps.append(f"sumber '{source.system_ref}' berstatus {source.health_status}")
    if source.last_synced_at is None:
        gaps.append(f"sumber '{source.system_ref}' belum pernah disinkronkan")
    else:
        if claim.episode_end is not None and source.last_synced_at < claim.episode_end:
            gaps.append(
                f"sinkronisasi terakhir sumber '{source.system_ref}' terjadi sebelum episode berakhir"
            )
        if now - source.last_synced_at > timedelta(seconds=source.freshness_sla_seconds):
            gaps.append(f"sinkronisasi sumber '{source.system_ref}' sudah melewati batas kesegaran")
    return gaps


def evaluate_coverage(
    requirement: Requirement,
    sources: list[SourceView],
    claim: ClaimView,
    now: datetime,
) -> tuple[bool, list[str], list[uuid.UUID]]:
    enabled = [s for s in sources if s.is_enabled]
    wanted_types = requirement.source_types or sorted({s.source_type for s in enabled})
    if not wanted_types:
        return False, ["tidak ada sumber bukti aktif untuk faskes ini"], []
    gaps: list[str] = []
    searched: list[uuid.UUID] = []
    adequate = True
    for source_type in wanted_types:
        candidates = [s for s in enabled if s.source_type == source_type]
        if not candidates:
            gaps.append(f"tidak ada sumber aktif bertipe '{source_type}'")
            adequate = False
            continue
        usable = [s for s in candidates if not _source_gaps(s, claim, now)]
        if usable:
            searched.extend(s.id for s in usable)
            continue
        adequate = False
        for source in candidates:
            gaps.extend(g for g in _source_gaps(source, claim, now) if g not in gaps)
    return adequate, gaps, searched


def _matches(requirement: Requirement, evidence: EvidenceView) -> bool:
    if requirement.source_types and evidence.source_type not in requirement.source_types:
        return False
    if requirement.evidence_kinds and evidence.kind not in requirement.evidence_kinds:
        return False
    if requirement.keywords_any:
        haystack = evidence.text.lower()
        if not any(keyword.lower() in haystack for keyword in requirement.keywords_any):
            return False
    return True


def _structure_matches(requirement: Requirement, evidence: EvidenceView) -> bool:
    if requirement.source_types and evidence.source_type not in requirement.source_types:
        return False
    if requirement.evidence_kinds and evidence.kind not in requirement.evidence_kinds:
        return False
    return True


def _in_window(requirement: Requirement, claim: ClaimView, evidence: EvidenceView) -> bool:
    if requirement.window == "any":
        return True
    grace = timedelta(hours=requirement.window_grace_hours)
    if claim.episode_start is not None and evidence.recorded_at < claim.episode_start - grace:
        return False
    if claim.episode_end is not None and evidence.recorded_at > claim.episode_end + grace:
        return False
    return True


def _distinct_by_hash(items: list[EvidenceView]) -> list[EvidenceView]:
    seen: set[str] = set()
    distinct: list[EvidenceView] = []
    for item in items:
        if item.content_hash not in seen:
            seen.add(item.content_hash)
            distinct.append(item)
    return distinct


def evaluate_requirement(
    requirement: Requirement,
    claim: ClaimView,
    evidence: list[EvidenceView],
    sources: list[SourceView],
    now: datetime,
) -> RequirementOutcome:
    trusted = [e for e in evidence if not e.quarantined]
    matched = [e for e in trusted if _matches(requirement, e)]
    in_window = [e for e in matched if _in_window(requirement, claim, e)]
    out_of_window = [e for e in matched if not _in_window(requirement, claim, e)]
    supporting = _distinct_by_hash([e for e in in_window if e.assertion != "negates"])
    negating = [e for e in in_window if e.assertion == "negates"]
    satisfied = len(supporting) >= requirement.min_count
    outcome = RequirementOutcome(
        requirement=requirement,
        satisfied=satisfied,
        supporting_ids=[e.id for e in supporting],
        negating_ids=[e.id for e in negating],
        out_of_window_ids=[e.id for e in out_of_window if e.assertion != "negates"],
        unresolved_conflict=satisfied and bool(negating),
    )
    if satisfied:
        return outcome
    adequate, gaps, searched = evaluate_coverage(requirement, sources, claim, now)
    outcome.searched_source_ids = searched
    quarantined = [
        e.id for e in evidence if e.quarantined and _structure_matches(requirement, e)
    ]
    if quarantined:
        adequate = False
        gaps = [*gaps, "ada bukti yang dikarantina karena dugaan instruksi tersisip dan belum ditinjau manusia"]
        outcome.quarantined_ids = quarantined
    outcome.coverage_adequate = adequate
    outcome.coverage_gaps = gaps
    return outcome


def compare(
    claim: ClaimView,
    rules: list[RuleView],
    evidence: list[EvidenceView],
    sources: list[SourceView],
    now: datetime,
) -> list[Comparison]:
    comparisons: list[Comparison] = []
    for rule in rules:
        for code in claim.codes:
            if not fnmatchcase(code.code, rule.code_pattern):
                continue
            conflicts: list[CodeView] = []
            if rule.spec.check is CheckType.BUNDLING_CONFLICT:
                conflicts = [
                    other
                    for other in claim.codes
                    if other.id != code.id
                    and any(fnmatchcase(other.code, p) for p in rule.spec.conflicts_with_codes)
                ]
            outcomes = [
                evaluate_requirement(req, claim, evidence, sources, now)
                for req in rule.spec.requirements
            ]
            comparisons.append(Comparison(rule, code, outcomes, conflicts))
    return comparisons


def derive_facts(comparison: Comparison) -> dict[str, Any]:
    unmet = comparison.unmet
    if comparison.check is CheckType.BUNDLING_CONFLICT:
        missing_ratio = 1.0 if comparison.conflicting_codes else 0.0
    elif comparison.outcomes:
        missing_ratio = round(len(unmet) / len(comparison.outcomes), 4)
    else:
        missing_ratio = 0.0
    return {
        "vector_code": comparison.rule.vector_code,
        "check_type": comparison.check.value,
        "rule_validation": comparison.rule.validation_status,
        "delta_present": comparison.delta_present,
        "coverage_adequate": comparison.coverage_adequate,
        "unresolved_conflict": comparison.unresolved_conflict,
        "has_contradiction": any(o.negating_ids for o in unmet),
        "only_out_of_window_matches": bool(unmet) and all(o.out_of_window_ids for o in unmet),
        "missing_ratio": missing_ratio,
        "citation_valid_count": 0,
        "citation_invalid_count": 0,
    }
