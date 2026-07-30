"""Known-answer tests for ranking, metrics, and deterministic split logic."""

from __future__ import annotations

import unittest

import numpy as np

from src.retrieval_metrics import (
    aggregate_evaluation,
    deterministic_stratified_split,
    direct_cosine_top_k,
    score_query,
)


class RetrievalMetricTests(unittest.TestCase):
    def test_direct_cosine_ranking_and_stable_tie_break(self) -> None:
        documents = np.array([[1, 0], [0, 1], [1, 0]], dtype=np.float32)
        ids, scores = direct_cosine_top_k(np.array([[1, 0]], dtype=np.float32), documents, ["b", "c", "a"], 3)
        self.assertEqual(ids[0], ["a", "b", "c"])
        self.assertEqual(scores[0], [1.0, 1.0, 0.0])

    def test_record_metrics_known_example(self) -> None:
        query = {
            "query_id": "q1",
            "difficulty_type": "exact_name",
            "expected_relevant_record_ids": ["r2", "r4"],
            "expected_document_families": ["topic_profile"],
            "expected_subject_family": "computing",
        }
        records = [
            {"record_id": "r1", "document_family": "subject_profile", "subject_family": "computing"},
            {"record_id": "r2", "document_family": "topic_profile", "subject_family": "computing"},
            {"record_id": "r3", "document_family": "topic_profile", "subject_family": "mathematics"},
            {"record_id": "r4", "document_family": "topic_profile", "subject_family": "computing"},
        ]
        row = score_query(query, records)
        self.assertEqual(row["recall_at_1"], 0.0)
        self.assertEqual(row["recall_at_3"], 0.5)
        self.assertEqual(row["recall_at_5"], 1.0)
        self.assertEqual(row["mrr_at_10"], 0.5)
        self.assertAlmostEqual(row["ndcg_at_10"], (1 / np.log2(3) + 1 / np.log2(5)) / (1 + 1 / np.log2(3)))
        self.assertTrue(row["document_family_hit_at_5"])
        self.assertTrue(row["subject_family_hit_at_1"])

    def test_criteria_only_query_excludes_record_metrics(self) -> None:
        query = {
            "query_id": "q1", "difficulty_type": "ambiguous", "expected_document_families": ["subject_alias"],
            "expected_subject_family": None,
        }
        row = score_query(query, [])
        self.assertIsNone(row["recall_at_5"])
        result = aggregate_evaluation([row], [query])
        self.assertEqual(result["overall"]["queries_with_expected_record_ids"], 0)
        self.assertIsNone(result["overall"]["mrr_at_10"])

    def test_split_is_deterministic_disjoint_and_complete(self) -> None:
        queries = [
            {
                "query_id": f"q{i:02d}",
                "difficulty_type": ["exact_name", "ambiguous", "sensor_situation"][i % 3],
                "expected_subject_family": ["computing", "mathematics", None][i % 3],
                "expected_document_families": ["subject_profile"],
            }
            for i in range(12)
        ]
        first = deterministic_stratified_split(queries, development_count=8, seed=42)
        second = deterministic_stratified_split(queries, development_count=8, seed=42)
        self.assertEqual(first, second)
        development, final = first
        self.assertEqual((len(development), len(final)), (8, 4))
        self.assertFalse(set(development).intersection(final))
        self.assertEqual(set(development).union(final), {q["query_id"] for q in queries})


if __name__ == "__main__":
    unittest.main()
