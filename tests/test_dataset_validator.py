"""Tests for Stage 3 validation rules and fixtures."""

from __future__ import annotations

import copy
import unittest

from src.dataset_builder import DATASET_VERSION, PROJECT_ROOT
from src.dataset_io import read_jsonl, read_source_catalog
from src.dataset_validator import (
    detect_near_duplicates,
    find_broken_parent_references,
    find_broken_source_references,
    find_duplicate_retrieval_texts,
    find_evaluation_leaks,
    find_sensor_safety_errors,
    find_source_role_errors,
    validate_dataset,
    validate_record,
)


def valid_subject_fixture() -> dict[str, object]:
    return {
        "record_id": "subject-test-subject-cross-level-v1",
        "document_family": "subject_profile",
        "title": "Test subject profile",
        "retrieval_text": "Subject profile: Test Subject uses reading, explanation, and checked practice. This fixture has enough standalone retrieval text for validation.",
        "educational_level": ["school", "university"],
        "subject_family": "general",
        "subject_name": "Test Subject",
        "aliases": ["Test Studies"],
        "typical_learning_activities": ["read and explain", "practise and check"],
        "characteristics": ["theory", "practice"],
        "evidence_level": "source_descriptive",
        "source_ids": ["src-learn-guide-004"],
        "safety_scope": "none",
        "synthetic": False,
        "reviewed": True,
        "review_tier": "tier_b",
        "dataset_version": DATASET_VERSION,
    }


class DatasetValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = read_jsonl(PROJECT_ROOT / "data" / "processed" / "knowledge_corpus.jsonl")
        cls.evaluations = read_jsonl(PROJECT_ROOT / "data" / "processed" / "retrieval_evaluation_queries.jsonl")
        cls.catalog_ids = {row["source_id"] for row in read_source_catalog(PROJECT_ROOT / "data" / "sources" / "source_catalog.csv")}

    def test_valid_fixture_acceptance(self) -> None:
        self.assertEqual(validate_record(valid_subject_fixture()), [])

    def test_required_and_conditional_field_rejection(self) -> None:
        fixture = valid_subject_fixture()
        del fixture["subject_name"]
        errors = validate_record(fixture)
        self.assertTrue(any("subject_name" in error for error in errors))

    def test_invalid_enumeration_rejection(self) -> None:
        fixture = valid_subject_fixture()
        fixture["subject_family"] = "unsupported_family"
        self.assertTrue(any("subject_family" in error for error in validate_record(fixture)))

    def test_source_reference_validation(self) -> None:
        fixture = valid_subject_fixture()
        fixture["source_ids"] = ["src-does-not-exist-999"]
        self.assertEqual(find_broken_source_references([fixture], self.catalog_ids), ["src-does-not-exist-999"])
        self.assertEqual(find_broken_source_references(self.corpus, self.catalog_ids), [])

    def test_subject_framework_cannot_be_effectiveness_evidence(self) -> None:
        fixture = valid_subject_fixture()
        fixture["source_ids"] = ["src-law-aba-023"]
        fixture["evidence_level"] = "moderate"
        roles = {"src-law-aba-023": "subject_framework"}
        self.assertTrue(find_source_role_errors([fixture], roles))
        fixture["evidence_level"] = "source_descriptive"
        self.assertEqual(find_source_role_errors([fixture], roles), [])

    def test_parent_reference_validation(self) -> None:
        parent = valid_subject_fixture()
        alias = copy.deepcopy(next(record for record in self.corpus if record["document_family"] == "subject_alias"))
        alias["record_id"] = "alias-test-subject-variant-v1"
        alias["derived_from_record_id"] = parent["record_id"]
        alias["derived_from_record_ids"] = [parent["record_id"]]
        alias["canonical_subject_record_id"] = parent["record_id"]
        alias["related_subject_record_ids"] = [parent["record_id"]]
        self.assertEqual(find_broken_parent_references([parent, alias]), [])
        alias["derived_from_record_ids"] = ["subject-missing-parent-v1"]
        self.assertTrue(find_broken_parent_references([parent, alias]))

    def test_duplicate_and_near_duplicate_detection(self) -> None:
        first = valid_subject_fixture()
        second = copy.deepcopy(first)
        second["record_id"] = "subject-second-test-cross-level-v1"
        self.assertEqual(len(find_duplicate_retrieval_texts([first, second])), 1)
        second["retrieval_text"] += " Additional."
        self.assertTrue(detect_near_duplicates([first, second], threshold=0.80))

    def test_sensor_safety_validation(self) -> None:
        valid_sensor = copy.deepcopy(next(record for record in self.corpus if record["document_family"] == "sensor_intervention"))
        self.assertEqual(find_sensor_safety_errors([valid_sensor]), [])
        valid_sensor["hardware_confirmation_required"] = False
        valid_sensor["retrieval_text"] = "The sensor proves injury and should diagnose the user."
        self.assertEqual(find_sensor_safety_errors([valid_sensor]), [valid_sensor["record_id"]])

    def test_evaluation_corpus_separation(self) -> None:
        self.assertEqual(find_evaluation_leaks(self.corpus, self.evaluations), [])
        leaked = copy.deepcopy(self.evaluations[0])
        leaked["query_text"] = self.corpus[0]["retrieval_text"]
        self.assertEqual(find_evaluation_leaks(self.corpus, [leaked]), [leaked["record_id"]])

    def test_complete_processed_dataset_is_valid(self) -> None:
        report = validate_dataset(PROJECT_ROOT, check_determinism=False, write_report=False)
        self.assertTrue(report["passed"], report["errors"])


if __name__ == "__main__":
    unittest.main()
