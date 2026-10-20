import uuid

import pytest

from app.domain.default_policy import DEFAULT_POLICY_RULES
from app.domain.enums import Tier
from app.domain.policy import (
    PolicyRuleView,
    PolicyValidationError,
    decide,
    validate_policy,
)
from app.domain.safety import govern


def default_rules() -> list[PolicyRuleView]:
    return [
        PolicyRuleView(
            id=uuid.uuid4(),
            code=r["code"],
            tier=r["tier"],
            priority=r["priority"],
            condition=r["condition"],
        )
        for r in DEFAULT_POLICY_RULES
    ]


def facts(**overrides):
    base = {
        "vector_code": "phantom_billing",
        "check_type": "evidence_presence",
        "rule_validation": "simulasi",
        "delta_present": True,
        "coverage_adequate": True,
        "unresolved_conflict": False,
        "has_contradiction": False,
        "only_out_of_window_matches": False,
        "missing_ratio": 1.0,
        "citation_valid_count": 1,
        "citation_invalid_count": 0,
    }
    base.update(overrides)
    return base


def test_default_policy_is_valid():
    validate_policy(default_rules())


@pytest.mark.parametrize(
    ("overrides", "tier", "rule"),
    [
        ({}, Tier.T3, "T3_FULL_DELTA"),
        ({"missing_ratio": 0.5}, Tier.T2, "T2_PARTIAL_DELTA"),
        ({"missing_ratio": 0.25}, Tier.T1, "T1_MINOR_DELTA"),
        ({"coverage_adequate": False}, Tier.T0, "T0_COVERAGE_INADEQUATE"),
        ({"unresolved_conflict": True}, Tier.T0, "T0_UNRESOLVED_CONFLICT"),
        ({"citation_valid_count": 0}, Tier.T0, "T0_CITATION_UNVERIFIED"),
        ({"rule_validation": "belum_tervalidasi"}, Tier.T1, "T1_UNVALIDATED_RULE_CAP"),
        ({"only_out_of_window_matches": True}, Tier.T1, "T1_OUT_OF_EPISODE_WINDOW"),
    ],
)
def test_decision_table(overrides, tier, rule):
    decision = decide(default_rules(), facts(**overrides))
    assert decision.tier is tier
    assert decision.rule_code == rule


def test_abstain_takes_precedence_over_full_delta():
    decision = decide(default_rules(), facts(coverage_adequate=False, missing_ratio=1.0))
    assert decision.tier is Tier.T0


def test_decision_is_deterministic_for_identical_facts():
    rules = default_rules()
    outcomes = {decide(rules, facts()).rule_code for _ in range(50)}
    assert outcomes == {"T3_FULL_DELTA"}


def test_inactive_rules_are_ignored():
    rules = default_rules()
    disabled = [
        PolicyRuleView(r.id, r.code, r.tier, r.priority, r.condition, is_active=r.code != "T3_FULL_DELTA")
        for r in rules
    ]
    assert decide(disabled, facts()).tier is Tier.T2


def test_missing_catch_all_is_rejected():
    rules = [r for r in default_rules() if r.code != "T1_MINOR_DELTA"]
    with pytest.raises(PolicyValidationError) as exc:
        validate_policy(rules)
    assert any("penampung" in p for p in exc.value.problems)


def test_t0_after_risk_rule_is_rejected():
    rules = default_rules()
    broken = [
        PolicyRuleView(r.id, r.code, r.tier, 65 if r.code == "T0_CITATION_UNVERIFIED" else r.priority, r.condition)
        for r in rules
    ]
    with pytest.raises(PolicyValidationError) as exc:
        validate_policy(broken)
    assert any("T0" in p for p in exc.value.problems)


def test_duplicate_priority_is_rejected():
    rules = default_rules()
    broken = [
        PolicyRuleView(r.id, r.code, r.tier, 10 if r.code == "T0_UNRESOLVED_CONFLICT" else r.priority, r.condition)
        for r in rules
    ]
    with pytest.raises(PolicyValidationError):
        validate_policy(broken)


def test_unknown_fact_is_rejected():
    rules = default_rules()
    broken = [
        PolicyRuleView(
            r.id,
            r.code,
            r.tier,
            r.priority,
            {"all": [{"fact": "model_score", "op": "gte", "value": 0.9}]} if r.code == "T3_FULL_DELTA" else r.condition,
        )
        for r in rules
    ]
    with pytest.raises(PolicyValidationError) as exc:
        validate_policy(broken)
    assert any("model_score" in p for p in exc.value.problems)


def test_policy_without_t0_is_rejected():
    rules = [r for r in default_rules() if r.tier is not Tier.T0]
    with pytest.raises(PolicyValidationError):
        validate_policy(rules)


def test_governor_forces_abstain_without_valid_citation():
    verdict = govern(
        tier=Tier.T3,
        rule_validation="simulasi",
        citation_valid_count=0,
        coverage_adequate=True,
        unresolved_conflict=False,
    )
    assert verdict.tier is Tier.T0
    assert verdict.overridden


def test_governor_caps_unvalidated_rule_at_t1():
    verdict = govern(
        tier=Tier.T2,
        rule_validation="belum_tervalidasi",
        citation_valid_count=2,
        coverage_adequate=True,
        unresolved_conflict=False,
    )
    assert verdict.tier is Tier.T1


def test_governor_leaves_compliant_decision_untouched():
    verdict = govern(
        tier=Tier.T3,
        rule_validation="simulasi",
        citation_valid_count=1,
        coverage_adequate=True,
        unresolved_conflict=False,
    )
    assert verdict.tier is Tier.T3
    assert not verdict.overridden
