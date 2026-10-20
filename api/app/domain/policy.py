import uuid
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.domain.enums import Tier

KNOWN_FACTS: frozenset[str] = frozenset(
    {
        "vector_code",
        "check_type",
        "rule_validation",
        "delta_present",
        "coverage_adequate",
        "unresolved_conflict",
        "has_contradiction",
        "only_out_of_window_matches",
        "missing_ratio",
        "citation_valid_count",
        "citation_invalid_count",
    }
)

Operator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in"]


class Predicate(BaseModel):
    fact: str
    op: Operator
    value: Any


class Condition(BaseModel):
    all: list[Predicate] = Field(default_factory=list)
    any: list[Predicate] = Field(default_factory=list)

    def is_catch_all(self) -> bool:
        return not self.all and not self.any


@dataclass(frozen=True)
class PolicyRuleView:
    id: uuid.UUID
    code: str
    tier: Tier
    priority: int
    condition: dict[str, Any]
    is_active: bool = True


@dataclass(frozen=True)
class PolicyDecision:
    tier: Tier
    rule_id: uuid.UUID
    rule_code: str
    priority: int


class PolicyValidationError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def _compare(actual: Any, op: Operator, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "in":
        return actual in expected
    if actual is None:
        return False
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    return actual <= expected


def _predicate_holds(predicate: Predicate, facts: dict[str, Any]) -> bool:
    if predicate.fact not in facts:
        return False
    return _compare(facts[predicate.fact], predicate.op, predicate.value)


def condition_matches(condition: Condition, facts: dict[str, Any]) -> bool:
    if condition.is_catch_all():
        return True
    if condition.all and not all(_predicate_holds(p, facts) for p in condition.all):
        return False
    if condition.any and not any(_predicate_holds(p, facts) for p in condition.any):
        return False
    return True


def parse_condition(spec: dict[str, Any]) -> Condition:
    return Condition.model_validate(spec)


def decide(rules: list[PolicyRuleView], facts: dict[str, Any]) -> PolicyDecision:
    ordered = sorted((r for r in rules if r.is_active), key=lambda r: r.priority)
    for rule in ordered:
        if condition_matches(parse_condition(rule.condition), facts):
            return PolicyDecision(rule.tier, rule.id, rule.code, rule.priority)
    raise PolicyValidationError(["tidak ada aturan kebijakan yang cocok dan tidak ada aturan penampung"])


def validate_policy(rules: list[PolicyRuleView]) -> None:
    problems: list[str] = []
    active = [r for r in rules if r.is_active]
    if not active:
        problems.append("kebijakan harus punya minimal satu aturan aktif")
        raise PolicyValidationError(problems)

    priorities = [r.priority for r in active]
    if len(priorities) != len(set(priorities)):
        problems.append("prioritas aturan harus unik")

    parsed: dict[uuid.UUID, Condition] = {}
    for rule in active:
        try:
            condition = parse_condition(rule.condition)
        except ValidationError as exc:
            problems.append(f"aturan {rule.code}: kondisi tidak valid ({exc.error_count()} galat)")
            continue
        parsed[rule.id] = condition
        for predicate in [*condition.all, *condition.any]:
            if predicate.fact not in KNOWN_FACTS:
                problems.append(f"aturan {rule.code}: fakta '{predicate.fact}' tidak dikenal")

    t0 = [r for r in active if r.tier is Tier.T0]
    others = [r for r in active if r.tier is not Tier.T0]
    if not t0:
        problems.append("kebijakan wajib punya aturan T0 (abstain)")
    if t0 and others and max(r.priority for r in t0) >= min(r.priority for r in others):
        problems.append("semua aturan T0 harus diprioritaskan sebelum aturan T1-T3")

    ordered = sorted(active, key=lambda r: r.priority)
    last = ordered[-1]
    last_condition = parsed.get(last.id)
    if last_condition is None or not last_condition.is_catch_all():
        problems.append("aturan dengan prioritas terakhir harus berupa aturan penampung tanpa kondisi")
    elif last.tier is Tier.T0:
        problems.append("aturan penampung tidak boleh T0")

    if problems:
        raise PolicyValidationError(problems)
