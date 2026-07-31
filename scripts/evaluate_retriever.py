"""Evaluate development candidates and run the sealed final retrieval test once."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chroma_store import canonical_json_hash  # noqa: E402
from src.dataset_io import read_json, read_jsonl, write_json, write_jsonl  # noqa: E402
from src.retrieval_metrics import aggregate_evaluation, score_query, stable_id_hash  # noqa: E402
from src.retriever import (  # noqa: E402
    RetrievalService,
    alias_configuration,
    baseline_configuration,
    intent_configuration,
)


PROCESSED = PROJECT_ROOT / "data" / "processed"
DEVELOPMENT_RESULTS = PROCESSED / "development_retrieval_results.jsonl"
FINAL_RESULTS = PROCESSED / "final_test_retrieval_results.jsonl"
FINAL_METRICS = PROCESSED / "final_retrieval_metrics.json"
FROZEN_CONFIG = PROCESSED / "retrieval_config.json"
TOP_K = 10


def _inputs() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    queries = read_jsonl(PROCESSED / "retrieval_evaluation_queries.jsonl")
    split = read_json(PROCESSED / "retrieval_eval_split.json")
    records = {record["record_id"]: record for record in read_jsonl(PROCESSED / "knowledge_corpus.jsonl")}
    return queries, split, records


def _selected_queries(queries: list[dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    by_id = {query["query_id"]: query for query in queries}
    missing = sorted(set(ids).difference(by_id))
    if missing:
        raise ValueError(f"Split refers to missing query IDs: {missing}")
    return [by_id[query_id] for query_id in ids]


def _compact_result(result: Any) -> dict[str, Any]:
    return {
        "record_id": result.record_id,
        "title": result.title,
        "document_family": result.document_family,
        "subject_family": result.subject_family,
        "score": result.score,
    }


def _evaluate_configuration(
    service: RetrievalService,
    queries: list[dict[str, Any]],
    records_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for query in queries:
        started = perf_counter()
        results = service.retrieve(query["query_text"], top_k=TOP_K)
        latency_ms = (perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        ranked_records = [records_by_id[result.record_id] for result in results]
        evaluation = score_query(query, ranked_records)
        score_rows.append(evaluation)
        output.append(
            {
                "query_id": query["query_id"],
                "latency_ms": latency_ms,
                "results": [_compact_result(result) for result in results],
                "evaluation": evaluation,
            }
        )
    metrics = aggregate_evaluation(score_rows, queries)
    sorted_latencies = sorted(latencies)
    metrics["latency_ms"] = {
        "average": sum(latencies) / len(latencies),
        "median": sorted_latencies[len(sorted_latencies) // 2],
        "maximum": max(latencies),
    }
    metrics["priority_slices"] = _priority_slices(score_rows, queries)
    return output, metrics


def _priority_slices(score_rows: list[dict[str, Any]], queries: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["query_id"]: row for row in score_rows}
    groups = {
        "alias_and_abbreviation": [q for q in queries if q["difficulty_type"] == "alias"],
        "session_template": [q for q in queries if "session_template" in q.get("expected_document_families", [])],
        "study_strategy": [q for q in queries if "study_strategy" in q.get("expected_document_families", [])],
    }
    return {
        name: aggregate_evaluation([by_id[q["query_id"]] for q in group], group)["overall"]
        for name, group in groups.items()
        if len(group) >= 3
    }


def _selection_key(metrics: dict[str, Any]) -> tuple[float, ...]:
    overall = metrics["overall"]
    slices = metrics["priority_slices"]
    alias = slices.get("alias_and_abbreviation", {})
    session = slices.get("session_template", {})
    strategy = slices.get("study_strategy", {})
    return (
        float(overall["recall_at_5"] or 0.0),
        float(overall["mrr_at_10"] or 0.0),
        float(alias.get("recall_at_5") or 0.0),
        float(session.get("document_family_hit_at_5") or 0.0),
        float(strategy.get("document_family_hit_at_5") or 0.0),
        -float(metrics["latency_ms"]["average"]),
    )


def development_evaluation(*, freeze: bool, write_results: bool = False) -> dict[str, Any]:
    if FINAL_RESULTS.exists() or FINAL_METRICS.exists():
        raise RuntimeError("Final-test artifacts already exist; development tuning is permanently closed")
    queries, split, records_by_id = _inputs()
    final_ids = set(split["final_test_query_ids"])
    development = _selected_queries(queries, split["development_query_ids"])
    if len(development) != 64 or final_ids.intersection(q["query_id"] for q in development):
        raise AssertionError("Development/final split isolation failed")

    configurations = [baseline_configuration(), alias_configuration(), intent_configuration()]
    all_rows: dict[str, list[dict[str, Any]]] = {}
    all_metrics: dict[str, dict[str, Any]] = {}
    with RetrievalService(PROJECT_ROOT, configuration=configurations[0]) as service:
        for configuration in configurations:
            service.configuration = configuration
            rows, metrics = _evaluate_configuration(service, development, records_by_id)
            all_rows[configuration.config_id] = rows
            all_metrics[configuration.config_id] = metrics

    selected = max(configurations, key=lambda item: _selection_key(all_metrics[item.config_id]))
    summary = {
        "development_query_count": len(development),
        "candidate_metrics": all_metrics,
        "selected_config_id": selected.config_id,
        "selection_key": list(_selection_key(all_metrics[selected.config_id])),
    }
    if not freeze and not write_results:
        return summary

    rows_by_config = {
        config_id: {row["query_id"]: row for row in rows}
        for config_id, rows in all_rows.items()
    }
    output_rows = []
    for query in development:
        analysis = service.query_analyzer.analyze(query["query_text"])
        output_rows.append(
            {
                "query_id": query["query_id"],
                "split": "development",
                "query_text": query["query_text"],
                "query_analysis": {
                    "normalized_query": analysis.normalized_query,
                    "primary_intent": analysis.primary_intent,
                    "intents": list(analysis.intents),
                    "resolved_subject_record_ids": list(analysis.alias_resolution.resolved_subject_record_ids),
                    "ambiguity_preserved": analysis.alias_resolution.has_ambiguity,
                },
                "configurations": {
                    config_id: rows_by_config[config_id][query["query_id"]]
                    for config_id in sorted(rows_by_config)
                },
            }
        )
    if final_ids.intersection(row["query_id"] for row in output_rows):
        raise AssertionError("Final-test IDs entered the development output")
    write_jsonl(DEVELOPMENT_RESULTS, output_rows)

    if not freeze:
        return summary

    selected_payload = selected.to_dict()
    selected_model = read_json(PROCESSED / "selected_embedding_model.json")
    manifest = read_json(PROCESSED / "chroma_index_manifest.json")
    frozen = {
        "schema_version": "1.0.0",
        "frozen": True,
        "frozen_date": date.today().isoformat(),
        "frozen_before_final_test": True,
        "final_test_metrics_seen_during_selection": False,
        "development_query_count": 64,
        "development_query_id_hash": stable_id_hash(split["development_query_ids"]),
        "sealed_final_test_query_count": 32,
        "sealed_final_test_query_id_hash": stable_id_hash(split["final_test_query_ids"]),
        "embedding_configuration": {
            "config_id": selected_model["config_id"],
            "model_id": selected_model["model_id"],
            "model_revision": selected_model["model_revision"],
            "normalize_embeddings": selected_model["normalize_embeddings"],
            "query_prefix": selected_model["query_prefix"],
            "document_prefix": selected_model["document_prefix"],
        },
        "collection": {
            "name": manifest["collection_name"],
            "manifest_hash": canonical_json_hash(manifest),
            "distance_metric": manifest["distance_metric"],
        },
        "retrieval_configuration": selected_payload,
        "retrieval_configuration_hash": canonical_json_hash(selected_payload),
        "selection_rule": [
            "maximize development Recall@5",
            "then maximize development MRR@10",
            "then alias Recall@5",
            "then session-template and study-strategy document-family Hit@5",
            "then minimize measured average latency",
        ],
        "development_candidate_metrics": all_metrics,
        "selected_config_id": selected.config_id,
    }
    write_json(FROZEN_CONFIG, frozen)
    return summary


def _assert_development_isolation(split: dict[str, Any]) -> dict[str, Any]:
    if not DEVELOPMENT_RESULTS.exists() or not FROZEN_CONFIG.exists():
        raise RuntimeError("Development results and frozen retrieval_config.json are required")
    final_ids = set(split["final_test_query_ids"])
    development_rows = read_jsonl(DEVELOPMENT_RESULTS)
    development_ids = {row["query_id"] for row in development_rows}
    leaked = sorted(final_ids.intersection(development_ids))
    if leaked:
        raise AssertionError(f"Final-test IDs found in development results: {leaked}")
    failure_path = PROCESSED / "development_failure_analysis.json"
    if failure_path.exists():
        failure_text = failure_path.read_text(encoding="utf-8")
        mentioned = sorted(query_id for query_id in final_ids if query_id in failure_text)
        if mentioned:
            raise AssertionError(f"Final-test IDs found in failure analysis: {mentioned}")
    frozen = read_json(FROZEN_CONFIG)
    if frozen["development_query_id_hash"] != stable_id_hash(split["development_query_ids"]):
        raise AssertionError("Frozen configuration development-ID hash mismatch")
    if frozen["sealed_final_test_query_id_hash"] != stable_id_hash(split["final_test_query_ids"]):
        raise AssertionError("Frozen configuration sealed-ID hash mismatch")
    return {
        "development_artifact_query_count": len(development_ids),
        "final_test_ids_in_development_artifacts": 0,
        "development_id_hash_verified": True,
        "sealed_final_id_hash_verified": True,
    }


def final_evaluation(*, acknowledged: bool) -> dict[str, Any]:
    if not acknowledged:
        raise RuntimeError("Pass --acknowledge-sealed-test to run the sealed set exactly once")
    if FINAL_RESULTS.exists() or FINAL_METRICS.exists():
        raise RuntimeError("Final-test artifacts already exist; refusing a second sealed evaluation")
    queries, split, records_by_id = _inputs()
    isolation = _assert_development_isolation(split)
    final_queries = _selected_queries(queries, split["final_test_query_ids"])
    if len(final_queries) != 32:
        raise AssertionError("The sealed final-test set must contain exactly 32 queries")
    frozen = read_json(FROZEN_CONFIG)
    with RetrievalService.from_frozen_config(PROJECT_ROOT) as service:
        rows, metrics = _evaluate_configuration(service, final_queries, records_by_id)
        configuration_hash = canonical_json_hash(service.configuration.to_dict())
    if configuration_hash != frozen["retrieval_configuration_hash"]:
        raise AssertionError("Runtime configuration differs from the frozen configuration")
    output_rows = [
        {
            "query_id": query["query_id"],
            "split": "final_test",
            "query_text": query["query_text"],
            **row,
        }
        for query, row in zip(final_queries, rows, strict=True)
    ]
    write_jsonl(FINAL_RESULTS, output_rows)
    payload = {
        "evaluation": "sealed_final_test",
        "evaluation_date": date.today().isoformat(),
        "evaluated_exactly_once_guard": True,
        "query_count": 32,
        "frozen_config_id": frozen["selected_config_id"],
        "retrieval_configuration_hash": configuration_hash,
        "development_isolation": isolation,
        "metrics": metrics,
    }
    write_json(FINAL_METRICS, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("development", "final-test"), required=True)
    parser.add_argument("--freeze", action="store_true", help="Write development results and freeze the selected configuration")
    parser.add_argument("--write-results", action="store_true", help="Write development comparisons without freezing")
    parser.add_argument("--acknowledge-sealed-test", action="store_true")
    args = parser.parse_args()
    if args.phase == "development":
        result = development_evaluation(freeze=args.freeze, write_results=args.write_results)
    else:
        if args.freeze or args.write_results:
            parser.error("--freeze and --write-results are only valid for development")
        result = final_evaluation(acknowledged=args.acknowledge_sealed_test)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
