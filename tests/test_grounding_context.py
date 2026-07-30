"""Tests for minimized, immutable grounding context construction."""

from __future__ import annotations

import copy
import json
import unittest

from src.grounding_context import build_grounding_context


def fixture() -> tuple[dict, dict]:
    request = {
        "total_available_minutes": 70,
        "subjects": [{"name": "Mathematics", "difficulty": 4, "priority": 5, "workload": 3, "current_understanding": 2}],
    }
    plan = {
        "total_available_minutes": 70,
        "total_study_minutes": 60,
        "total_break_minutes": 10,
        "scheduled_subjects": [{
            "subject": "Mathematics",
            "allocated_study_minutes": 60,
            "reason": "High priority.",
            "retrieved_record_ids": ["subject-mathematics-cross-level-v1"],
        }],
        "unscheduled_subjects": [],
        "sessions": [{
            "order": 1, "session_type": "study", "duration_minutes": 60,
            "subject": "Mathematics", "recommended_methods": ["practice"],
            "retrieved_record_ids": ["subject-mathematics-cross-level-v1"],
        }, {"order": 2, "session_type": "break", "duration_minutes": 10, "retrieved_record_ids": []}],
        "warnings": [],
    }
    return request, plan


class GroundingContextTests(unittest.TestCase):
    def test_keeps_only_relevant_record_summaries(self) -> None:
        request, plan = fixture()
        records = [
            {"record_id": "subject-mathematics-cross-level-v1", "title": "Mathematics", "document_family": "subject_profile", "retrieval_text": "Supported summary."},
            {"record_id": "subject-physics-cross-level-v1", "title": "Physics", "document_family": "subject_profile", "retrieval_text": "Unrelated summary."},
        ]
        context = build_grounding_context(request, plan, retrieved_record_summaries=records)
        self.assertEqual(
            [item["record_id"] for item in context["retrieved_record_summaries"]],
            ["subject-mathematics-cross-level-v1"],
        )
        self.assertNotIn("Unrelated summary", json.dumps(context))

    def test_record_summaries_are_bounded_and_keep_traceability_metadata(self) -> None:
        request, plan = fixture()
        records = [{
            "record_id": "subject-mathematics-cross-level-v1",
            "title": "Mathematics",
            "document_family": "subject_profile",
            "retrieval_text": "grounded " * 100,
            "source_ids": ["src-example-001"],
            "evidence_level": "source_descriptive",
            "reviewed": True,
        }]
        context = build_grounding_context(request, plan, retrieved_record_summaries=records)
        summary = context["retrieved_record_summaries"][0]
        self.assertLessEqual(len(summary["summary"]), 220)
        self.assertEqual(summary["source_ids"], ["src-example-001"])
        self.assertTrue(summary["reviewed"])

    def test_input_objects_are_not_mutated(self) -> None:
        request, plan = fixture()
        before = copy.deepcopy((request, plan))
        context = build_grounding_context(request, plan)
        context["final_plan"]["sessions"][0]["duration_minutes"] = 1
        self.assertEqual((request, plan), before)

    def test_rejects_evaluation_data_leakage(self) -> None:
        request, plan = fixture()
        request["expected_ids"] = ["secret"]
        with self.assertRaisesRegex(ValueError, "evaluation or internal-only"):
            build_grounding_context(request, plan)

    def test_rejects_nested_evaluation_data_leakage(self) -> None:
        request, plan = fixture()
        request["subjects"][0]["expected_record_ids"] = ["secret"]
        with self.assertRaisesRegex(ValueError, "evaluation or internal-only"):
            build_grounding_context(request, plan)

    def test_sensor_timeline_becomes_final_timeline(self) -> None:
        request, plan = fixture()
        sensor = {
            "sessions": [{"order": 1, "session_type": "study", "duration_minutes": 55, "subject": "Mathematics", "retrieved_record_ids": []}],
            "total_study_minutes": 55,
            "total_break_minutes": 0,
            "mode": "sensor",
            "severity": "normal",
            "triggers": [],
            "actions": [],
            "sensor_notice": "The adapted plan is active.",
            "adaptation_applied": True,
            "warnings": [],
        }
        context = build_grounding_context(request, plan, sensor_result=sensor)
        self.assertEqual(context["final_plan"]["sessions"][0]["duration_minutes"], 55)


if __name__ == "__main__":
    unittest.main()
