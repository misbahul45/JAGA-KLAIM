from typing import Any

from app.domain.enums import Tier

POLICY_VERSION_LABEL = "policy-sim-1.0"

POLICY_CONFIG: dict[str, Any] = {
    "evaluation": "first_match_by_priority",
    "abstain_precedes_risk": True,
    "unvalidated_rule_cap": Tier.T1.value,
    "label": "Kebijakan simulasi T0-T3, belum divalidasi pakar",
}

DEFAULT_POLICY_RULES: list[dict[str, Any]] = [
    {
        "code": "T0_COVERAGE_INADEQUATE",
        "tier": Tier.T0,
        "priority": 10,
        "condition": {"all": [{"fact": "coverage_adequate", "op": "eq", "value": False}]},
    },
    {
        "code": "T0_UNRESOLVED_CONFLICT",
        "tier": Tier.T0,
        "priority": 20,
        "condition": {"all": [{"fact": "unresolved_conflict", "op": "eq", "value": True}]},
    },
    {
        "code": "T0_CITATION_UNVERIFIED",
        "tier": Tier.T0,
        "priority": 30,
        "condition": {
            "all": [
                {"fact": "delta_present", "op": "eq", "value": True},
                {"fact": "citation_valid_count", "op": "lt", "value": 1},
            ]
        },
    },
    {
        "code": "T1_UNVALIDATED_RULE_CAP",
        "tier": Tier.T1,
        "priority": 40,
        "condition": {
            "all": [
                {"fact": "delta_present", "op": "eq", "value": True},
                {"fact": "rule_validation", "op": "eq", "value": "belum_tervalidasi"},
            ]
        },
    },
    {
        "code": "T1_OUT_OF_EPISODE_WINDOW",
        "tier": Tier.T1,
        "priority": 50,
        "condition": {"all": [{"fact": "only_out_of_window_matches", "op": "eq", "value": True}]},
    },
    {
        "code": "T3_FULL_DELTA",
        "tier": Tier.T3,
        "priority": 60,
        "condition": {
            "all": [
                {"fact": "delta_present", "op": "eq", "value": True},
                {"fact": "missing_ratio", "op": "gte", "value": 1.0},
                {"fact": "citation_valid_count", "op": "gte", "value": 1},
            ]
        },
    },
    {
        "code": "T2_PARTIAL_DELTA",
        "tier": Tier.T2,
        "priority": 70,
        "condition": {
            "all": [
                {"fact": "delta_present", "op": "eq", "value": True},
                {"fact": "missing_ratio", "op": "gte", "value": 0.5},
            ]
        },
    },
    {
        "code": "T1_MINOR_DELTA",
        "tier": Tier.T1,
        "priority": 90,
        "condition": {},
    },
]
