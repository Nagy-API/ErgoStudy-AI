"""Orchestrator for deterministic, non-sensor, one-day study plans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.alias_resolver import normalize_query
from src.knowledge_adapter import KnowledgeAdapter, SubjectKnowledge
from src.planner_config import PlannerConfig, default_planner_config
from src.planner_models import (
    DailyPlanRequest,
    DailyStudyPlan,
    ScheduledSubject,
    UnscheduledSubject,
)
from src.session_scheduler import ScheduledTimeline, schedule_sessions
from src.subject_scoring import score_subjects
from src.time_allocator import SubjectAllocation, allocate_study_minutes, select_schedulable_subjects


def _normalized_request(request: DailyPlanRequest) -> dict[str, Any]:
    subjects = [
        {
            "name": normalize_query(item.name),
            "topics": [normalize_query(topic) for topic in item.topics],
            "difficulty": item.difficulty,
            "priority": item.priority,
            "workload": item.workload,
            "current_understanding": item.current_understanding,
        }
        for item in request.subjects
    ]
    subjects.sort(key=lambda item: item["name"])
    return {
        "total_available_minutes": request.total_available_minutes,
        "preferred_start_time": request.preferred_start_time,
        "preferred_session_length": request.preferred_session_length,
        "subjects": subjects,
    }


def deterministic_plan_id(request: DailyPlanRequest, config: PlannerConfig) -> str:
    payload = {"request": _normalized_request(request), "configuration": config.to_dict()}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "plan-" + hashlib.sha256(encoded).hexdigest()[:16]


class DailyPlanner:
    """Build an explainable plan without an LLM or sensor input."""

    def __init__(
        self,
        project_root: Path,
        *,
        retrieval_service: Any | None = None,
        config: PlannerConfig | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.config = config or default_planner_config(self.project_root)
        self.knowledge_adapter = KnowledgeAdapter(retrieval_service, self.config)

    def plan(self, values: dict[str, Any] | DailyPlanRequest) -> DailyStudyPlan:
        request = values if isinstance(values, DailyPlanRequest) else DailyPlanRequest.from_dict(values)
        self.config.validate_request(request)
        scored = score_subjects(request.subjects, self.config)
        knowledge: dict[str, SubjectKnowledge] = {
            subject.name: self.knowledge_adapter.retrieve(subject) for subject in request.subjects
        }
        selected, omitted = select_schedulable_subjects(
            scored, request.total_available_minutes, self.config
        )
        preferred = request.preferred_session_length or self.config.time_rules.default_session_minutes
        timeline, allocations = self._fit_timeline(
            selected,
            request.total_available_minutes,
            preferred,
            request.preferred_start_time,
            knowledge,
        )
        scheduled = tuple(
            ScheduledSubject(
                subject=item.scored_subject.subject.name,
                canonical_subject=knowledge[item.scored_subject.subject.name].canonical_subject,
                score=item.scored_subject.score,
                allocated_study_minutes=item.study_minutes,
                session_count=len(item.session_durations),
                reason=item.scored_subject.reason,
                retrieved_record_ids=knowledge[item.scored_subject.subject.name].retrieved_record_ids,
                used_fallback=knowledge[item.scored_subject.subject.name].used_fallback,
            )
            for item in allocations
        )
        unscheduled = tuple(
            UnscheduledSubject(
                subject=item.subject.name,
                score=item.score,
                reason=(
                    "Not scheduled because the remaining time cannot fit the configured "
                    "minimum useful study session and required break reserve."
                ),
            )
            for item in omitted
        )
        total_planned = timeline.total_study_minutes + timeline.total_break_minutes
        warnings = sorted(warning for item in knowledge.values() for warning in item.warnings)
        if omitted:
            warnings.append("Some subjects were left unscheduled because meaningful sessions would not fit.")
        unallocated = request.total_available_minutes - total_planned
        if unallocated:
            warnings.append(
                f"{unallocated} available minute{'s were' if unallocated != 1 else ' was'} left unallocated "
                "because adding them would change the bounded session structure."
            )
        return DailyStudyPlan(
            plan_id=deterministic_plan_id(request, self.config),
            total_available_minutes=request.total_available_minutes,
            total_study_minutes=timeline.total_study_minutes,
            total_break_minutes=timeline.total_break_minutes,
            total_planned_minutes=total_planned,
            unallocated_minutes=unallocated,
            scheduled_subjects=scheduled,
            unscheduled_subjects=unscheduled,
            sessions=timeline.sessions,
            warnings=tuple(dict.fromkeys(warnings)),
            planner_version=self.config.planner_version,
        )

    def _fit_timeline(
        self,
        selected: tuple,
        total_available: int,
        preferred: int,
        start_time: str | None,
        knowledge: dict[str, SubjectKnowledge],
    ) -> tuple[ScheduledTimeline, tuple]:
        if not selected:
            return ScheduledTimeline((), 0, 0), ()
        minimum_total = len(selected) * self.config.time_rules.minimum_useful_session_minutes
        study_budget = total_available
        seen_budgets: set[int] = set()
        best: tuple[ScheduledTimeline, tuple] | None = None
        for _ in range(30):
            if study_budget in seen_budgets:
                break
            seen_budgets.add(study_budget)
            allocations = allocate_study_minutes(selected, study_budget, preferred, self.config)
            timeline = schedule_sessions(allocations, knowledge, start_time, self.config)
            if timeline.total_study_minutes + timeline.total_break_minutes <= total_available:
                best = (timeline, allocations)
            adjusted = total_available - timeline.total_break_minutes
            if adjusted == study_budget:
                return timeline, allocations
            study_budget = max(minimum_total, adjusted)
        if best is None:
            raise AssertionError("planner could not fit selected subjects within available time")
        return self._fill_remaining_time(best, total_available, start_time, knowledge)

    def _fill_remaining_time(
        self,
        fitted: tuple[ScheduledTimeline, tuple[SubjectAllocation, ...]],
        total_available: int,
        start_time: str | None,
        knowledge: dict[str, SubjectKnowledge],
    ) -> tuple[ScheduledTimeline, tuple[SubjectAllocation, ...]]:
        """Use harmless slack without adding another session or break."""
        timeline, allocations = fitted
        remaining = total_available - timeline.total_study_minutes - timeline.total_break_minutes
        if remaining <= 0:
            return fitted
        maximum = self.config.time_rules.maximum_session_minutes
        expanded: list[SubjectAllocation] = []
        for item in allocations:
            capacity = len(item.session_durations) * maximum - item.study_minutes
            added = min(remaining, capacity)
            new_total = item.study_minutes + added
            count = len(item.session_durations)
            base, remainder = divmod(new_total, count)
            durations = tuple(base + (1 if index < remainder else 0) for index in range(count))
            expanded.append(SubjectAllocation(item.scored_subject, new_total, durations))
            remaining -= added
        result = tuple(expanded)
        updated = schedule_sessions(result, knowledge, start_time, self.config)
        if updated.total_study_minutes + updated.total_break_minutes > total_available:
            raise AssertionError("slack filling exceeded available time")
        return updated, result
