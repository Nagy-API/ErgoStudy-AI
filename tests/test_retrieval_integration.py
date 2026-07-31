"""Integration checks against the existing persistent ErgoStudy collection."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.dataset_io import read_json, read_jsonl
from src.retriever import RetrievalService, intent_configuration
from src.retrieval_metrics import stable_id_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RetrievalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = RetrievalService(PROJECT_ROOT, configuration=intent_configuration(), device="cpu")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.service.close()

    def test_persistent_collection_returns_exact_subject(self) -> None:
        results = self.service.retrieve("I need a Mathematics course plan", top_k=5)
        self.assertEqual(results[0].record_id, "subject-mathematics-cross-level-v1")
        self.assertTrue(all(result.retrieval_text for result in results))

    def test_persistent_collection_metadata_filter(self) -> None:
        results = self.service.retrieve(
            "active recall study method",
            top_k=5,
            metadata_filters={"document_family": "study_strategy", "reviewed": True},
        )
        self.assertTrue(results)
        self.assertTrue(all(result.document_family == "study_strategy" for result in results))

    def test_reopening_preserves_deterministic_ids(self) -> None:
        expected = [item.record_id for item in self.service.retrieve("flashcards for vocabulary", top_k=5)]
        with RetrievalService(PROJECT_ROOT, configuration=intent_configuration(), device="cpu") as reopened:
            actual = [item.record_id for item in reopened.retrieve("flashcards for vocabulary", top_k=5)]
        self.assertEqual(actual, expected)

    def test_final_test_ids_are_absent_from_development_artifacts(self) -> None:
        processed = PROJECT_ROOT / "data" / "processed"
        split = read_json(processed / "retrieval_eval_split.json")
        development_ids = {row["query_id"] for row in read_jsonl(processed / "development_retrieval_results.jsonl")}
        final_ids = set(split["final_test_query_ids"])
        self.assertEqual(len(development_ids), len(split["development_query_ids"]))
        self.assertFalse(final_ids.intersection(development_ids))
        frozen = read_json(processed / "retrieval_config.json")
        self.assertTrue(frozen["frozen"])
        self.assertFalse(frozen["final_test_metrics_seen_during_selection"])
        self.assertEqual(frozen["development_query_id_hash"], stable_id_hash(split["development_query_ids"]))
        self.assertEqual(frozen["sealed_final_test_query_id_hash"], stable_id_hash(split["final_test_query_ids"]))

    def test_sealed_final_artifacts_match_frozen_configuration(self) -> None:
        processed = PROJECT_ROOT / "data" / "processed"
        split = read_json(processed / "retrieval_eval_split.json")
        frozen = read_json(processed / "retrieval_config.json")
        final_rows = read_jsonl(processed / "final_test_retrieval_results.jsonl")
        final_metrics = read_json(processed / "final_retrieval_metrics.json")
        self.assertEqual([row["query_id"] for row in final_rows], split["final_test_query_ids"])
        self.assertEqual(len(final_rows), len(split["final_test_query_ids"]))
        self.assertEqual(final_metrics["query_count"], len(split["final_test_query_ids"]))
        self.assertEqual(final_metrics["retrieval_configuration_hash"], frozen["retrieval_configuration_hash"])


if __name__ == "__main__":
    unittest.main()
