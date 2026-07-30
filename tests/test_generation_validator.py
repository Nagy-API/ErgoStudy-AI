"""Controlled grounding and safety attacks against the Stage 7 validator."""

from __future__ import annotations

import unittest

from src.generation_validator import validate_generated_response


def context() -> dict:
    return {
        "original_user_input": {"subjects": [{"name": "Mathematics"}, {"name": "Biology"}]},
        "final_plan": {
            "total_available_minutes": 105,
            "total_study_minutes": 90,
            "total_break_minutes": 10,
            "subject_allocations": [
                {"subject": "Mathematics", "allocated_minutes": 60, "reason": "High priority."},
                {"subject": "Biology", "allocated_minutes": 30, "reason": "Combined score."},
            ],
            "sessions": [
                {"order": 1, "session_type": "study", "duration_minutes": 60, "subject": "Mathematics"},
                {"order": 2, "session_type": "break", "duration_minutes": 10, "subject": None},
                {"order": 3, "session_type": "study", "duration_minutes": 30, "subject": "Biology"},
            ],
            "unscheduled_subjects": [],
            "warnings": ["5 minutes remain unallocated."],
        },
        "retrieved_record_summaries": [{"record_id": "subject-mathematics-cross-level-v1"}],
        "sensor_result": None,
    }


def valid_output() -> dict:
    return {
        "summary": "Today's plan covers Mathematics and Biology.",
        "allocation_explanations": [
            {"subject": "Mathematics", "allocated_minutes": 60, "reason": "This reflects its high priority."},
            {"subject": "Biology", "allocated_minutes": 30, "reason": "This reflects its combined score."},
        ],
        "session_messages": [
            {"session_order": 1, "message": "Study Mathematics for 60 minutes."},
            {"session_order": 2, "message": "Take the planned 10-minute break."},
            {"session_order": 3, "message": "Study Biology for 30 minutes."},
        ],
        "sensor_message": None,
        "unscheduled_message": None,
        "warnings": ["5 minutes remain unallocated."],
    }


class GenerationValidatorTests(unittest.TestCase):
    def assertRejected(self, values: str | dict, phrase: str) -> None:  # noqa: N802
        result = validate_generated_response(values, context())
        self.assertFalse(result.valid)
        self.assertIn(phrase, " ".join(result.errors))

    def test_accepts_correct_valid_output(self) -> None:
        self.assertTrue(validate_generated_response(valid_output(), context()).valid)

    def test_rejects_invalid_json(self) -> None:
        self.assertRejected("{invalid", "invalid JSON")

    def test_rejects_changed_allocated_duration(self) -> None:
        values = valid_output()
        values["allocation_explanations"][0]["allocated_minutes"] = 50
        self.assertRejected(values, "allocated minutes changed")

    def test_rejects_changed_study_duration(self) -> None:
        values = valid_output()
        values["session_messages"][0]["message"] = "Study Mathematics for 45 minutes."
        self.assertRejected(values, "study duration changed")

    def test_rejects_changed_break_duration(self) -> None:
        values = valid_output()
        values["session_messages"][1]["message"] = "Take a 15-minute break."
        self.assertRejected(values, "break duration changed")

    def test_rejects_invented_subject(self) -> None:
        values = valid_output()
        values["allocation_explanations"][0]["subject"] = "Physics"
        self.assertRejected(values, "exact scheduled subject")

    def test_rejects_invented_record_id(self) -> None:
        values = valid_output()
        values["summary"] += " See subject-invented-example-v1."
        self.assertRejected(values, "invented retrieved record IDs")

    def test_rejects_omitted_scheduled_subject(self) -> None:
        values = valid_output()
        values["allocation_explanations"].pop()
        self.assertRejected(values, "every exact scheduled subject")

    def test_rejects_wrong_session_reference(self) -> None:
        values = valid_output()
        values["session_messages"][2]["session_order"] = 4
        self.assertRejected(values, "every exact final session order")

    def test_rejects_medical_diagnostic_language(self) -> None:
        values = valid_output()
        values["summary"] = "This posture diagnoses a chronic pain condition."
        self.assertRejected(values, "unsupported medical language")

    def test_rejects_non_english_output(self) -> None:
        values = valid_output()
        values["summary"] = "El plan de Matemáticas está listo."
        self.assertRejected(values, "English-only")

    def test_rejects_unsupported_subject_fact(self) -> None:
        values = valid_output()
        values["summary"] = "Mathematics is a universal language."
        self.assertRejected(values, "unsupported subject-specific fact")

    def test_rejects_invented_user_input(self) -> None:
        values = valid_output()
        values["summary"] = "This plan prepares you for tomorrow's exam."
        self.assertRejected(values, "unsupported invented user input")

    def test_rejects_session_that_omits_exact_subject_name(self) -> None:
        values = valid_output()
        values["session_messages"][0]["message"] = "Begin with the first planned block."
        self.assertRejected(values, "omits its exact subject name")

    def test_rejects_changed_priority_claim(self) -> None:
        values = valid_output()
        values["allocation_explanations"][0]["reason"] = "This reflects its low priority."
        self.assertRejected(values, "unsupported priority claim")

    def test_rejects_changed_warning_duration(self) -> None:
        values = valid_output()
        values["warnings"] = ["10 minutes remain unallocated."]
        self.assertRejected(values, "warning text changes or invents a duration")

    def test_rejects_changed_sensor_duration(self) -> None:
        values = valid_output()
        values["sensor_message"] = "Take a 15-minute movement break."
        grounded = context()
        grounded["sensor_result"] = {
            "notice": "Take a short movement break.",
            "actions": [{"action": "insert_movement_break", "duration_minutes": 10}],
        }
        result = validate_generated_response(values, grounded)
        self.assertFalse(result.valid)
        self.assertIn("sensor duration", " ".join(result.errors))

    def test_rejects_invented_sensor_action_for_missing_data(self) -> None:
        values = valid_output()
        values["sensor_message"] = "Move now before the next block."
        grounded = context()
        grounded["sensor_result"] = {
            "notice": "No current sensor observation is available; the timer-based plan remains active.",
            "actions": [],
        }
        result = validate_generated_response(values, grounded)
        self.assertFalse(result.valid)
        self.assertIn("unsupported action", " ".join(result.errors))


if __name__ == "__main__":
    unittest.main()
