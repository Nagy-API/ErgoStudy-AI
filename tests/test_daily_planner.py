"""End-to-end planner tests with deterministic local retrieval doubles."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.daily_planner import DailyPlanner
from tests.planner_fakes import FakeRetrievalService


ROOT = Path(__file__).resolve().parents[1]


def subject(name: str, *, priority: int = 3, understanding: int = 3, topics: list[str] | None = None) -> dict:
    return {
        "name": name,
        "topics": topics or [],
        "difficulty": 4,
        "priority": priority,
        "workload": 3,
        "current_understanding": understanding,
    }


class DailyPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = DailyPlanner(ROOT, retrieval_service=FakeRetrievalService())

    def test_same_input_produces_identical_plan_and_id(self) -> None:
        values = {"total_available_minutes": 120, "subjects": [subject("Mathematics", topics=["Equations"])]}
        first = self.planner.plan(values).to_dict()
        second = self.planner.plan(values).to_dict()
        self.assertEqual(first, second)

    def test_total_time_never_exceeded_and_durations_are_positive(self) -> None:
        for total in (30, 45, 90, 240, 720):
            values = {
                "total_available_minutes": total,
                "subjects": [subject("Mathematics", priority=5, understanding=1), subject("Unknown Studies")],
            }
            plan = self.planner.plan(values)
            self.assertLessEqual(plan.total_planned_minutes, total)
            self.assertTrue(all(item.duration_minutes > 0 for item in plan.sessions))
            study = [item for item in plan.sessions if item.session_type == "study"]
            self.assertTrue(all(20 <= item.duration_minutes <= 60 for item in study))

    def test_insufficient_time_reports_unscheduled_subjects(self) -> None:
        values = {
            "total_available_minutes": 30,
            "subjects": [subject("Mathematics", priority=5), subject("Computer Science", priority=2)],
        }
        plan = self.planner.plan(values)
        self.assertEqual(len(plan.scheduled_subjects), 1)
        self.assertEqual(plan.unscheduled_subjects[0].subject, "Computer Science")
        self.assertIn("minimum useful", plan.unscheduled_subjects[0].reason)

    def test_alias_topics_and_unknown_fallback(self) -> None:
        values = {
            "total_available_minutes": 120,
            "subjects": [subject("CS", topics=["Algorithms"]), subject("Unknown Studies")],
        }
        plan = self.planner.plan(values)
        cs = next(item for item in plan.scheduled_subjects if item.subject == "CS")
        unknown = next(item for item in plan.scheduled_subjects if item.subject == "Unknown Studies")
        self.assertEqual(cs.canonical_subject, "Computer Science")
        self.assertTrue(unknown.used_fallback)
        self.assertTrue(any("no reliable subject profile" in value for value in plan.warnings))

    def test_start_times_and_json_compatible_lists(self) -> None:
        values = {
            "total_available_minutes": 90,
            "preferred_start_time": "08:15",
            "subjects": [subject("Mathematics")],
        }
        output = self.planner.plan(values).to_dict()
        self.assertEqual(output["sessions"][0]["start_time"], "08:15")
        self.assertIsInstance(output["sessions"][0]["recommended_methods"], list)

    def test_missing_start_time_returns_null_times(self) -> None:
        plan = self.planner.plan({
            "total_available_minutes": 60,
            "subjects": [subject("Mathematics")],
        })
        self.assertTrue(all(item.start_time is None for item in plan.sessions))

    def test_invalid_total_and_preferred_session_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "total_available"):
            self.planner.plan({"total_available_minutes": 29, "subjects": [subject("Mathematics")]})
        with self.assertRaisesRegex(ValueError, "preferred_session"):
            self.planner.plan({
                "total_available_minutes": 90,
                "preferred_session_length": 10,
                "subjects": [subject("Mathematics")],
            })
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            self.planner.plan({
                "total_available_minutes": 90,
                "preferred_start_time": "9pm",
                "subjects": [subject("Mathematics")],
            })


if __name__ == "__main__":
    unittest.main()
