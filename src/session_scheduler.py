"""Order bounded study blocks and deterministic recovery breaks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.alias_resolver import normalize_query
from src.knowledge_adapter import SubjectKnowledge
from src.planner_config import PlannerConfig
from src.planner_models import PlannedSession
from src.time_allocator import SubjectAllocation


@dataclass(frozen=True)
class ScheduledTimeline:
    sessions: tuple[PlannedSession, ...]
    total_study_minutes: int
    total_break_minutes: int


def _clock(value: datetime | None) -> str | None:
    return value.strftime("%H:%M") if value is not None else None


def _parse_start(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%H:%M")
    except ValueError as error:
        raise ValueError("preferred_start_time must use valid 24-hour HH:MM format") from error


def schedule_sessions(
    allocations: tuple[SubjectAllocation, ...],
    knowledge_by_subject: dict[str, SubjectKnowledge],
    preferred_start_time: str | None,
    config: PlannerConfig,
) -> ScheduledTimeline:
    """Interleave subjects, avoiding adjacent high-demand blocks when possible."""
    current_time = _parse_start(preferred_start_time)
    queues: dict[str, list[tuple[int, int]]] = {
        item.scored_subject.subject.name: list(enumerate(item.session_durations)) for item in allocations
    }
    by_name = {item.scored_subject.subject.name: item for item in allocations}
    ordered_study: list[tuple[SubjectAllocation, int, int]] = []
    previous_demand: str | None = None
    previous_subject: str | None = None
    while any(queues.values()):
        candidate_names = [name for name, queue in queues.items() if queue]
        if previous_demand == "high":
            lower_demand = [
                name for name in candidate_names if by_name[name].scored_subject.cognitive_demand != "high"
            ]
            if lower_demand:
                candidate_names = lower_demand
        other_subjects = [name for name in candidate_names if name != previous_subject]
        if other_subjects:
            candidate_names = other_subjects
        candidate_names.sort(
            key=lambda name: (-by_name[name].scored_subject.score, normalize_query(name))
        )
        name = candidate_names[0]
        chunk_index, duration = queues[name].pop(0)
        allocation = by_name[name]
        ordered_study.append((allocation, chunk_index, duration))
        previous_subject = name
        previous_demand = allocation.scored_subject.cognitive_demand

    sessions: list[PlannedSession] = []
    total_break = 0
    for study_index, (allocation, chunk_index, duration) in enumerate(ordered_study):
        scored = allocation.scored_subject
        subject = scored.subject
        knowledge = knowledge_by_subject[subject.name]
        topic = subject.topics[chunk_index % len(subject.topics)] if subject.topics else None
        topic_ids = dict(knowledge.topic_record_ids)
        record_ids = list(knowledge.retrieved_record_ids)
        if topic and topic in topic_ids and topic_ids[topic] not in record_ids:
            record_ids.append(topic_ids[topic])
        sessions.append(
            PlannedSession(
                order=len(sessions) + 1,
                session_type="study",
                duration_minutes=duration,
                reason=scored.reason,
                start_time=_clock(current_time),
                subject=subject.name,
                topic=topic,
                cognitive_demand=scored.cognitive_demand,
                recommended_methods=knowledge.recommended_methods,
                retrieved_record_ids=tuple(record_ids),
                used_fallback=knowledge.used_fallback,
            )
        )
        if current_time is not None:
            current_time += timedelta(minutes=duration)
        if study_index == len(ordered_study) - 1:
            continue
        break_duration = (
            config.time_rules.normal_break_minutes
            if scored.cognitive_demand == "high"
            else config.time_rules.short_break_minutes
        )
        sessions.append(
            PlannedSession(
                order=len(sessions) + 1,
                session_type="break",
                duration_minutes=break_duration,
                reason="Scheduled recovery break after a demanding session."
                if scored.cognitive_demand == "high"
                else "Scheduled short recovery break.",
                start_time=_clock(current_time),
            )
        )
        total_break += break_duration
        if current_time is not None:
            current_time += timedelta(minutes=break_duration)
    return ScheduledTimeline(
        sessions=tuple(sessions),
        total_study_minutes=sum(item[2] for item in ordered_study),
        total_break_minutes=total_break,
    )
