"""Verify persistence, dense-result overlap, separation, and metadata filters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chroma_store import COLLECTION_NAME, close_client, query_collection, reopen_and_verify  # noqa: E402
from src.dataset_io import read_json, read_jsonl, write_json, write_jsonl  # noqa: E402
from src.embedding_evaluator import load_stage4_inputs  # noqa: E402
from src.embedding_models import encode_texts, load_embedding_configurations, load_sentence_transformer  # noqa: E402
from src.retrieval_metrics import aggregate_evaluation, direct_cosine_top_k, score_query  # noqa: E402


FILTER_CASES = {
    "subject_profile_only": {"document_family": "subject_profile"},
    "topic_profile_only": {"document_family": "topic_profile"},
    "computing_subject_family": {"subject_family": "computing"},
    "mathematics_subject_family": {"subject_family": "mathematics"},
    "school_supported": {"supports_school": True},
    "university_supported": {"supports_university": True},
    "reviewed_only": {"reviewed": True},
    "sensor_intervention_only": {"document_family": "sensor_intervention"},
    "non_medical_wellbeing": {"safety_scope": "non_medical_wellbeing"},
}


def main() -> int:
    import chromadb

    processed = PROJECT_ROOT / "data" / "processed"
    records, queries, split = load_stage4_inputs(PROJECT_ROOT)
    selected = read_json(processed / "selected_embedding_model.json")
    manifest = read_json(processed / "chroma_index_manifest.json")
    persisted = reopen_and_verify(
        project_root=PROJECT_ROOT,
        chroma_path=PROJECT_ROOT / "chroma_db",
        records=records,
        manifest=manifest,
    )
    settings, configurations = load_embedding_configurations(PROJECT_ROOT / "config" / "embedding_models.json")
    configuration = next(item for item in configurations if item.config_id == selected["config_id"])
    model = load_sentence_transformer(
        configuration.model_id,
        selected["device"],
        revision=selected["model_revision"],
        local_files_only=True,
    )
    document_embeddings = encode_texts(
        model,
        [configuration.format_document(record["retrieval_text"]) for record in records],
        batch_size=int(settings["batch_size"]),
        normalize_embeddings=configuration.normalize_embeddings,
    )
    query_embeddings = encode_texts(
        model,
        [configuration.format_query(query["query_text"]) for query in queries],
        batch_size=int(settings["batch_size"]),
        normalize_embeddings=configuration.normalize_embeddings,
    )
    record_ids = [record["record_id"] for record in records]
    direct_ids, direct_scores = direct_cosine_top_k(query_embeddings, document_embeddings, record_ids, k=10)
    chroma_results = query_collection(PROJECT_ROOT / "chroma_db", query_embeddings, n_results=10)
    chroma_ids = chroma_results["ids"]
    overlaps = [len(set(a).intersection(b)) / 10.0 for a, b in zip(direct_ids, chroma_ids, strict=True)]
    average_overlap = float(np.mean(overlaps))
    if average_overlap < 0.90:
        raise AssertionError(f"Direct/Chroma top-10 overlap {average_overlap:.3f} is below 0.90")
    records_by_id = {record["record_id"]: record for record in records}
    direct_score_rows = [
        score_query(query, [records_by_id[record_id] for record_id in ids])
        for query, ids in zip(queries, direct_ids, strict=True)
    ]
    score_rows = [
        score_query(query, [records_by_id[record_id] for record_id in ids])
        for query, ids in zip(queries, chroma_ids, strict=True)
    ]
    direct_metrics = aggregate_evaluation(direct_score_rows, queries)
    metrics = aggregate_evaluation(score_rows, queries)
    mismatch_details = []
    for query, direct, chroma, overlap in zip(queries, direct_ids, chroma_ids, overlaps, strict=True):
        if overlap < 1.0:
            mismatch_details.append({
                "query_id": query["query_id"],
                "top_10_overlap": overlap,
                "direct_only_ids": sorted(set(direct).difference(chroma)),
                "chroma_only_ids": sorted(set(chroma).difference(direct)),
            })
    baseline_rows = []
    for query, d_ids, d_scores, c_ids, distances, overlap in zip(
        queries, direct_ids, direct_scores, chroma_ids, chroma_results["distances"], overlaps, strict=True
    ):
        baseline_rows.append({
            "query_id": query["query_id"],
            "split": "development",
            "direct_top_10_ids": d_ids,
            "direct_top_10_cosine_scores": d_scores,
            "chroma_top_10_ids": c_ids,
            "chroma_top_10_cosine_scores": [1.0 - float(distance) for distance in distances],
            "top_10_overlap": overlap,
        })
    write_jsonl(processed / "baseline_retrieval_results.jsonl", baseline_rows)

    client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_db"))
    collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
    filter_results = {}
    first_embedding = query_embeddings[0].tolist()
    for name, where in FILTER_CASES.items():
        result = collection.query(
            query_embeddings=[first_embedding], where=where, n_results=10, include=["metadatas"]
        )
        metadatas = result["metadatas"][0]
        key, expected = next(iter(where.items()))
        passed = bool(metadatas) and all(metadata[key] == expected for metadata in metadatas)
        if not passed:
            raise AssertionError(f"Metadata filter failed: {name}")
        filter_results[name] = {"passed": True, "returned_count": len(metadatas), "where": where}

    evaluation_ids = {query["record_id"] for query in read_jsonl(processed / "retrieval_evaluation_queries.jsonl")}
    corpus_ids = set(collection.get(include=[])["ids"])
    leaked_ids = sorted(evaluation_ids.intersection(corpus_ids))
    if leaked_ids:
        raise AssertionError(f"Evaluation records leaked into Chroma: {leaked_ids}")
    close_client(client)
    verification = {
        "persistence": persisted,
        "development_query_count": len(queries),
        "sealed_final_test_query_count": len(split["final_test_query_ids"]),
        "sealed_final_test_metrics_computed": False,
        "average_direct_chroma_top_10_overlap": average_overlap,
        "minimum_direct_chroma_top_10_overlap": min(overlaps),
        "mismatch_query_count": len(mismatch_details),
        "mismatch_details": mismatch_details,
        "mismatch_assessment": (
            f"{len(mismatch_details)} development queries differ because Chroma HNSW is approximate; "
            "the required average overlap is exceeded and logical contents are intact."
            if mismatch_details
            else "Chroma and direct cosine top-10 ID sets match for every development query."
        ),
        "direct_metrics": direct_metrics,
        "chroma_metrics": metrics,
        "metadata_filters": filter_results,
        "evaluation_query_ids_in_collection": 0,
    }
    summary = read_json(processed / "embedding_benchmark_summary.json")
    summary["chroma_verification"] = verification
    write_json(processed / "embedding_benchmark_summary.json", summary)
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
