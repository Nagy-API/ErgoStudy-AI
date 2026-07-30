"""Deterministic, non-oracle query intent analysis."""

from __future__ import annotations

from src.alias_resolver import AliasResolver, normalize_query
from src.retrieval_models import QueryAnalysis


_SENSOR_TERMS = {
    "imbalance", "leaning", "posture", "pressure", "sensor", "sitting", "slouch", "slouching", "standing"
}
_SAFETY_TERMS = {"dizzy", "dizziness", "faint", "numb", "numbness", "pain", "severe", "symptom"}
_SESSION_TERMS = {"block", "break", "minutes", "routine", "schedule", "session", "template", "timer"}
_STRATEGY_TERMS = {
    "annotate", "annotation", "concept map", "explain", "flashcard", "flashcards", "interleave", "method",
    "practice", "questions", "reread", "remember", "recall", "self test", "strategy", "testing myself",
    "worked example", "worked examples",
}
_TOPIC_TERMS = {"chapter", "equation", "equations", "lab", "problem", "problems", "topic", "vocabulary"}


def _contains_any(normalized: str, terms: set[str]) -> bool:
    padded = f" {normalized} "
    return any(f" {term} " in padded for term in terms)


class QueryAnalyzer:
    """Infer broad retrieval intent from query meaning and controlled names."""

    def __init__(self, alias_resolver: AliasResolver) -> None:
        self.alias_resolver = alias_resolver

    def analyze(self, query: str) -> QueryAnalysis:
        normalized = normalize_query(query)
        resolution = self.alias_resolver.resolve(query)
        if not normalized:
            return QueryAnalysis("", "invalid", (), (), resolution)

        intents: list[str] = []
        if _contains_any(normalized, _SENSOR_TERMS | _SAFETY_TERMS):
            intents.append("sensor_or_posture")
        if _contains_any(normalized, _SESSION_TERMS):
            intents.append("session_template")
        if _contains_any(normalized, _STRATEGY_TERMS) or normalized.startswith(("how should i study", "how do i study")):
            intents.append("study_strategy")
        if _contains_any(normalized, _TOPIC_TERMS):
            intents.append("topic_lookup")
        if resolution.matches:
            if any(match.match_kind == "alias" for match in resolution.matches):
                intents.append("alias_lookup")
            if resolution.resolved_subject_record_ids:
                intents.append("subject_lookup")
        if not intents:
            intents.append("semantic_lookup")

        priority = (
            "sensor_or_posture", "session_template", "study_strategy", "alias_lookup", "subject_lookup",
            "topic_lookup", "semantic_lookup",
        )
        ordered = tuple(name for name in priority if name in intents)
        families_by_intent = {
            "sensor_or_posture": ("sensor_intervention",),
            "session_template": ("session_template", "study_strategy"),
            "study_strategy": ("study_strategy", "session_template"),
            "alias_lookup": ("subject_alias", "subject_profile"),
            "subject_lookup": ("subject_profile", "subject_alias"),
            "topic_lookup": ("topic_profile",),
        }
        families: list[str] = []
        for intent in ordered:
            for family in families_by_intent.get(intent, ()):
                if family not in families:
                    families.append(family)
        return QueryAnalysis(normalized, ordered[0], ordered, tuple(families), resolution)
