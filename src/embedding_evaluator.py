"""Direct embedding benchmark orchestration for the ErgoStudy development set."""

from __future__ import annotations

import csv
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from src.dataset_io import file_sha256, read_json, read_jsonl, write_json
from src.embedding_models import (
    EmbeddingConfiguration,
    configure_deterministic_inference,
    encode_texts,
    load_sentence_transformer,
    measure_query_latencies,
    select_device,
    token_length_report,
)
from src.retrieval_metrics import METRIC_KEYS, aggregate_evaluation, direct_cosine_top_k, score_query


AUDIT_CATEGORIES = {
    "exact_name": {"exact_name"},
    "aliases_or_abbreviations": {"alias"},
    "ambiguous": {"ambiguous"},
    "unseen_wording": {"unseen_wording"},
    "topic": {"topic_level"},
    "study_strategy": {"method_selection"},
    "sensor_or_safety": {"sensor_situation", "missing_or_unreliable_sensor", "safety_boundary"},
}


def package_versions() -> dict[str, str]:
    """Return exact top-level versions relevant to the logical index."""
    names = ("torch", "sentence-transformers", "chromadb", "numpy", "huggingface-hub", "ipykernel", "psutil")
    return {name: version(name) for name in names}


def environment_report() -> dict[str, Any]:
    """Record portable Python, package, CPU-memory, and verified CUDA details."""
    import psutil
    import torch

    cuda_available = bool(torch.cuda.is_available())
    gpu: dict[str, Any] | None = None
    tensor_check: dict[str, Any]
    if cuda_available:
        device = torch.device("cuda:0")
        left = torch.tensor([1.0, 2.0, 3.0], device=device)
        right = torch.tensor([4.0, 5.0, 6.0], device=device)
        value = float(torch.dot(left, right).cpu().item())
        free_bytes, total_bytes = torch.cuda.mem_get_info(device)
        properties = torch.cuda.get_device_properties(device)
        gpu = {
            "name": torch.cuda.get_device_name(device),
            "total_memory_bytes": int(total_bytes),
            "available_memory_bytes_at_check": int(free_bytes),
            "compute_capability": f"{properties.major}.{properties.minor}",
        }
        tensor_check = {"device": "cuda:0", "operation": "dot([1,2,3],[4,5,6])", "result": value, "passed": value == 32.0}
    else:
        left = torch.tensor([1.0, 2.0, 3.0])
        right = torch.tensor([4.0, 5.0, 6.0])
        value = float(torch.dot(left, right).item())
        tensor_check = {"device": "cpu", "operation": "dot([1,2,3],[4,5,6])", "result": value, "passed": value == 32.0}
    return {
        "report_version": "1.0.0",
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "is_64_bit": sys.maxsize > 2**32,
        },
        "operating_system": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "system_memory_bytes": int(psutil.virtual_memory().total),
        "packages": package_versions(),
        "torch": {
            "version": torch.__version__,
            "cuda_available": cuda_available,
            "cuda_runtime": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version() if cuda_available else None,
        },
        "gpu": gpu,
        "selected_device": "cuda" if cuda_available else "cpu",
        "cpu_fallback_reason": None if cuda_available else "PyTorch could not initialize a compatible CUDA device; Stage 4 remains runnable on CPU.",
        "tensor_operation_check": tensor_check,
        "portable_paths_only": True,
    }


def model_hub_metadata(model_id: str) -> dict[str, Any]:
    """Resolve the Hub commit, declared license, and safely measured cache size."""
    from huggingface_hub import model_info, scan_cache_dir

    info = model_info(model_id)
    card_data = info.card_data.to_dict() if info.card_data is not None else {}
    cache_size = None
    try:
        cache = scan_cache_dir()
        repository = next((repo for repo in cache.repos if repo.repo_id == model_id and repo.repo_type == "model"), None)
        cache_size = None if repository is None else int(repository.size_on_disk)
    except Exception:
        cache_size = None
    return {
        "model_revision": info.sha,
        "license": card_data.get("license", "not_declared"),
        "cache_size_bytes": cache_size,
    }


def _qualitative_audit(
    queries: list[dict[str, Any]],
    ranked_ids: list[list[str]],
    ranked_scores: list[list[float]],
    records_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for category, difficulties in AUDIT_CATEGORIES.items():
        indexes = [index for index, query in enumerate(queries) if query["difficulty_type"] in difficulties][:3]
        if len(indexes) < 3:
            raise ValueError(f"Development split has fewer than three {category} audit queries")
        examples: list[dict[str, Any]] = []
        for index in indexes:
            query = queries[index]
            top = []
            for record_id, score in zip(ranked_ids[index][:5], ranked_scores[index][:5], strict=True):
                record = records_by_id[record_id]
                top.append({
                    "record_id": record_id,
                    "title": record["title"],
                    "document_family": record["document_family"],
                    "subject_family": record.get("subject_family", "not_applicable"),
                    "cosine_score": score,
                })
            expected = set(query.get("expected_relevant_record_ids", []))
            returned = {row["record_id"] for row in top}
            if expected:
                assessment = (
                    "At least one labeled relevant record appears in the top five."
                    if expected.intersection(returned)
                    else "No labeled relevant record appears in the top five; this is an embedding-model or label-coverage limitation to review."
                )
            else:
                assessment = "This query has criteria-only relevance; results require human review and are not counted as record-level relevance."
            examples.append({
                "query_id": query["query_id"],
                "query": query["query_text"],
                "expected_record_ids": query.get("expected_relevant_record_ids", []),
                "relevance_criteria": query["relevance_criteria"],
                "top_5": top,
                "assessment": assessment,
            })
        output[category] = examples
    return output


def benchmark_configuration(
    configuration: EmbeddingConfiguration,
    *,
    records: list[dict[str, Any]],
    development_queries: list[dict[str, Any]],
    batch_size: int,
    device: str,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Benchmark one configuration with direct normalized cosine retrieval."""
    import torch

    configure_deterministic_inference()
    model = load_sentence_transformer(configuration.model_id, device)
    record_ids = [record["record_id"] for record in records]
    document_texts = [configuration.format_document(record["retrieval_text"]) for record in records]
    query_texts = [configuration.format_query(query["query_text"]) for query in development_queries]
    document_tokens = token_length_report(model, record_ids, document_texts)
    query_tokens = token_length_report(model, [q["query_id"] for q in development_queries], query_texts)
    if document_tokens["truncation_count"]:
        raise RuntimeError(
            f"{configuration.config_id} would silently truncate corpus records: "
            f"{document_tokens['truncated_record_ids']}"
        )
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
    started = perf_counter()
    document_embeddings = encode_texts(
        model,
        document_texts,
        batch_size=batch_size,
        normalize_embeddings=configuration.normalize_embeddings,
    )
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    document_time = perf_counter() - started
    query_embeddings, latency = measure_query_latencies(
        model,
        query_texts,
        normalize_embeddings=configuration.normalize_embeddings,
    )
    peak_gpu_memory = int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
    ranked_ids, ranked_scores = direct_cosine_top_k(query_embeddings, document_embeddings, record_ids, k=10)
    records_by_id = {record["record_id"]: record for record in records}
    query_rows: list[dict[str, Any]] = []
    for query, ids, scores in zip(development_queries, ranked_ids, ranked_scores, strict=True):
        ranked_records = [records_by_id[record_id] for record_id in ids]
        row = score_query(query, ranked_records)
        row.update({"top_10_ids": ids, "top_10_cosine_scores": scores})
        query_rows.append(row)
    result = {
        **configuration.to_dict(),
        **model_hub_metadata(configuration.model_id),
        "device": device,
        "embedding_dimension": int(document_embeddings.shape[1]),
        "maximum_sequence_length": int(model.max_seq_length),
        "normalization_behavior": "SentenceTransformer normalized output; direct cosine uses float32 unit vectors",
        "document_embedding_time_seconds": document_time,
        **latency,
        "peak_gpu_memory_bytes": peak_gpu_memory,
        "document_token_report": document_tokens,
        "query_token_report": query_tokens,
        "metrics": aggregate_evaluation(query_rows, development_queries),
        "qualitative_audit": _qualitative_audit(
            development_queries, ranked_ids, ranked_scores, records_by_id
        ),
    }
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return result, document_embeddings, query_embeddings, query_rows


def _sensor_serious_failure(result: dict[str, Any]) -> bool:
    sensor = result["metrics"]["slices"].get("sensor_and_safety")
    if not sensor:
        return True
    recall = sensor.get("recall_at_5")
    family_hit = sensor.get("document_family_hit_at_5")
    return (recall is not None and recall < 0.25) or (family_hit is not None and family_hit < 0.60)


def select_configuration(results: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply the documented development-only quality and efficiency rule."""
    eligible = [result for result in results if not _sensor_serious_failure(result)]
    if not eligible:
        raise RuntimeError("Every candidate has a serious sensor/safety development-slice failure")
    best_recall = max(result["metrics"]["overall"]["recall_at_5"] for result in eligible)
    recall_band = [
        result for result in eligible
        if best_recall - result["metrics"]["overall"]["recall_at_5"] < 0.02
    ]
    best_mrr = max(result["metrics"]["overall"]["mrr_at_10"] for result in recall_band)
    mrr_band = [
        result for result in recall_band
        if best_mrr - result["metrics"]["overall"]["mrr_at_10"] < 0.02
    ]

    def slice_quality(result: dict[str, Any]) -> float:
        slices = result["metrics"]["slices"]
        values = []
        for name in ("ambiguous", "unseen_wording", "sensor_and_safety"):
            item = slices.get(name, {})
            for key in ("recall_at_5", "mrr_at_10", "document_family_hit_at_5"):
                if item.get(key) is not None:
                    values.append(item[key])
        return float(np.mean(values)) if values else 0.0

    chosen = sorted(
        mrr_band,
        key=lambda result: (
            -slice_quality(result),
            result["average_query_latency_ms"],
            result["peak_gpu_memory_bytes"] or 0,
            result["cache_size_bytes"] or 0,
            result["config_id"],
        ),
    )[0]
    decision = {
        "development_only": True,
        "sealed_final_test_metrics_computed": False,
        "serious_sensor_failure_rule": "Recall@5 below 0.25 or document-family Hit@5 below 0.60 on the sensor/safety development slice",
        "ineligible_configurations": [result["config_id"] for result in results if _sensor_serious_failure(result)],
        "highest_recall_at_5": best_recall,
        "recall_within_0_02": [result["config_id"] for result in recall_band],
        "highest_mrr_at_10_in_recall_band": best_mrr,
        "mrr_within_0_02": [result["config_id"] for result in mrr_band],
        "selected_config_id": chosen["config_id"],
        "reason": "Applied Recall@5, MRR@10, critical-slice quality, then efficiency in the required order.",
    }
    return chosen, decision


def write_benchmark_csv(path: Path, results: list[dict[str, Any]]) -> None:
    """Write one readable comparison row per configuration."""
    fields = [
        "config_id", "model_id", "model_revision", "license", "device", "embedding_dimension",
        "maximum_sequence_length", "document_embedding_time_seconds", "average_query_latency_ms",
        "median_query_latency_ms", "p95_query_latency_ms", "peak_gpu_memory_bytes", "cache_size_bytes",
        "truncation_count", "recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10",
        "mrr_at_10", "ndcg_at_10", "document_family_hit_at_1", "document_family_hit_at_5",
        "subject_family_hit_at_1", "subject_family_hit_at_5", "zero_result_count", "zero_relevant_hit_count",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            overall = result["metrics"]["overall"]
            row = {key: result.get(key) for key in fields}
            row["truncation_count"] = result["document_token_report"]["truncation_count"]
            for key in METRIC_KEYS + (
                "document_family_hit_at_1", "document_family_hit_at_5",
                "subject_family_hit_at_1", "subject_family_hit_at_5",
                "zero_result_count", "zero_relevant_hit_count",
            ):
                row[key] = overall.get(key)
            writer.writerow(row)


def load_stage4_inputs(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Load corpus and only the named development query IDs."""
    records = read_jsonl(project_root / "data" / "processed" / "knowledge_corpus.jsonl")
    all_queries = read_jsonl(project_root / "data" / "processed" / "retrieval_evaluation_queries.jsonl")
    split = read_json(project_root / "data" / "processed" / "retrieval_eval_split.json")
    development_ids = set(split["development_query_ids"])
    development = [query for query in all_queries if query["query_id"] in development_ids]
    if len(development) != 64 or development_ids.intersection(split["final_test_query_ids"]):
        raise ValueError("Development/final split integrity check failed")
    return records, development, split
