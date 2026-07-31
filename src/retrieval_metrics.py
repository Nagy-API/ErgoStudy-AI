"""Deterministic retrieval metrics and development/test split helpers."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np


METRIC_KEYS = ("recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10", "mrr_at_10", "ndcg_at_10")


def stable_id_hash(ids: Iterable[str]) -> str:
    """Hash an ordered ID sequence with unambiguous JSON encoding."""
    payload = json.dumps(list(ids), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def direct_cosine_top_k(
    query_embeddings: np.ndarray,
    document_embeddings: np.ndarray,
    document_ids: list[str],
    k: int = 10,
) -> tuple[list[list[str]], list[list[float]]]:
    """Rank normalized embeddings by cosine similarity with stable tie-breaking."""
    similarities = np.asarray(query_embeddings, dtype=np.float32) @ np.asarray(document_embeddings, dtype=np.float32).T
    ranked_ids: list[list[str]] = []
    ranked_scores: list[list[float]] = []
    for row in similarities:
        indices = sorted(range(len(document_ids)), key=lambda index: (-float(row[index]), document_ids[index]))[:k]
        ranked_ids.append([document_ids[index] for index in indices])
        ranked_scores.append([float(row[index]) for index in indices])
    return ranked_ids, ranked_scores


def _dcg(relevances: list[int]) -> float:
    return sum(value / np.log2(index + 2) for index, value in enumerate(relevances))


def score_query(query: dict[str, Any], ranked_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Score one query using record IDs and structured corpus metadata."""
    expected_ids = set(query.get("expected_relevant_record_ids", []))
    ranked_ids = [record["record_id"] for record in ranked_records]
    row: dict[str, Any] = {
        "query_id": query["query_id"],
        "difficulty_type": query["difficulty_type"],
        "expected_subject_family": query.get("expected_subject_family"),
        "expected_document_families": query.get("expected_document_families", []),
        "has_expected_record_ids": bool(expected_ids),
        "zero_result": not ranked_records,
    }
    if expected_ids:
        for k in (1, 3, 5, 10):
            row[f"recall_at_{k}"] = len(expected_ids.intersection(ranked_ids[:k])) / len(expected_ids)
        first_rank = next((index + 1 for index, value in enumerate(ranked_ids[:10]) if value in expected_ids), None)
        row["mrr_at_10"] = 0.0 if first_rank is None else 1.0 / first_rank
        relevance = [int(value in expected_ids) for value in ranked_ids[:10]]
        ideal = [1] * min(len(expected_ids), 10)
        row["ndcg_at_10"] = 0.0 if not ideal else float(_dcg(relevance) / _dcg(ideal))
        row["zero_relevant_hit"] = not any(relevance)
    else:
        for key in METRIC_KEYS:
            row[key] = None
        row["zero_relevant_hit"] = None

    expected_families = set(query.get("expected_document_families", []))
    expected_subject = query.get("expected_subject_family")
    for k in (1, 5):
        prefix = ranked_records[:k]
        row[f"document_family_hit_at_{k}"] = bool(expected_families.intersection(r.get("document_family") for r in prefix))
        row[f"subject_family_hit_at_{k}"] = (
            None if expected_subject is None else any(r.get("subject_family") == expected_subject for r in prefix)
        )
    return row


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"query_count": len(rows)}
    relevant_rows = [row for row in rows if row["has_expected_record_ids"]]
    result["queries_with_expected_record_ids"] = len(relevant_rows)
    for key in METRIC_KEYS:
        result[key] = float(np.mean([row[key] for row in relevant_rows])) if relevant_rows else None
    for prefix in ("document_family_hit", "subject_family_hit"):
        for k in (1, 5):
            key = f"{prefix}_at_{k}"
            applicable = [row[key] for row in rows if row[key] is not None]
            result[key] = float(np.mean(applicable)) if applicable else None
    result["zero_result_count"] = sum(bool(row["zero_result"]) for row in rows)
    result["zero_relevant_hit_count"] = sum(bool(row["zero_relevant_hit"]) for row in relevant_rows)
    return result


def evaluation_slices(queries: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build requested query slices without reading the sealed split outcomes."""
    slices: dict[str, list[str]] = defaultdict(list)
    for query in queries:
        query_id = query["query_id"]
        difficulty = query["difficulty_type"]
        subject = query.get("expected_subject_family") or "not_applicable"
        slices[f"difficulty:{difficulty}"].append(query_id)
        slices[f"subject_family:{subject}"].append(query_id)
        for family in query.get("expected_document_families", []):
            slices[f"document_family:{family}"].append(query_id)
        if difficulty == "school_level":
            slices["school_related"].append(query_id)
        if difficulty == "university_level":
            slices["university_related"].append(query_id)
        if difficulty == "alias":
            slices["aliases_and_misspellings"].append(query_id)
        if difficulty == "ambiguous":
            slices["ambiguous"].append(query_id)
        if difficulty == "unseen_wording":
            slices["unseen_wording"].append(query_id)
        if difficulty == "topic_level":
            slices["topic_queries"].append(query_id)
        if difficulty == "method_selection":
            slices["study_strategy_queries"].append(query_id)
    return dict(sorted(slices.items()))


def aggregate_evaluation(query_rows: list[dict[str, Any]], queries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate overall and requested development slices."""
    by_id = {row["query_id"]: row for row in query_rows}
    slices = evaluation_slices(queries)
    return {
        "overall": _aggregate(query_rows),
        "slices": {name: _aggregate([by_id[query_id] for query_id in ids]) for name, ids in slices.items()},
    }


def _labels(query: dict[str, Any]) -> set[str]:
    labels = {
        f"difficulty:{query['difficulty_type']}",
        f"subject:{query.get('expected_subject_family') or 'not_applicable'}",
    }
    labels.update(f"document:{value}" for value in query.get("expected_document_families", []))
    difficulty = query["difficulty_type"]
    if difficulty == "school_level":
        labels.add("special:school")
    if difficulty == "university_level":
        labels.add("special:university")
    return labels


def deterministic_stratified_split(
    queries: list[dict[str, Any]], *, development_count: int, seed: int
) -> tuple[list[str], list[str]]:
    """Choose a deterministic final third using only structured stratification labels."""
    final_count = len(queries) - development_count
    if final_count <= 0:
        raise ValueError("development_count must leave a non-empty final-test split")
    rng = random.Random(seed)
    candidates = list(queries)
    rng.shuffle(candidates)
    totals = Counter(label for query in queries for label in _labels(query))
    targets = {label: total * final_count / len(queries) for label, total in totals.items()}
    selected: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    while len(selected) < final_count:
        best = min(
            candidates,
            key=lambda query: (
                sum((counts[label] + int(label in _labels(query)) - targets[label]) ** 2 for label in totals),
                query["query_id"],
            ),
        )
        selected.append(best)
        candidates.remove(best)
        counts.update(_labels(best))
    final_ids = sorted(query["query_id"] for query in selected)
    final_set = set(final_ids)
    development_ids = sorted(query["query_id"] for query in queries if query["query_id"] not in final_set)
    return development_ids, final_ids


def split_counts(queries: list[dict[str, Any]], ids: Iterable[str]) -> dict[str, Any]:
    """Summarize split membership without exposing retrieval outcomes."""
    selected = set(ids)
    rows = [query for query in queries if query["query_id"] in selected]
    return {
        "total": len(rows),
        "by_difficulty_type": dict(sorted(Counter(q["difficulty_type"] for q in rows).items())),
        "by_subject_family": dict(sorted(Counter(q.get("expected_subject_family") or "not_applicable" for q in rows).items())),
        "by_document_family": dict(sorted(Counter(f for q in rows for f in q.get("expected_document_families", [])).items())),
        "school_related": sum(q["difficulty_type"] == "school_level" for q in rows),
        "university_related": sum(q["difficulty_type"] == "university_level" for q in rows),
    }
