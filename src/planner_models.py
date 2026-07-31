"""JSON-compatible data models for the deterministic daily planner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.alias_resolver import normalize_query


def _rating(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
        raise ValueError(f"{field_name} must be an integer from 1 to 5")
    return value


@dataclass(frozen=True)
class SubjectInput:
    """One subject supplied by the student."""

    name: str
    difficulty: int
    priority: int
    workload: int
    current_understanding: int
    topics: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SubjectInput":
        if not isinstance(values, dict):
            raise ValueError("each subject must be an object")
        name = values.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("subject name must be a non-empty string")
        raw_topics = values.get("topics", [])
        if raw_topics is None:
            raw_topics = []
        if not isinstance(raw_topics, (list, tuple)):
            raise ValueError("topics must be a list of non-empty strings")
        topics: list[str] = []
        seen: set[str] = set()
        for raw_topic in raw_topics:
            if not isinstance(raw_topic, str) or not raw_topic.strip():
                raise ValueError("topics must contain only non-empty strings")
            topic = raw_topic.strip()
            normalized = normalize_query(topic)
            if normalized in seen:
                raise ValueError(f"duplicate topic for {name.strip()}: {topic}")
            seen.add(normalized)
            topics.append(topic)
        return cls(
            name=name.strip(),
            difficulty=_rating(values.get("difficulty"), "difficulty"),
            priority=_rating(values.get("priority"), "priority"),
            workload=_rating(values.get("workload"), "workload"),
            current_understanding=_rating(values.get("current_understanding"), "current_understanding"),
            topics=tuple(topics),
        )


@dataclass(frozen=True)
class DailyPlanRequest:
    """Validated shape of one daily-planning request."""

    total_available_minutes: int
    subjects: tuple[SubjectInput, ...]
    preferred_start_time: str | None = None
    preferred_session_length: int | None = None

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "DailyPlanRequest":
        if not isinstance(values, dict):
            raise ValueError("planner input must be an object")
        total = values.get("total_available_minutes")
        if not isinstance(total, int) or isinstance(total, bool):
            raise ValueError("total_available_minutes must be an integer")
        raw_subjects = values.get("subjects")
        if not isinstance(raw_subjects, list) or not raw_subjects:
            raise ValueError("subjects must be a non-empty list")
        subjects = tuple(SubjectInput.from_dict(item) for item in raw_subjects)
        normalized_names = [normalize_query(item.name) for item in subjects]
        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("duplicate subject names are not allowed")
        start = values.get("preferred_start_time")
        if start is not None and (not isinstance(start, str) or not start.strip()):
            raise ValueError("preferred_start_time must be HH:MM or null")
        preferred_length = values.get("preferred_session_length")
        if preferred_length is not None and (
            not isinstance(preferred_length, int) or isinstance(preferred_length, bool)
        ):
            raise ValueError("preferred_session_length must be an integer or null")
        return cls(total, subjects, start.strip() if isinstance(start, str) else None, preferred_length)


@dataclass(frozen=True)
class PlannedSession:
    order: int
    session_type: str
    duration_minutes: int
    reason: str
    start_time: str | None = None
    subject: str | None = None
    topic: str | None = None
    cognitive_demand: str | None = None
    recommended_methods: tuple[str, ...] = ()
    retrieved_record_ids: tuple[str, ...] = ()
    used_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["recommended_methods"] = list(self.recommended_methods)
        values["retrieved_record_ids"] = list(self.retrieved_record_ids)
        return values


@dataclass(frozen=True)
class ScheduledSubject:
    subject: str
    canonical_subject: str | None
    score: float
    allocated_study_minutes: int
    session_count: int
    reason: str
    retrieved_record_ids: tuple[str, ...] = ()
    used_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["retrieved_record_ids"] = list(self.retrieved_record_ids)
        return values


@dataclass(frozen=True)
class UnscheduledSubject:
    subject: str
    score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyStudyPlan:
    plan_id: str
    total_available_minutes: int
    total_study_minutes: int
    total_break_minutes: int
    total_planned_minutes: int
    unallocated_minutes: int
    scheduled_subjects: tuple[ScheduledSubject, ...]
    unscheduled_subjects: tuple[UnscheduledSubject, ...]
    sessions: tuple[PlannedSession, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planner_version: str = "1.0.0-prototype"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "total_available_minutes": self.total_available_minutes,
            "total_study_minutes": self.total_study_minutes,
            "total_break_minutes": self.total_break_minutes,
            "total_planned_minutes": self.total_planned_minutes,
            "unallocated_minutes": self.unallocated_minutes,
            "scheduled_subjects": [item.to_dict() for item in self.scheduled_subjects],
            "unscheduled_subjects": [item.to_dict() for item in self.unscheduled_subjects],
            "sessions": [item.to_dict() for item in self.sessions],
            "warnings": list(self.warnings),
            "planner_version": self.planner_version,
        }
