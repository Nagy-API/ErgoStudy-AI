"""Classify development-only baseline retrieval failures."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_io import read_json, read_jsonl, write_json  # noqa: E402


PROCESSED = PROJECT_ROOT / "data" / "processed"
ALLOWED_CATEGORIES = {
    "embedding limitation",
    "corpus coverage limitation",
    "narrow or incorrect evaluation label",
    "ambiguous query",
    "wrong document-family ranking",
    "alias-resolution failure",
    "metadata mismatch",
}


def _classification(
    query: dict[str, Any],
    evaluation: dict[str, Any],
    top_five: list[dict[str, Any]],
    records_by_id: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    expected_ids = query.get("expected_relevant_record_ids") or []
    for expected_id in expected_ids:
        record = records_by_id.get(expected_id)
        if record is None:
            return "corpus coverage limitation", "A labeled record ID is absent from the retrieval corpus."
        expected_subject = query.get("expected_subject_family")
        expected_families = set(query.get("expected_document_families", []))
        if (
            expected_subject
            and record.get("document_family") in {"subject_profile", "subject_alias", "topic_profile"}
            and record.get("subject_family") != expected_subject
        ):
            return "metadata mismatch", "A labeled record's subject_family conflicts with the query metadata."
        if expected_families and record.get("document_family") not in expected_families:
            return "metadata mismatch", "A labeled record's document_family conflicts with the query metadata."
    expected_subject = query.get("expected_subject_family")
    expected_families = set(query.get("expected_document_families", []))
    plausible_alternative = any(
        record.get("document_family") in expected_families
        and (expected_subject is None or record.get("subject_family") == expected_subject)
        for record in top_five
    )
    if query["difficulty_type"] == "ambiguous":
        return "ambiguous query", "The wording intentionally permits multiple reasonable interpretations."
    if query["difficulty_type"] == "alias":
        if plausible_alternative and evaluation["zero_relevant_hit"]:
            return (
                "narrow or incorrect evaluation label",
                "The dense top five resolves the stated subject but the labeled alias or companion method is narrower.",
            )
        return "alias-resolution failure", "Dense retrieval did not reliably resolve the controlled alias in the top five."
    if not evaluation["document_family_hit_at_5"]:
        return "wrong document-family ranking", "No expected document family appears in the dense top five."
    if not expected_ids:
        return "corpus coverage limitation", "The criteria-only query lacks a record-level target and corpus coverage is incomplete."
    if plausible_alternative and evaluation["zero_relevant_hit"]:
        return (
            "narrow or incorrect evaluation label",
            "The dense top five contains a family- and subject-compatible alternative but not the narrow labeled ID.",
        )
    return "embedding limitation", "The labeled record exists, but dense similarity ranks it too low."


def main() -> int:
    split = read_json(PROCESSED / "retrieval_eval_split.json")
    development_ids = set(split["development_query_ids"])
    final_ids = set(split["final_test_query_ids"])
    queries = {
        query["query_id"]: query
        for query in read_jsonl(PROCESSED / "retrieval_evaluation_queries.jsonl")
        if query["query_id"] in development_ids
    }
    records_by_id = {record["record_id"]: record for record in read_jsonl(PROCESSED / "knowledge_corpus.jsonl")}
    development_rows = read_jsonl(PROCESSED / "development_retrieval_results.jsonl")
    if final_ids.intersection(row["query_id"] for row in development_rows):
        raise AssertionError("Final-test IDs leaked into development retrieval results")

    failures = []
    for row in development_rows:
        query = queries[row["query_id"]]
        baseline = row["configurations"]["baseline_dense"]
        evaluation = baseline["evaluation"]
        record_failure = evaluation["recall_at_5"] is not None and evaluation["recall_at_5"] < 1.0
        family_failure = not evaluation["document_family_hit_at_5"]
        subject_failure = evaluation["subject_family_hit_at_5"] is False
        if not (record_failure or family_failure or subject_failure):
            continue
        top_five = [records_by_id[result["record_id"]] for result in baseline["results"][:5]]
        category, explanation = _classification(query, evaluation, top_five, records_by_id)
        if category not in ALLOWED_CATEGORIES:
            raise AssertionError(f"Unexpected category: {category}")
        alias_plus = row["configurations"]["alias_plus_dense"]["evaluation"]
        intent_aware = row["configurations"]["intent_aware_blend"]["evaluation"]
        failures.append(
            {
                "query_id": row["query_id"],
                "query_text": query["query_text"],
                "primary_category": category,
                "explanation": explanation,
                "baseline": {
                    "recall_at_5": evaluation["recall_at_5"],
                    "mrr_at_10": evaluation["mrr_at_10"],
                    "document_family_hit_at_5": evaluation["document_family_hit_at_5"],
                    "subject_family_hit_at_5": evaluation["subject_family_hit_at_5"],
                    "top_5_ids": [result["record_id"] for result in baseline["results"][:5]],
                },
                "alias_plus_dense": {
                    "recall_at_5": alias_plus["recall_at_5"],
                    "mrr_at_10": alias_plus["mrr_at_10"],
                    "document_family_hit_at_5": alias_plus["document_family_hit_at_5"],
                    "subject_family_hit_at_5": alias_plus["subject_family_hit_at_5"],
                },
                "intent_aware": {
                    "recall_at_5": intent_aware["recall_at_5"],
                    "mrr_at_10": intent_aware["mrr_at_10"],
                    "document_family_hit_at_5": intent_aware["document_family_hit_at_5"],
                    "subject_family_hit_at_5": intent_aware["subject_family_hit_at_5"],
                },
            }
        )
    counts = Counter(item["primary_category"] for item in failures)
    payload = {
        "analysis_scope": "64-query development split only",
        "final_test_query_ids_used": False,
        "baseline_failure_definition": "Recall@5 below 1.0, document-family Hit@5 failure, or subject-family Hit@5 failure.",
        "baseline_failure_count": len(failures),
        "category_counts": {category: counts.get(category, 0) for category in sorted(ALLOWED_CATEGORIES)},
        "failures": failures,
    }
    write_json(PROCESSED / "development_failure_analysis.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
