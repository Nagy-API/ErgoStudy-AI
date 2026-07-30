"""Tests for Chroma-safe scalar metadata and deterministic source handling."""

from __future__ import annotations

import unittest

from src.metadata_projection import PROJECTION_FIELDS, project_metadata, projection_hash


def sample_record() -> dict:
    return {
        "record_id": "subject-test-v1",
        "document_family": "subject_profile",
        "subject_family": "computing",
        "evidence_level": "source_descriptive",
        "review_tier": "tier_b",
        "reviewed": True,
        "synthetic": False,
        "safety_scope": "none",
        "dataset_version": "1.0.0-prototype",
        "educational_level": ["university", "school"],
        "source_ids": ["source-z", "source-a"],
        "retrieval_text": "Test retrieval text.",
    }


class MetadataProjectionTests(unittest.TestCase):
    def test_projection_has_complete_scalar_fields(self) -> None:
        metadata = project_metadata(sample_record())
        self.assertEqual(tuple(metadata), PROJECTION_FIELDS)
        self.assertTrue(all(isinstance(value, (str, int, float, bool)) for value in metadata.values()))
        self.assertTrue(metadata["supports_school"])
        self.assertTrue(metadata["supports_university"])
        self.assertEqual(metadata["learning_task"], "")

    def test_source_ids_json_is_sorted_and_deterministic(self) -> None:
        record = sample_record()
        first = project_metadata(record)
        record["source_ids"] = list(reversed(record["source_ids"]))
        second = project_metadata(record)
        self.assertEqual(first["source_ids_json"], '["source-a","source-z"]')
        self.assertEqual(first["source_ids_json"], second["source_ids_json"])
        self.assertEqual(first["primary_source_id"], "source-z")
        self.assertEqual(second["primary_source_id"], "source-a")

    def test_projection_hash_changes_with_metadata(self) -> None:
        first = sample_record()
        second = sample_record()
        second["reviewed"] = False
        self.assertNotEqual(projection_hash([first]), projection_hash([second]))


if __name__ == "__main__":
    unittest.main()
