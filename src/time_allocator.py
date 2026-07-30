"""Deterministic proportional allocation with meaningful-session bounds."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.alias_resolver import normalize_query
from src.planner_config import PlannerConfig
from src.subject_scoring import SubjectScore


@dataclass(frozen=True)
class SubjectAllocation:
    scored_subject: SubjectScore
    study_minutes: int
    session_durations: tuple[int, ...]


def rank_subjects(scored_subjects: tuple[SubjectScore, ...]) -> tuple[SubjectScore, ...]:
    return tuple(sorted(scored_subjects, key=lambda item: (-item.score, normalize_query(item.subject.name))))


def select_schedulable_subjects(
    scored_subjects: tuple[SubjectScore, ...], total_available_minutes: int, config: PlannerConfig
) -> tuple[tuple[SubjectScore, ...], tuple[SubjectScore, ...]]:
    """Select the highest scores that can each receive one useful session.

    Normal breaks are reserved between minimum sessions so selection remains
    safe even when every selected subject has high cognitive demand.
    """
    ranked = rank_subjects(scored_subjects)
    minimum = config.time_rules.minimum_useful_session_minutes
    break_minutes = config.time_rules.normal_break_minutes
    count = 0
    for candidate_count in range(1, len(ranked) + 1):
        required = candidate_count * minimum + (candidate_count - 1) * break_minutes
        if required <= total_available_minutes:
            count = candidate_count
        else:
            break
    return ranked[:count], ranked[count:]


def split_session_minutes(total_minutes: int, preferred_minutes: int, config: PlannerConfig) -> tuple[int, ...]:
    """Split a subject allocation into balanced, bounded sessions."""
    minimum = config.time_rules.minimum_useful_session_minutes
    maximum = config.time_rules.maximum_session_minutes
    if total_minutes < minimum:
        raise ValueError("a subject allocation cannot be below the minimum useful session")
    smallest_count = math.ceil(total_minutes / maximum)
    largest_count = total_minutes // minimum
    counts = range(smallest_count, largest_count + 1)
    count = min(counts, key=lambda value: (abs(total_minutes / value - preferred_minutes), value))
    base, remainder = divmod(total_minutes, count)
    durations = tuple(base + (1 if index < remainder else 0) for index in range(count))
    if any(value < minimum or value > maximum for value in durations):
        raise AssertionError("session splitting violated configured bounds")
    return durations


def allocate_study_minutes(
    selected: tuple[SubjectScore, ...],
    study_budget: int,
    preferred_session_minutes: int,
    config: PlannerConfig,
) -> tuple[SubjectAllocation, ...]:
    """Give every selected subject a minimum, then distribute by score."""
    if not selected:
        return ()
    minimum = config.time_rules.minimum_useful_session_minutes
    base_total = len(selected) * minimum
    if study_budget < base_total:
        raise ValueError("study budget is too small for the selected subjects")
    remaining = study_budget - base_total
    score_total = sum(item.score for item in selected)
    exact_extras = [remaining * item.score / score_total for item in selected]
    extras = [math.floor(value) for value in exact_extras]
    leftover = remaining - sum(extras)
    remainder_order = sorted(
        range(len(selected)),
        key=lambda index: (-(exact_extras[index] - extras[index]), normalize_query(selected[index].subject.name)),
    )
    for index in remainder_order[:leftover]:
        extras[index] += 1
    allocations = []
    for item, extra in zip(selected, extras, strict=True):
        minutes = minimum + extra
        allocations.append(
            SubjectAllocation(item, minutes, split_session_minutes(minutes, preferred_session_minutes, config))
        )
    return tuple(allocations)
