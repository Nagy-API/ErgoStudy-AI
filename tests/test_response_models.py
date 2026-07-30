"""Tests for strict Stage 7 response models."""

from __future__ import annotations

import unittest

from src.response_models import GroundedResponse


def valid_values() -> dict:
    return {
        "summary": "Today's plan has one study block.",
        "allocation_explanations": [
            {"subject": "Mathematics", "allocated_minutes": 60, "reason": "High priority."}
        ],
        "session_messages": [{"session_order": 1, "message": "Study Mathematics."}],
        "sensor_message": None,
        "unscheduled_message": None,
        "warnings": [],
    }


class ResponseModelTests(unittest.TestCase):
    def test_parses_and_serializes_valid_response(self) -> None:
        model = GroundedResponse.from_dict(valid_values())
        self.assertEqual(model.to_dict(), valid_values())

    def test_rejects_extra_fields(self) -> None:
        values = valid_values()
        values["extra"] = "not allowed"
        with self.assertRaisesRegex(ValueError, "extra fields"):
            GroundedResponse.from_dict(values)

    def test_rejects_wrong_field_types(self) -> None:
        values = valid_values()
        values["session_messages"][0]["session_order"] = "1"
        with self.assertRaisesRegex(ValueError, "positive integer"):
            GroundedResponse.from_dict(values)


if __name__ == "__main__":
    unittest.main()
