"""Tests for the stable Stage 7 deterministic fallback."""

from __future__ import annotations

import unittest

from src.deterministic_response import deterministic_grounded_response
from src.generation_validator import validate_generated_response


def context() -> dict:
    return {
        "original_user_input": {"subjects": [{"name": "Chemistry"}, {"name": "English Literature"}]},
        "final_plan": {
            "total_available_minutes": 30,
            "total_study_minutes": 25,
            "total_break_minutes": 5,
            "subject_allocations": [
                {"subject": "Chemistry", "allocated_minutes": 30, "reason": "High priority."}
            ],
            "sessions": [
                {"order": 1, "session_type": "break", "duration_minutes": 5, "subject": None, "recommended_methods": []},
                {"order": 2, "session_type": "study", "duration_minutes": 25, "subject": "Chemistry", "recommended_methods": ["practice"]},
            ],
            "unscheduled_subjects": [
                {"subject": "English Literature", "reason": "A useful session did not fit."}
            ],
            "warnings": ["5 study minutes were deferred."],
        },
        "retrieved_record_summaries": [],
        "sensor_result": {
            "notice": "Take a short movement break before the next study block.",
            "actions": [{"action": "insert_movement_break"}],
        },
    }


class DeterministicResponseTests(unittest.TestCase):
    def test_same_input_produces_same_output(self) -> None:
        first = deterministic_grounded_response(context()).to_dict()
        second = deterministic_grounded_response(context()).to_dict()
        self.assertEqual(first, second)

    def test_fallback_preserves_exact_values_and_validates(self) -> None:
        values = context()
        response = deterministic_grounded_response(values)
        self.assertEqual(response.allocation_explanations[0].allocated_minutes, 30)
        self.assertEqual([item.session_order for item in response.session_messages], [1, 2])
        self.assertIn("English Literature", response.unscheduled_message or "")
        self.assertTrue(validate_generated_response(response.to_dict(), values).valid)

    def test_fallback_sensor_language_is_non_medical(self) -> None:
        message = deterministic_grounded_response(context()).sensor_message or ""
        self.assertNotIn("diagnos", message.lower())
        self.assertNotIn("treatment", message.lower())


if __name__ == "__main__":
    unittest.main()
