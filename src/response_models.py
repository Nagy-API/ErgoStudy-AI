"""Strict JSON-compatible models for grounded response generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


RESPONSE_FIELDS = frozenset(
    {
        "summary",
        "allocation_explanations",
        "session_messages",
        "unscheduled_message",
        "warnings",
    }
)
GENERATION_MODES = frozenset(
    {"local_llm", "local_llm_corrected", "deterministic_fallback"}
)


def _exact_fields(values: dict[str, Any], expected: frozenset[str], label: str) -> None:
    if not isinstance(values, dict):
        raise ValueError(f"{label} must be an object")
    missing = expected - values.keys()
    extra = values.keys() - expected
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{label} has extra fields: {', '.join(sorted(extra))}")


def _non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class AllocationExplanation:
    subject: str
    allocated_minutes: int
    reason: str

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "AllocationExplanation":
        expected = frozenset({"subject", "allocated_minutes", "reason"})
        _exact_fields(values, expected, "allocation explanation")
        minutes = values["allocated_minutes"]
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValueError("allocated_minutes must be a positive integer")
        return cls(
            subject=_non_empty_string(values["subject"], "subject"),
            allocated_minutes=minutes,
            reason=_non_empty_string(values["reason"], "reason"),
        )


@dataclass(frozen=True)
class SessionMessage:
    session_order: int
    message: str

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SessionMessage":
        expected = frozenset({"session_order", "message"})
        _exact_fields(values, expected, "session message")
        order = values["session_order"]
        if not isinstance(order, int) or isinstance(order, bool) or order <= 0:
            raise ValueError("session_order must be a positive integer")
        return cls(order, _non_empty_string(values["message"], "message"))


@dataclass(frozen=True)
class GroundedResponse:
    summary: str
    allocation_explanations: tuple[AllocationExplanation, ...]
    session_messages: tuple[SessionMessage, ...]
    unscheduled_message: str | None
    warnings: tuple[str, ...]

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "GroundedResponse":
        _exact_fields(values, RESPONSE_FIELDS, "grounded response")
        allocations = values["allocation_explanations"]
        sessions = values["session_messages"]
        warnings = values["warnings"]
        if not isinstance(allocations, list):
            raise ValueError("allocation_explanations must be a list")
        if not isinstance(sessions, list):
            raise ValueError("session_messages must be a list")
        if not isinstance(warnings, list) or not all(
            isinstance(item, str) and item.strip() for item in warnings
        ):
            raise ValueError("warnings must be a list of non-empty strings")
        unscheduled = values["unscheduled_message"]
        if unscheduled is not None and (
            not isinstance(unscheduled, str) or not unscheduled.strip()
        ):
            raise ValueError("unscheduled_message must be a non-empty string or null")
        return cls(
            summary=_non_empty_string(values["summary"], "summary"),
            allocation_explanations=tuple(
                AllocationExplanation.from_dict(item) for item in allocations
            ),
            session_messages=tuple(SessionMessage.from_dict(item) for item in sessions),
            unscheduled_message=(
                unscheduled.strip() if isinstance(unscheduled, str) else None
            ),
            warnings=tuple(item.strip() for item in warnings),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "allocation_explanations": [asdict(item) for item in self.allocation_explanations],
            "session_messages": [asdict(item) for item in self.session_messages],
            "unscheduled_message": self.unscheduled_message,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class GenerationResult:
    response: GroundedResponse
    generation_mode: str
    attempt_count: int
    latency_seconds: float
    validation_errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.generation_mode not in GENERATION_MODES:
            raise ValueError(f"unsupported generation_mode: {self.generation_mode}")
        if self.attempt_count not in {0, 1, 2}:
            raise ValueError("attempt_count must be 0, 1, or 2")
        if self.latency_seconds < 0:
            raise ValueError("latency_seconds must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_mode": self.generation_mode,
            "attempt_count": self.attempt_count,
            "latency_seconds": round(self.latency_seconds, 4),
            "validation_errors": list(self.validation_errors),
            "response": self.response.to_dict(),
        }


OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(RESPONSE_FIELDS),
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "allocation_explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["subject", "allocated_minutes", "reason"],
                "properties": {
                    "subject": {"type": "string", "minLength": 1},
                    "allocated_minutes": {"type": "integer", "minimum": 1},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
        },
        "session_messages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["session_order", "message"],
                "properties": {
                    "session_order": {"type": "integer", "minimum": 1},
                    "message": {"type": "string", "minLength": 1},
                },
            },
        },
        "unscheduled_message": {"type": ["string", "null"]},
        "warnings": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}
