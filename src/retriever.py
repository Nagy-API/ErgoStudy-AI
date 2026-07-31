"""Reusable production retrieval service over the persistent Chroma index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from src.alias_resolver import AliasResolver
from src.chroma_store import COLLECTION_NAME, close_client
from src.dataset_io import read_json, read_jsonl
from src.embedding_models import encode_texts, load_sentence_transformer
from src.metadata_projection import PROJECTION_FIELDS
from src.query_analyzer import QueryAnalyzer
from src.retrieval_models import QueryAnalysis, RetrievalConfiguration, RetrievalResult


DEFAULT_INTENT_BOOSTS = {
    "session_template": {"session_template": 0.03, "study_strategy": 0.01},
    "study_strategy": {"study_strategy": 0.025, "session_template": 0.01},
    "topic_lookup": {"topic_profile": 0.02},
    "alias_lookup": {"subject_alias": 0.0, "subject_profile": 0.0},
    "subject_lookup": {"subject_profile": 0.0, "subject_alias": 0.0},
}


def baseline_configuration() -> RetrievalConfiguration:
    return RetrievalConfiguration("baseline_dense", False, False, dense_candidate_count=10)


def alias_configuration() -> RetrievalConfiguration:
    return RetrievalConfiguration("alias_plus_dense", True, False, dense_candidate_count=40)


def intent_configuration() -> RetrievalConfiguration:
    return RetrievalConfiguration(
        "intent_aware_blend",
        True,
        True,
        dense_candidate_count=40,
        intent_family_boosts=DEFAULT_INTENT_BOOSTS,
    )


def cosine_distance_to_similarity(distance: float) -> float:
    """Convert Chroma cosine distance to cosine similarity: ``1 - distance``."""
    return 1.0 - float(distance)


def _where_clause(filters: Mapping[str, str | int | float | bool] | None) -> dict[str, Any] | None:
    if not filters:
        return None
    clauses: list[dict[str, Any]] = []
    for key, value in sorted(filters.items()):
        if key not in PROJECTION_FIELDS:
            raise ValueError(f"Unsupported metadata filter: {key}")
        if value is None or not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"Metadata filter {key!r} must be a non-null scalar")
        clauses.append({key: value})
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class RetrievalService:
    """Load the selected local model and retrieve structured Chroma results."""

    def __init__(
        self,
        project_root: Path,
        *,
        configuration: RetrievalConfiguration | None = None,
        model: Any | None = None,
        collection: Any | None = None,
        client: Any | None = None,
        records: list[dict[str, Any]] | None = None,
        device: str | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        processed = self.project_root / "data" / "processed"
        selected = read_json(processed / "selected_embedding_model.json")
        if selected["config_id"] != "minilm_plain":
            raise ValueError("Stage 5 requires the selected minilm_plain configuration")
        self.selected_model = selected
        self.configuration = configuration or intent_configuration()
        self.records = records or read_jsonl(processed / "knowledge_corpus.jsonl")
        self.records_by_id = {record["record_id"]: record for record in self.records}
        self.alias_resolver = AliasResolver(self.records)
        self.query_analyzer = QueryAnalyzer(self.alias_resolver)
        self._owns_client = collection is None

        if collection is None:
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.project_root / "chroma_db"))
            self.collection = self.client.get_collection(COLLECTION_NAME, embedding_function=None)
        else:
            self.client = client
            self.collection = collection
        self.model = model or load_sentence_transformer(
            selected["model_id"],
            device or selected.get("device", "cpu"),
            revision=selected["model_revision"],
            local_files_only=True,
        )

    @classmethod
    def from_frozen_config(cls, project_root: Path, **kwargs: Any) -> "RetrievalService":
        """Construct a service from the frozen Stage 5 JSON configuration."""
        raw = read_json(project_root / "data" / "processed" / "retrieval_config.json")
        if not raw.get("frozen"):
            raise ValueError("retrieval_config.json is not frozen")
        values = raw["retrieval_configuration"]
        configuration = RetrievalConfiguration(**values)
        return cls(project_root, configuration=configuration, **kwargs)

    def close(self) -> None:
        if self._owns_client and self.client is not None:
            close_client(self.client)

    def __enter__(self) -> "RetrievalService":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def analyze_query(self, query: str) -> QueryAnalysis:
        """Expose the deterministic analysis for diagnostics and explainability."""
        return self.query_analyzer.analyze(query)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 10,
        metadata_filters: Mapping[str, str | int | float | bool] | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve records using semantic search plus optional deterministic blending."""
        if not isinstance(query, str) or not query.strip():
            return []
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        analysis = self.query_analyzer.analyze(query)
        where = _where_clause(metadata_filters)
        formatted = f"{self.selected_model.get('query_prefix', '')}{query.strip()}"
        query_embedding = encode_texts(
            self.model,
            [formatted],
            batch_size=1,
            normalize_embeddings=bool(self.selected_model["normalize_embeddings"]),
        )[0]
        requested = max(top_k, self.configuration.dense_candidate_count if self.configuration.intent_routing_enabled else top_k)
        requested = min(requested, self.collection.count())
        result = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=requested,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        candidates: dict[str, dict[str, Any]] = {}
        for record_id, distance in zip(result["ids"][0], result["distances"][0], strict=True):
            candidates[record_id] = {
                "similarity": cosine_distance_to_similarity(distance),
                "ranking_score": cosine_distance_to_similarity(distance),
            }

        if self.configuration.alias_resolution_enabled:
            exact_ids = set(analysis.alias_resolution.resolved_subject_record_ids)
            exact_ids.update(analysis.alias_resolution.matched_alias_record_ids)
            self._add_exact_candidates(candidates, exact_ids, query_embedding, where)
            for match in analysis.alias_resolution.matches:
                if not match.resolved:
                    continue
                boost = (
                    self.configuration.exact_subject_boost
                    if match.match_kind == "subject_name"
                    else self.configuration.exact_alias_boost
                )
                for record_id in match.subject_record_ids:
                    if record_id in candidates:
                        candidates[record_id]["ranking_score"] += boost
                for record_id in match.alias_record_ids:
                    if record_id in candidates:
                        candidates[record_id]["ranking_score"] += self.configuration.exact_alias_boost

        if self.configuration.intent_routing_enabled:
            for record_id, values in candidates.items():
                family = self.records_by_id[record_id]["document_family"]
                family_boost = max(
                    (
                        self.configuration.intent_family_boosts.get(intent, {}).get(family, 0.0)
                        for intent in analysis.intents
                    ),
                    default=0.0,
                )
                values["ranking_score"] += family_boost

        ranked_ids = sorted(
            candidates,
            key=lambda record_id: (
                -candidates[record_id]["ranking_score"],
                -candidates[record_id]["similarity"],
                record_id,
            ),
        )[:top_k]
        return [self._public_result(record_id, candidates[record_id]["similarity"]) for record_id in ranked_ids]

    def _add_exact_candidates(
        self,
        candidates: dict[str, dict[str, Any]],
        record_ids: set[str],
        query_embedding: np.ndarray,
        where: dict[str, Any] | None,
    ) -> None:
        missing = sorted(record_id for record_id in record_ids if record_id not in candidates)
        if not missing:
            return
        stored = self.collection.get(ids=missing, where=where, include=["embeddings"])
        for record_id, embedding in zip(stored["ids"], stored["embeddings"], strict=True):
            similarity = float(np.dot(query_embedding, np.asarray(embedding, dtype=np.float32)))
            candidates[record_id] = {"similarity": similarity, "ranking_score": similarity}

    def _public_result(self, record_id: str, similarity: float) -> RetrievalResult:
        record = self.records_by_id[record_id]
        public_keys = {"record_id", "title", "retrieval_text", "document_family", "subject_family"}
        metadata = {key: value for key, value in record.items() if key not in public_keys}
        return RetrievalResult(
            record_id=record_id,
            title=str(record["title"]),
            retrieval_text=str(record["retrieval_text"]),
            document_family=str(record["document_family"]),
            subject_family=str(record.get("subject_family") or "not_applicable"),
            score=float(similarity),
            metadata=metadata,
        )
