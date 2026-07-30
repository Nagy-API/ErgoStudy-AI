"""Typed data models for deterministic ErgoStudy retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AliasMatch:
    """One normalized subject-name or controlled-alias match."""

    matched_text: str
    match_kind: str
    subject_record_ids: tuple[str, ...]
    alias_record_ids: tuple[str, ...] = ()
    ambiguous: bool = False
    resolved: bool = True


@dataclass(frozen=True)
class AliasResolution:
    """All exact controlled-name matches found in a plain-English query."""

    normalized_query: str
    matches: tuple[AliasMatch, ...] = ()

    @property
    def resolved_subject_record_ids(self) -> tuple[str, ...]:
        values = {
            record_id
            for match in self.matches
            if match.resolved
            for record_id in match.subject_record_ids
        }
        return tuple(sorted(values))

    @property
    def matched_alias_record_ids(self) -> tuple[str, ...]:
        values = {record_id for match in self.matches for record_id in match.alias_record_ids}
        return tuple(sorted(values))

    @property
    def has_ambiguity(self) -> bool:
        return any(match.ambiguous and not match.resolved for match in self.matches)


@dataclass(frozen=True)
class QueryAnalysis:
    """Non-oracle signals derived only from the submitted query and alias catalog."""

    normalized_query: str
    primary_intent: str
    intents: tuple[str, ...]
    suggested_document_families: tuple[str, ...]
    alias_resolution: AliasResolution


@dataclass(frozen=True)
class RetrievalResult:
    """Stable public result schema returned by :class:`RetrievalService`.

    ``score`` is cosine similarity, calculated as ``1 - Chroma cosine
    distance``. Deterministic intent and exact-name adjustments affect ordering
    but never change this reported semantic score.
    """

    record_id: str
    title: str
    retrieval_text: str
    document_family: str
    subject_family: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation with stable field names."""
        return asdict(self)


@dataclass(frozen=True)
class RetrievalConfiguration:
    """Frozen deterministic routing and blending settings."""

    config_id: str
    alias_resolution_enabled: bool
    intent_routing_enabled: bool
    dense_candidate_count: int = 40
    exact_subject_boost: float = 0.25
    exact_alias_boost: float = 0.25
    intent_family_boosts: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready configuration."""
        return asdict(self)
