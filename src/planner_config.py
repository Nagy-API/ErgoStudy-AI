"""Load and validate the versioned deterministic planner configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.planner_models import DailyPlanRequest


@dataclass(frozen=True)
class PlanningWeights:
    priority: float
    workload: float
    difficulty: float
    knowledge_gap: float


@dataclass(frozen=True)
class TimeRules:
    minimum_useful_session_minutes: int
    maximum_session_minutes: int
    default_session_minutes: int
    short_break_minutes: int
    normal_break_minutes: int
    minimum_total_available_minutes: int
    maximum_total_available_minutes: int


@dataclass(frozen=True)
class CognitiveDemandRules:
    high_score_threshold: float
    medium_score_threshold: float


@dataclass(frozen=True)
class RetrievalRules:
    subject_top_k: int
    topic_top_k: int
    strategy_top_k: int
    template_top_k: int
    minimum_similarity: float
    maximum_methods_per_session: int


@dataclass(frozen=True)
class PlannerConfig:
    planner_version: str
    planning_weights: PlanningWeights
    time_rules: TimeRules
    cognitive_demand: CognitiveDemandRules
    retrieval: RetrievalRules
    fallback_methods: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["fallback_methods"] = list(self.fallback_methods)
        return values

    def validate_request(self, request: DailyPlanRequest) -> None:
        rules = self.time_rules
        if not rules.minimum_total_available_minutes <= request.total_available_minutes <= rules.maximum_total_available_minutes:
            raise ValueError(
                "total_available_minutes must be between "
                f"{rules.minimum_total_available_minutes} and {rules.maximum_total_available_minutes}"
            )
        if request.preferred_session_length is not None and not (
            rules.minimum_useful_session_minutes
            <= request.preferred_session_length
            <= rules.maximum_session_minutes
        ):
            raise ValueError(
                "preferred_session_length must be between "
                f"{rules.minimum_useful_session_minutes} and {rules.maximum_session_minutes}"
            )
        if request.preferred_start_time is not None:
            try:
                datetime.strptime(request.preferred_start_time, "%H:%M")
            except ValueError as error:
                raise ValueError("preferred_start_time must use valid 24-hour HH:MM format") from error


def _positive_integer(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def load_planner_config(path: Path) -> PlannerConfig:
    """Read one JSON configuration and fail early on unsafe boundaries."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    weights = PlanningWeights(**raw["planning_weights"])
    if abs(sum(asdict(weights).values()) - 1.0) > 1e-9:
        raise ValueError("planning weights must sum to 1.0")
    if any(value < 0 for value in asdict(weights).values()):
        raise ValueError("planning weights cannot be negative")

    time_values = raw["time_rules"]
    for name, value in time_values.items():
        _positive_integer(value, name)
    time_rules = TimeRules(**time_values)
    if not (
        time_rules.minimum_useful_session_minutes
        <= time_rules.default_session_minutes
        <= time_rules.maximum_session_minutes
    ):
        raise ValueError("default session duration must be within the session bounds")
    if time_rules.short_break_minutes > time_rules.normal_break_minutes:
        raise ValueError("short break cannot exceed normal break")
    if time_rules.minimum_total_available_minutes < time_rules.minimum_useful_session_minutes:
        raise ValueError("minimum total time cannot be below the minimum useful session")

    demand = CognitiveDemandRules(**raw["cognitive_demand"])
    if demand.medium_score_threshold >= demand.high_score_threshold:
        raise ValueError("medium cognitive-demand threshold must be below the high threshold")
    retrieval = RetrievalRules(**raw["retrieval"])
    for name in ("subject_top_k", "topic_top_k", "strategy_top_k", "template_top_k", "maximum_methods_per_session"):
        _positive_integer(getattr(retrieval, name), name)
    if not -1.0 <= retrieval.minimum_similarity <= 1.0:
        raise ValueError("minimum_similarity must be between -1.0 and 1.0")
    fallback_methods = tuple(raw["fallback"]["recommended_methods"])
    if not fallback_methods or any(not isinstance(value, str) or not value.strip() for value in fallback_methods):
        raise ValueError("fallback recommended methods must be non-empty strings")
    return PlannerConfig(raw["planner_version"], weights, time_rules, demand, retrieval, fallback_methods)


def default_planner_config(project_root: Path) -> PlannerConfig:
    return load_planner_config(project_root / "config" / "planner_config.json")
