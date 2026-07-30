"""Create the sealed split, benchmark candidates, and select from development data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_io import file_sha256, read_jsonl, write_json, write_jsonl  # noqa: E402
from src.embedding_evaluator import (  # noqa: E402
    benchmark_configuration,
    environment_report,
    load_stage4_inputs,
    package_versions,
    select_configuration,
    write_benchmark_csv,
)
from src.embedding_models import load_embedding_configurations, select_device  # noqa: E402
from src.retrieval_metrics import (  # noqa: E402
    deterministic_stratified_split,
    split_counts,
    stable_id_hash,
)


def create_or_verify_split() -> dict:
    config, _ = load_embedding_configurations(PROJECT_ROOT / "config" / "embedding_models.json")
    query_path = PROJECT_ROOT / "data" / "processed" / "retrieval_evaluation_queries.jsonl"
    queries = read_jsonl(query_path)
    development_ids, final_ids = deterministic_stratified_split(
        queries,
        development_count=int(config["development_count"]),
        seed=int(config["split_seed"]),
    )
    all_ids = sorted(query["query_id"] for query in queries)
    split = {
        "split_version": "1.0.0",
        "fixed_seed": int(config["split_seed"]),
        "source_query_count": len(queries),
        "development_query_ids": development_ids,
        "final_test_query_ids": final_ids,
        "counts": {
            "development": split_counts(queries, development_ids),
            "final_test": split_counts(queries, final_ids),
        },
        "integrity_hashes": {
            "source_file_sha256": file_sha256(query_path),
            "all_query_ids_sha256": stable_id_hash(all_ids),
            "development_query_ids_sha256": stable_id_hash(development_ids),
            "final_test_query_ids_sha256": stable_id_hash(final_ids),
            "query_records_sha256": hashlib.sha256(
                json.dumps(queries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "final_test_policy": "IDs exist and are excluded from development metrics; Stage 4 computes no final-test retrieval results.",
    }
    path = PROJECT_ROOT / "data" / "processed" / "retrieval_eval_split.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != split:
            raise RuntimeError("Existing retrieval split differs from the deterministic split")
    else:
        write_json(path, split)
    return split


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-split", action="store_true", help="Create/verify the split without loading models")
    arguments = parser.parse_args()
    split = create_or_verify_split()
    if arguments.prepare_split:
        print(json.dumps(split["counts"], indent=2, sort_keys=True))
        return 0

    settings, configurations = load_embedding_configurations(PROJECT_ROOT / "config" / "embedding_models.json")
    write_json(PROJECT_ROOT / "data" / "processed" / "stage4_environment.json", environment_report())
    records, development_queries, _ = load_stage4_inputs(PROJECT_ROOT)
    device = select_device()
    results = []
    runtime_rows = {}
    for configuration in configurations:
        print(f"Benchmarking {configuration.config_id} on {device}...", flush=True)
        result, _document_embeddings, _query_embeddings, query_rows = benchmark_configuration(
            configuration,
            records=records,
            development_queries=development_queries,
            batch_size=int(settings["batch_size"]),
            device=device,
        )
        results.append(result)
        runtime_rows[configuration.config_id] = query_rows
        print(json.dumps(result["metrics"]["overall"], indent=2, sort_keys=True), flush=True)

    selected, decision = select_configuration(results)
    processed = PROJECT_ROOT / "data" / "processed"
    summary = {
        "benchmark_version": settings["benchmark_version"],
        "corpus_record_count": len(records),
        "corpus_sha256": file_sha256(processed / "knowledge_corpus.jsonl"),
        "development_query_count": len(development_queries),
        "sealed_final_test_query_count": len(split["final_test_query_ids"]),
        "sealed_final_test_metrics_computed": False,
        "package_versions": package_versions(),
        "results": results,
        "selection_decision": decision,
    }
    write_json(processed / "embedding_benchmark_summary.json", summary)
    write_benchmark_csv(processed / "embedding_benchmark_results.csv", results)
    selected_record = {
        key: selected[key]
        for key in (
            "config_id", "model_id", "model_revision", "license", "embedding_dimension",
            "maximum_sequence_length", "device", "normalize_embeddings", "normalization_behavior",
            "query_prefix", "document_prefix", "cache_size_bytes", "document_embedding_time_seconds",
            "average_query_latency_ms", "median_query_latency_ms", "p95_query_latency_ms",
            "peak_gpu_memory_bytes", "document_token_report", "query_token_report",
        )
    }
    selected_record["selection_decision"] = decision
    selected_record["development_metrics"] = selected["metrics"]
    selected_record["sealed_final_test_metrics_computed"] = False
    write_json(processed / "selected_embedding_model.json", selected_record)
    baseline = []
    for row in runtime_rows[selected["config_id"]]:
        baseline.append({
            "query_id": row["query_id"],
            "split": "development",
            "direct_top_10_ids": row["top_10_ids"],
            "direct_top_10_cosine_scores": row["top_10_cosine_scores"],
        })
    write_jsonl(processed / "baseline_retrieval_results.jsonl", baseline)
    print(f"Selected {selected['config_id']} using development queries only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
