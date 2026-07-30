"""Explainable subject scoring for the deterministic planner."""

from __future__ import annotations

from dataclasses import dataclass

from src.planner_config import PlannerConfig
from src.planner_models import SubjectInput


@dataclass(frozen=True)
class SubjectScore:
    subject: SubjectInput
    score: float
    knowledge_gap: int
    cognitive_demand: str
    reason: str


def score_subject(subject: SubjectInput, config: PlannerConfig) -> SubjectScore:
    """Calculate the configured weighted score on the shared 1-to-5 scale."""
    gap = 6 - subject.current_understanding
    weights = config.planning_weights
    score = (
        weights.priority * subject.priority
        + weights.workload * subject.workload
        + weights.difficulty * subject.difficulty
        + weights.knowledge_gap * gap
    )
    if score >= config.cognitive_demand.high_score_threshold:
        demand = "high"
    elif score >= config.cognitive_demand.medium_score_threshold:
        demand = "medium"
    else:
        demand = "low"

    factors: list[str] = []
    if subject.priority >= 4:
        factors.append("high priority")
    if subject.workload >= 4:
        factors.append("high workload")
    if subject.difficulty >= 4:
        factors.append("high difficulty")
    if gap >= 4:
        factors.append("a large knowledge gap")
    if not factors:
        factors.append("its combined priority, workload, difficulty, and knowledge gap")
    if len(factors) == 1:
        reason = f"Scheduled based on {factors[0]}."
    else:
        reason = "Scheduled because of " + ", ".join(factors[:-1]) + f", and {factors[-1]}."
    return SubjectScore(subject, round(score, 4), gap, demand, reason)


def score_subjects(subjects: tuple[SubjectInput, ...], config: PlannerConfig) -> tuple[SubjectScore, ...]:
    return tuple(score_subject(subject, config) for subject in subjects)
