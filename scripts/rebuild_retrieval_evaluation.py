"""Rebuild the non-sensor retrieval split and evaluate the unchanged frozen retriever."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_retriever import _evaluate_configuration  # noqa: E402
from src.chroma_store import canonical_json_hash  # noqa: E402
from src.dataset_io import read_json, read_jsonl, write_json, write_jsonl  # noqa: E402
from src.retrieval_metrics import deterministic_stratified_split, split_counts, stable_id_hash  # noqa: E402
from src.retriever import RetrievalService  # noqa: E402


PROCESSED = PROJECT_ROOT / "data" / "processed"
SPLIT_SEED = 20260730
DEVELOPMENT_COUNT = 61
REMOVED_QUERY_IDS = {"rq-128", "rq-129", "rq-130", "rq-131", "rq-132"}


def _assert_clean_queries(queries: list[dict]) -> None:
    forbidden_difficulties = {"sensor_situation", "missing_or_unreliable_sensor", "safety_boundary"}
    for query in queries:
        if query["query_id"] in REMOVED_QUERY_IDS:
            raise AssertionError(f"Removed query ID remains: {query['query_id']}")
        if query.get("difficulty_type") in forbidden_difficulties:
            raise AssertionError(f"Sensor-only difficulty remains: {query['query_id']}")
        if "sensor_intervention" in query.get("expected_document_families", []):
            raise AssertionError(f"Sensor-only expected family remains: {query['query_id']}")


def main() -> int:
    queries = read_jsonl(PROCESSED / "retrieval_evaluation_queries.jsonl")
    _assert_clean_queries(queries)
    if len(queries) != 91:
        raise AssertionError(f"Expected 91 non-sensor queries, found {len(queries)}")

    development_ids, final_ids = deterministic_stratified_split(
        queries,
        development_count=DEVELOPMENT_COUNT,
        seed=SPLIT_SEED,
    )
    split = {
        "split_version": "1.0.0-current-scope",
        "fixed_seed": SPLIT_SEED,
        "source_query_count": len(queries),
        "development_query_ids": development_ids,
        "final_test_query_ids": final_ids,
        "counts": {
            "development": split_counts(queries, development_ids),
            "final_test": split_counts(queries, final_ids),
        },
        "integrity_hashes": {
            "all_query_ids_sha256": stable_id_hash(query["query_id"] for query in queries),
            "development_query_ids_sha256": stable_id_hash(development_ids),
            "final_test_query_ids_sha256": stable_id_hash(final_ids),
        },
        "scope_note": "Fresh deterministic split after removal of five sensor-only queries.",
    }
    write_json(PROCESSED / "retrieval_eval_split.json", split)

    by_id = {query["query_id"]: query for query in queries}
    records = {
        record["record_id"]: record
        for record in read_jsonl(PROCESSED / "knowledge_corpus.jsonl")
    }
    development = [by_id[query_id] for query_id in development_ids]
    final = [by_id[query_id] for query_id in final_ids]
    with RetrievalService.from_frozen_config(PROJECT_ROOT) as service:
        development_rows, development_metrics = _evaluate_configuration(service, development, records)
        final_rows, final_metrics = _evaluate_configuration(service, final, records)
        configuration_hash = canonical_json_hash(service.configuration.to_dict())

    write_jsonl(
        PROCESSED / "development_retrieval_results.jsonl",
        [
            {"query_id": query["query_id"], "split": "development", "query_text": query["query_text"], **row}
            for query, row in zip(development, development_rows, strict=True)
        ],
    )
    write_jsonl(
        PROCESSED / "final_test_retrieval_results.jsonl",
        [
            {"query_id": query["query_id"], "split": "final_test", "query_text": query["query_text"], **row}
            for query, row in zip(final, final_rows, strict=True)
        ],
    )
    metrics_payload = {
        "evaluation": "current_scope_final_test",
        "evaluation_date": date.today().isoformat(),
        "query_count": len(final),
        "corpus_query_count": len(queries),
        "frozen_config_id": "alias_plus_dense",
        "retrieval_configuration_hash": configuration_hash,
        "retuned": False,
        "metrics": final_metrics,
    }
    write_json(PROCESSED / "final_retrieval_metrics.json", metrics_payload)

    frozen = read_json(PROCESSED / "retrieval_config.json")
    manifest = read_json(PROCESSED / "chroma_index_manifest.json")
    frozen.pop("development_candidate_metrics", None)
    frozen["development_query_count"] = len(development)
    frozen["development_query_id_hash"] = stable_id_hash(development_ids)
    frozen["sealed_final_test_query_count"] = len(final)
    frozen["sealed_final_test_query_id_hash"] = stable_id_hash(final_ids)
    frozen["collection"]["manifest_hash"] = canonical_json_hash(manifest)
    frozen["selection_rule"] = [
        "retain the previously selected alias_plus_dense configuration without retuning"
    ]
    frozen["current_scope_evaluation"] = {
        "sensor_queries_removed": 5,
        "retuned": False,
        "query_count": len(final),
    }
    write_json(PROCESSED / "retrieval_config.json", frozen)

    print(json.dumps({
        "evaluation_query_count": len(queries),
        "development_query_count": len(development),
        "final_query_count": len(final),
        "development_metrics": development_metrics["overall"],
        "final_metrics": final_metrics["overall"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
