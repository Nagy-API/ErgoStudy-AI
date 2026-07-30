"""Temporary-directory integration tests for safe persistent Chroma behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.chroma_store import (
    COLLECTION_NAME,
    build_collection,
    canonical_json_hash,
    close_client,
    create_manifest,
    reopen_and_verify,
    validate_chroma_path,
    validate_collection_name,
)


def records() -> list[dict]:
    base = {
        "evidence_level": "source_descriptive",
        "review_tier": "tier_b",
        "reviewed": True,
        "synthetic": False,
        "safety_scope": "none",
        "dataset_version": "1.0.0-prototype",
        "sensor_mode": "not_applicable",
        "source_ids": ["source-a"],
    }
    return [
        {**base, "record_id": "r-computing", "document_family": "subject_profile", "subject_family": "computing", "educational_level": ["school", "university"], "retrieval_text": "Computing study."},
        {**base, "record_id": "r-math", "document_family": "topic_profile", "subject_family": "mathematics", "educational_level": ["school"], "retrieval_text": "Mathematics topic.", "learning_task": "problem_solving", "cognitive_demand": "apply"},
    ]


class ChromaStoreTests(unittest.TestCase):
    def test_safe_collection_name_and_path_boundaries(self) -> None:
        validate_collection_name(COLLECTION_NAME)
        with self.assertRaises(ValueError):
            validate_collection_name("other")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            validate_chroma_path(root, root / "chroma_db")
            with self.assertRaises(ValueError):
                validate_chroma_path(root, root / "other")

    def test_manifest_hash_is_stable_and_sensitive(self) -> None:
        self.assertEqual(canonical_json_hash({"b": 2, "a": 1}), canonical_json_hash({"a": 1, "b": 2}))
        self.assertNotEqual(canonical_json_hash({"a": 1}), canonical_json_hash({"a": 2}))

    def test_persistence_ids_filters_and_safe_rebuild(self) -> None:
        import chromadb

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chroma_path = root / "chroma_db"
            rows = records()
            selected = {
                "model_id": "fake/model", "model_revision": "abc", "embedding_dimension": 3,
                "config_id": "fake", "query_prefix": "", "document_prefix": "", "normalize_embeddings": True,
            }
            manifest = create_manifest(records=rows, corpus_sha256="corpus", selected_model=selected, package_versions={"chromadb": "test"})
            embeddings = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)
            built = build_collection(project_root=root, chroma_path=chroma_path, records=rows, embeddings=embeddings, manifest=manifest, rebuild=False, batch_size=1)
            self.assertEqual(built["count"], 2)
            reopened = reopen_and_verify(project_root=root, chroma_path=chroma_path, records=rows, manifest=manifest)
            self.assertEqual(reopened["documents_verified"], 2)
            client = chromadb.PersistentClient(path=str(chroma_path))
            client.create_collection("unrelated-collection", embedding_function=None)
            collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
            self.assertEqual(set(collection.get(include=[])["ids"]), {"r-computing", "r-math"})
            filtered = collection.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=2, where={"supports_school": True}, include=["metadatas"])
            self.assertTrue(all(item["supports_school"] for item in filtered["metadatas"][0]))
            del collection, filtered
            close_client(client)
            build_collection(project_root=root, chroma_path=chroma_path, records=rows, embeddings=embeddings, manifest=manifest, rebuild=True, batch_size=2)
            final_client = chromadb.PersistentClient(path=str(chroma_path))
            names = {item.name if hasattr(item, "name") else str(item) for item in final_client.list_collections()}
            self.assertIn("unrelated-collection", names)
            self.assertIn(COLLECTION_NAME, names)
            close_client(final_client)


if __name__ == "__main__":
    unittest.main()
