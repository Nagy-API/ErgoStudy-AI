"""Safe persistent Chroma collection construction and verification."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from src.metadata_projection import project_metadata, projection_hash
from src.retrieval_metrics import stable_id_hash


COLLECTION_NAME = "ergostudy-knowledge-1-0-0"
COLLECTION_PATTERN = re.compile(r"^ergostudy-knowledge-[0-9]+-[0-9]+-[0-9]+$")
INDEX_CONFIGURATION = {
    "space": "cosine",
    "ef_construction": 400,
    "ef_search": 1000,
    "max_neighbors": 32,
}


def validate_collection_name(name: str) -> None:
    """Require the documented ErgoStudy collection naming boundary."""
    if not COLLECTION_PATTERN.fullmatch(name):
        raise ValueError(f"Unsafe or unsupported collection name: {name!r}")


def validate_chroma_path(project_root: Path, chroma_path: Path) -> Path:
    """Require Chroma persistence to remain in project_root/chroma_db."""
    expected = (project_root / "chroma_db").resolve()
    actual = chroma_path.resolve()
    if actual != expected:
        raise ValueError(f"Chroma path must be exactly {expected.name}/ inside the project")
    return actual


def canonical_json_hash(value: Any) -> str:
    """Hash a portable JSON value using stable UTF-8 serialization."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def retrieval_text_hash(records: Iterable[dict[str, Any]]) -> str:
    """Hash the ordered record ID/retrieval-text logical contents."""
    return canonical_json_hash(
        [{"record_id": record["record_id"], "retrieval_text": record["retrieval_text"]} for record in records]
    )


def create_manifest(
    *,
    records: list[dict[str, Any]],
    corpus_sha256: str,
    selected_model: dict[str, Any],
    package_versions: dict[str, str],
) -> dict[str, Any]:
    """Create the deterministic logical-index manifest."""
    record_ids = [record["record_id"] for record in records]
    return {
        "manifest_version": "1.0.0",
        "collection_name": COLLECTION_NAME,
        "corpus_record_count": len(records),
        "corpus_sha256": corpus_sha256,
        "record_id_set_hash": stable_id_hash(sorted(record_ids)),
        "retrieval_text_hash": retrieval_text_hash(records),
        "metadata_projection_hash": projection_hash(records),
        "dataset_version": records[0]["dataset_version"],
        "selected_model_id": selected_model["model_id"],
        "selected_model_revision": selected_model["model_revision"],
        "embedding_dimension": int(selected_model["embedding_dimension"]),
        "preprocessing_configuration": {
            "config_id": selected_model["config_id"],
            "query_prefix": selected_model["query_prefix"],
            "document_prefix": selected_model["document_prefix"],
        },
        "distance_metric": "cosine",
        "index_configuration": {"hnsw": dict(INDEX_CONFIGURATION)},
        "normalized_embeddings": bool(selected_model["normalize_embeddings"]),
        "package_versions": dict(sorted(package_versions.items())),
    }


def _client(chroma_path: Path):
    import chromadb

    return chromadb.PersistentClient(path=str(chroma_path))


def close_client(client: Any) -> None:
    """Release Chroma resources explicitly, including Windows file handles."""
    close = getattr(client, "close", None)
    if callable(close):
        close()


def _collection_names(client: Any) -> set[str]:
    return {item.name if hasattr(item, "name") else str(item) for item in client.list_collections()}


def build_collection(
    *,
    project_root: Path,
    chroma_path: Path,
    records: list[dict[str, Any]],
    embeddings: np.ndarray,
    manifest: dict[str, Any],
    rebuild: bool,
    batch_size: int = 64,
) -> dict[str, Any]:
    """Create, safely rebuild, or verify the exact ErgoStudy collection."""
    validate_collection_name(COLLECTION_NAME)
    path = validate_chroma_path(project_root, chroma_path)
    path.mkdir(parents=True, exist_ok=True)
    if len(records) != len(embeddings):
        raise ValueError("Record and embedding counts differ")
    client = _client(path)
    names = _collection_names(client)
    if rebuild and COLLECTION_NAME in names:
        client.delete_collection(COLLECTION_NAME)
        names.remove(COLLECTION_NAME)
    if COLLECTION_NAME in names:
        collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
        if collection.count() != len(records):
            close_client(client)
            raise ValueError("Existing collection is incompatible; rerun with --rebuild")
        verification = verify_collection(collection, records, manifest)
        verification["action"] = "verified_existing"
        close_client(client)
        return verification

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"manifest_hash": canonical_json_hash(manifest)},
        configuration={"hnsw": dict(INDEX_CONFIGURATION)},
        embedding_function=None,
    )
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        collection.add(
            ids=[record["record_id"] for record in batch],
            documents=[record["retrieval_text"] for record in batch],
            metadatas=[project_metadata(record) for record in batch],
            embeddings=np.asarray(embeddings[start : start + batch_size], dtype=np.float32).tolist(),
        )
    verification = verify_collection(collection, records, manifest)
    verification["action"] = "rebuilt" if rebuild else "created"
    close_client(client)
    return verification


def verify_collection(collection: Any, records: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify IDs, documents, metadata, count, and manifest marker."""
    expected = {record["record_id"]: record for record in records}
    stored = collection.get(include=["documents", "metadatas"])
    ids = stored["ids"]
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate Chroma IDs found")
    if set(ids) != set(expected):
        raise AssertionError("Chroma record-ID set does not match the corpus")
    for index, record_id in enumerate(ids):
        if stored["documents"][index] != expected[record_id]["retrieval_text"]:
            raise AssertionError(f"Stored document differs for {record_id}")
        if stored["metadatas"][index] != project_metadata(expected[record_id]):
            raise AssertionError(f"Stored metadata differs for {record_id}")
    expected_manifest_hash = canonical_json_hash(manifest)
    if collection.metadata.get("manifest_hash") != expected_manifest_hash:
        raise AssertionError("Collection manifest marker differs")
    actual_hnsw = collection.configuration["hnsw"]
    for key, expected_value in INDEX_CONFIGURATION.items():
        if actual_hnsw.get(key) != expected_value:
            raise AssertionError(f"Collection HNSW configuration differs for {key}")
    return {
        "count": collection.count(),
        "missing_ids": 0,
        "duplicate_ids": 0,
        "documents_verified": len(ids),
        "metadata_verified": len(ids),
        "manifest_verified": True,
    }


def reopen_and_verify(
    *, project_root: Path, chroma_path: Path, records: list[dict[str, Any]], manifest: dict[str, Any]
) -> dict[str, Any]:
    """Open a fresh client and verify persisted logical contents."""
    path = validate_chroma_path(project_root, chroma_path)
    client = _client(path)
    collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
    result = verify_collection(collection, records, manifest)
    close_client(client)
    return result


def query_collection(chroma_path: Path, query_embeddings: np.ndarray, n_results: int = 10) -> dict[str, Any]:
    """Query using caller-provided embeddings only."""
    client = _client(chroma_path)
    collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
    result = collection.query(
        query_embeddings=np.asarray(query_embeddings, dtype=np.float32).tolist(),
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    close_client(client)
    return result


def validate_filter_results(records: list[dict[str, Any]], metadata: list[dict[str, Any]], where: dict[str, Any]) -> bool:
    """Check simple equality-filter results independently of Chroma."""
    del records
    key, expected = next(iter(where.items()))
    return all(item[key] == expected for item in metadata)
