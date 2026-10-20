import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.citations import (
    CandidateCitation,
    CitationVerdict,
    EvidenceRecord,
    build_candidates,
    validate_citations,
)
from app.domain.comparator import (
    ClaimView,
    Comparison,
    EvidenceView,
    RuleView,
    SourceView,
    compare,
    derive_facts,
)
from app.domain.enums import RunOutcome, Tier
from app.domain.policy import PolicyDecision, PolicyRuleView, decide
from app.domain.safety import govern
from app.domain.synthesis import (
    SynthesizedFinding,
    Synthesizer,
    enforce_output_policy,
)
from app.domain.tools import StepRecorder

RecordsProvider = Callable[[set[uuid.UUID]], dict[uuid.UUID, EvidenceRecord]]


@dataclass
class Assessed:
    comparison: Comparison
    facts: dict[str, Any]
    candidates: list[CandidateCitation] = field(default_factory=list)
    verdicts: list[CitationVerdict] = field(default_factory=list)
    decision: PolicyDecision | None = None
    final_tier: Tier | None = None
    governor_reasons: list[str] = field(default_factory=list)
    synthesized: SynthesizedFinding | None = None

    @property
    def valid_citations(self) -> list[CitationVerdict]:
        return [v for v in self.verdicts if v.valid]


def assess(
    *,
    faskes_id: uuid.UUID,
    claim: ClaimView,
    rules: list[RuleView],
    policy_rules: list[PolicyRuleView],
    evidence: list[EvidenceView],
    sources: list[SourceView],
    now: datetime,
    records_provider: RecordsProvider,
    synthesizer: Synthesizer,
    recorder: StepRecorder,
) -> list[Assessed]:
    comparisons = recorder.run(
        "compare",
        "compare_expected_observed",
        lambda: compare(claim, rules, evidence, sources, now),
        summarize=lambda c: {
            "comparisons": len(c),
            "needing_decision": sum(1 for x in c if x.needs_decision),
        },
    )
    assessed = [Assessed(c, derive_facts(c)) for c in comparisons if c.needs_decision]

    def validate_all() -> int:
        total = 0
        for item in assessed:
            cmp = item.comparison
            if cmp.delta_present and cmp.coverage_adequate and not cmp.unresolved_conflict:
                item.candidates = build_candidates(cmp, evidence)
                records = records_provider({c.evidence_item_id for c in item.candidates})
                item.verdicts = validate_citations(
                    item.candidates, records, faskes_id=faskes_id, claim_id=claim.id
                )
            item.facts["citation_valid_count"] = len(item.valid_citations)
            item.facts["citation_invalid_count"] = len(item.verdicts) - len(item.valid_citations)
            total += len(item.verdicts)
        return total

    recorder.run(
        "validate_citations",
        "validate_citations",
        validate_all,
        summarize=lambda _: {
            "valid": sum(len(a.valid_citations) for a in assessed),
            "invalid": sum(len(a.verdicts) - len(a.valid_citations) for a in assessed),
        },
    )

    def decide_all() -> None:
        for item in assessed:
            item.decision = decide(policy_rules, item.facts)
            item.final_tier = item.decision.tier

    recorder.run(
        "policy_decide",
        "policy_engine",
        decide_all,
        summarize=lambda _: {
            "decisions": [
                {
                    "code": a.comparison.code.code,
                    "rule": a.decision.rule_code,
                    "tier": a.decision.tier.value,
                }
                for a in assessed
                if a.decision
            ]
        },
    )

    def govern_all() -> int:
        overrides = 0
        for item in assessed:
            assert item.decision is not None
            verdict = govern(
                tier=item.decision.tier,
                rule_validation=item.facts["rule_validation"],
                citation_valid_count=item.facts["citation_valid_count"],
                coverage_adequate=item.facts["coverage_adequate"],
                unresolved_conflict=item.facts["unresolved_conflict"],
            )
            item.final_tier = verdict.tier
            item.governor_reasons = verdict.reasons
            overrides += 1 if verdict.overridden else 0
        return overrides

    recorder.run(
        "safety_check",
        "safety_governor",
        govern_all,
        summarize=lambda overrides: {"overrides": overrides},
    )

    def synthesize_all() -> int:
        count = 0
        for item in assessed:
            if item.final_tier is not None and item.final_tier is not Tier.T0:
                item.synthesized = enforce_output_policy(
                    item.comparison, synthesizer.synthesize(item.comparison)
                )
                count += 1
        return count

    recorder.run(
        "synthesize",
        "template_synthesizer",
        synthesize_all,
        summarize=lambda count: {"findings": count},
    )
    return assessed


def surfaced(assessed: list[Assessed]) -> list[Assessed]:
    return [a for a in assessed if a.final_tier is not None and a.final_tier is not Tier.T0]


def abstained(assessed: list[Assessed]) -> list[Assessed]:
    return [a for a in assessed if a.final_tier is Tier.T0]


def outcome_of(assessed: list[Assessed]) -> RunOutcome:
    if surfaced(assessed):
        return RunOutcome.FINDINGS
    if abstained(assessed):
        return RunOutcome.ABSTAINED
    return RunOutcome.NO_ACTION
