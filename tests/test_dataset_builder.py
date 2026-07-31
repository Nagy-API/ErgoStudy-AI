"""Tests for deterministic Stage 3 dataset construction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.dataset_builder import PROJECT_ROOT, build_dataset, slugify, stable_record_id
from src.dataset_io import file_sha256, read_jsonl


class DatasetBuilderTests(unittest.TestCase):
    def test_stable_id_generation(self) -> None:
        self.assertEqual(stable_record_id("topic", "Integration", "Mathematics"), "topic-integration-mathematics-v1")
        self.assertEqual(stable_record_id("alias", "Computer Science", "C++"), "alias-computer-science-c-v1")
        self.assertEqual(slugify("Anatomy & Physiology"), "anatomy-physiology")

    def test_repeated_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first_name, tempfile.TemporaryDirectory() as second_name:
            first = Path(first_name)
            second = Path(second_name)
            first_stats = build_dataset(PROJECT_ROOT, first)
            second_stats = build_dataset(PROJECT_ROOT, second)
            self.assertEqual(first_stats, second_stats)
            filenames = [
                "knowledge_corpus.jsonl", "subject_profiles.jsonl", "topic_profiles.jsonl",
                "study_strategies.jsonl", "session_templates.jsonl",
                "subject_aliases.jsonl", "retrieval_evaluation_queries.jsonl", "dataset_statistics.json",
            ]
            self.assertEqual(
                {name: file_sha256(first / name) for name in filenames},
                {name: file_sha256(second / name) for name in filenames},
            )

    def test_expected_corpus_sizes_and_separation(self) -> None:
        records = read_jsonl(PROJECT_ROOT / "data" / "processed" / "knowledge_corpus.jsonl")
        evaluations = read_jsonl(PROJECT_ROOT / "data" / "processed" / "retrieval_evaluation_queries.jsonl")
        self.assertGreaterEqual(len(records), 450)
        self.assertLessEqual(len(records), 735)
        self.assertGreaterEqual(len(evaluations), 80)
        self.assertLessEqual(len(evaluations), 120)
        self.assertNotIn("retrieval_evaluation_query", {record["document_family"] for record in records})


if __name__ == "__main__":
    unittest.main()
