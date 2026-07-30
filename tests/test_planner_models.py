"""Validation tests for planner input and output models."""

from __future__ import annotations

import unittest

from src.planner_models import DailyPlanRequest


def valid_input() -> dict:
    return {
        "total_available_minutes": 120,
        "preferred_start_time": "16:00",
        "preferred_session_length": 40,
        "subjects": [
            {
                "name": "Mathematics",
                "topics": ["Equations"],
                "difficulty": 4,
                "priority": 5,
                "workload": 4,
                "current_understanding": 2,
            }
        ],
    }


class PlannerModelTests(unittest.TestCase):
    def test_valid_request_is_immutable_and_typed(self) -> None:
        request = DailyPlanRequest.from_dict(valid_input())
        self.assertEqual(request.total_available_minutes, 120)
        self.assertEqual(request.subjects[0].topics, ("Equations",))

    def test_invalid_rating_is_rejected(self) -> None:
        values = valid_input()
        values["subjects"][0]["difficulty"] = 6
        with self.assertRaisesRegex(ValueError, "difficulty"):
            DailyPlanRequest.from_dict(values)

    def test_duplicate_subject_names_are_rejected_after_normalization(self) -> None:
        values = valid_input()
        duplicate = dict(values["subjects"][0])
        duplicate["name"] = "  mathematics  "
        values["subjects"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate subject"):
            DailyPlanRequest.from_dict(values)

    def test_boolean_is_not_accepted_as_integer(self) -> None:
        values = valid_input()
        values["subjects"][0]["priority"] = True
        with self.assertRaises(ValueError):
            DailyPlanRequest.from_dict(values)


if __name__ == "__main__":
    unittest.main()
