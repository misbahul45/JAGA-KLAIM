import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import StepStatus

ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "load_claim_context",
        "check_source_coverage",
        "search_claim_evidence",
        "compare_expected_observed",
        "template_synthesizer",
        "validate_citations",
        "policy_engine",
        "safety_governor",
    }
)

ERROR_MESSAGE_LIMIT = 200


class ToolNotAllowed(Exception):
    def __init__(self, tool_name: str) -> None:
        super().__init__(f"tool '{tool_name}' tidak ada dalam allowlist")
        self.tool_name = tool_name


@dataclass
class StepRecord:
    seq: int
    step_type: str
    tool_name: str
    query: str | None
    source_id: uuid.UUID | None
    status: StepStatus
    result_ref: dict[str, Any] | None
    latency_ms: int
    error_message: str | None


@dataclass
class StepRecorder:
    allowed: frozenset[str] = ALLOWED_TOOLS
    steps: list[StepRecord] = field(default_factory=list)

    def _append(
        self,
        step_type: str,
        tool_name: str,
        query: str | None,
        source_id: uuid.UUID | None,
        status: StepStatus,
        result_ref: dict[str, Any] | None,
        started: float,
        error: str | None,
    ) -> None:
        self.steps.append(
            StepRecord(
                seq=len(self.steps) + 1,
                step_type=step_type,
                tool_name=tool_name,
                query=query,
                source_id=source_id,
                status=status,
                result_ref=result_ref,
                latency_ms=int((time.perf_counter() - started) * 1000),
                error_message=error,
            )
        )

    def run[T](
        self,
        step_type: str,
        tool_name: str,
        fn: Callable[[], T],
        *,
        summarize: Callable[[T], dict[str, Any]] | None = None,
        query: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> T:
        started = time.perf_counter()
        if tool_name not in self.allowed:
            self._append(
                step_type, tool_name, query, source_id, StepStatus.BLOCKED, None, started,
                "tool tidak ada dalam allowlist",
            )
            raise ToolNotAllowed(tool_name)
        try:
            result = fn()
        except Exception as exc:
            self._append(
                step_type, tool_name, query, source_id, StepStatus.FAILED, None, started,
                str(exc)[:ERROR_MESSAGE_LIMIT],
            )
            raise
        self._append(
            step_type, tool_name, query, source_id, StepStatus.OK,
            summarize(result) if summarize else None, started, None,
        )
        return result
