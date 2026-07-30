"""Rule and safety tests for deterministic sensor-aware plan adaptation."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from src.sensor_adapter import SensorPlanAdapter


ROOT = Path(__file__).resolve().parents[1]


def study(order: int, duration: int, subject: str = "Mathematics") -> dict:
    return {
        "order": order,
        "session_type": "study",
        "duration_minutes": duration,
        "reason": "Academic reason.",
        "start_time": None,
        "subject": subject,
        "topic": "Equations",
        "cognitive_demand": "high",
        "recommended_methods": ["worked examples"],
        "retrieved_record_ids": [f"record-{subject.lower()}"],
        "used_fallback": False,
    }


def timer_break(order: int, duration: int = 5) -> dict:
    return {
        "order": order,
        "session_type": "break",
        "duration_minutes": duration,
        "reason": "Scheduled short recovery break.",
        "start_time": None,
        "subject": None,
        "topic": None,
        "cognitive_demand": None,
        "recommended_methods": [],
        "retrieved_record_ids": [],
        "used_fallback": False,
    }


def plan(*sessions: dict, available: int | None = None) -> dict:
    planned = sum(item["duration_minutes"] for item in sessions)
    return {
        "plan_id": "plan-test",
        "total_available_minutes": available if available is not None else planned,
        "sessions": list(sessions),
    }


def observation(**overrides: object) -> dict:
    values: dict[str, object] = {
        "sensor_enabled": True,
        "connection_status": "connected",
        "observation_status": "valid",
        "continuous_sitting_minutes": 0,
        "poor_posture_duration_minutes": 0,
        "posture_direction": "upright",
        "pressure_imbalance_detected": False,
        "reading_age_seconds": 5,
    }
    values.update(overrides)
    return values


class SensorAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = SensorPlanAdapter(ROOT)
        self.base = plan(study(1, 40), timer_break(2), study(3, 35, "Physics"))

    def test_sensor_disabled_returns_original_timer_plan(self) -> None:
        result = self.adapter.adapt(self.base, {"sensor_enabled": False})
        self.assertEqual(result.mode, "non_sensor")
        self.assertFalse(result.adaptation_applied)
        self.assertEqual(list(result.sessions), self.base["sessions"])

    def test_connected_normal_and_unknown_posture_keep_plan(self) -> None:
        for direction in ("upright", "unknown"):
            with self.subTest(direction=direction):
                result = self.adapter.adapt(self.base, observation(posture_direction=direction))
                self.assertEqual(result.mode, "sensor")
                self.assertEqual(result.severity, "normal")
                self.assertFalse(result.adaptation_applied)

    def test_long_sitting_inserts_standard_break(self) -> None:
        original = plan(study(1, 40), available=45)
        result = self.adapter.adapt(original, observation(continuous_sitting_minutes=45))
        self.assertEqual(result.triggers, ("long_continuous_sitting",))
        self.assertEqual(result.sessions[0]["session_type"], "break")
        self.assertEqual(result.sessions[0]["duration_minutes"], 5)
        self.assertEqual(result.deferred_study_minutes, 0)

    def test_extended_sitting_uses_longer_break_and_reduces_next_session(self) -> None:
        original = plan(study(1, 40))
        result = self.adapter.adapt(original, observation(continuous_sitting_minutes=60))
        self.assertEqual(result.severity, "high")
        self.assertEqual(result.sessions[0]["duration_minutes"], 10)
        self.assertEqual(result.sessions[1]["duration_minutes"], 30)
        self.assertEqual(result.deferred_study_minutes, 10)
        self.assertIn("shorten_next_session", [item.action for item in result.actions])

    def test_each_supported_lean_adds_non_medical_reminder(self) -> None:
        for direction in (
            "leaning_left",
            "leaning_right",
            "leaning_forward",
            "leaning_backward",
        ):
            with self.subTest(direction=direction):
                result = self.adapter.adapt(
                    plan(study(1, 30), available=35),
                    observation(
                        posture_direction=direction,
                        poor_posture_duration_minutes=10,
                    ),
                )
                self.assertIn(direction, result.triggers)
                self.assertIn("show_posture_reminder", [item.action for item in result.actions])
                output_text = str(result.to_dict()).lower()
                for medical_word in ("diagnosis", "injury", "treatment", "disease"):
                    self.assertNotIn(medical_word, output_text)

    def test_pressure_imbalance_adds_one_break(self) -> None:
        result = self.adapter.adapt(
            plan(study(1, 30), available=35),
            observation(pressure_imbalance_detected=True),
        )
        self.assertEqual(result.triggers, ("pressure_imbalance",))
        self.assertTrue(result.adaptation_applied)
        self.assertEqual(sum(item["session_type"] == "break" for item in result.sessions), 1)

    def test_simultaneous_triggers_follow_severity_order_without_duplicate_breaks(self) -> None:
        result = self.adapter.adapt(
            plan(study(1, 40), available=50),
            observation(
                continuous_sitting_minutes=70,
                posture_direction="leaning_right",
                poor_posture_duration_minutes=15,
                pressure_imbalance_detected=True,
            ),
        )
        self.assertEqual(
            result.triggers,
            ("extended_continuous_sitting", "leaning_right", "pressure_imbalance"),
        )
        self.assertEqual(sum(item["session_type"] == "break" for item in result.sessions), 1)

    def test_bad_data_states_fall_back_calmly(self) -> None:
        cases = (
            observation(connection_status="disconnected"),
            observation(observation_status="missing"),
            observation(observation_status="stale"),
            observation(reading_age_seconds=31),
            observation(observation_status="invalid"),
        )
        for values in cases:
            with self.subTest(values=values):
                result = self.adapter.adapt(self.base, values)
                self.assertEqual(result.mode, "non_sensor")
                self.assertFalse(result.adaptation_applied)
                self.assertIn("timer-based plan remains active", result.sensor_notice)
                self.assertNotIn("danger", result.sensor_notice.lower())

    def test_completed_and_partial_current_sessions_are_not_modified(self) -> None:
        for elapsed in (20, 40):
            with self.subTest(elapsed=elapsed):
                result = self.adapter.adapt(
                    self.base,
                    observation(
                        continuous_sitting_minutes=50,
                        current_session_order=1,
                        elapsed_session_minutes=elapsed,
                    ),
                )
                self.assertEqual(result.sessions[0], self.base["sessions"][0])
                self.assertEqual(result.sessions[1], self.base["sessions"][1])
                self.assertEqual(result.sessions[1]["session_type"], "break")

    def test_existing_future_break_is_extended_instead_of_duplicated(self) -> None:
        result = self.adapter.adapt(
            self.base,
            observation(
                continuous_sitting_minutes=60,
                current_session_order=1,
                elapsed_session_minutes=40,
            ),
        )
        breaks = [item for item in result.sessions if item["session_type"] == "break"]
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0]["duration_minutes"], 10)

    def test_extra_break_shortens_future_session_and_reports_deferred_time(self) -> None:
        result = self.adapter.adapt(
            plan(study(1, 40)), observation(continuous_sitting_minutes=45)
        )
        self.assertEqual(result.total_planned_minutes, 40)
        self.assertEqual(result.total_study_minutes, 35)
        self.assertEqual(result.deferred_study_minutes, 5)
        self.assertIn("shorten_future_session", [item.action for item in result.actions])

    def test_insufficient_time_defers_whole_minimum_session(self) -> None:
        result = self.adapter.adapt(
            plan(study(1, 20)), observation(continuous_sitting_minutes=45)
        )
        self.assertEqual(result.deferred_study_minutes, 20)
        self.assertIn("defer_future_session", [item.action for item in result.actions])
        self.assertEqual(result.total_break_minutes, 5)

    def test_minimum_duration_time_limit_and_academic_fields_are_preserved(self) -> None:
        result = self.adapter.adapt(
            self.base, observation(continuous_sitting_minutes=60)
        )
        study_sessions = [item for item in result.sessions if item["session_type"] == "study"]
        self.assertTrue(all(item["duration_minutes"] >= 20 for item in study_sessions))
        self.assertLessEqual(result.total_planned_minutes, result.total_available_minutes)
        original_academic = [
            (
                item["subject"],
                item["topic"],
                item["reason"],
                item["recommended_methods"],
                item["retrieved_record_ids"],
            )
            for item in self.base["sessions"]
            if item["session_type"] == "study"
        ]
        adapted_academic = [
            (
                item["subject"],
                item["topic"],
                item["reason"],
                item["recommended_methods"],
                item["retrieved_record_ids"],
            )
            for item in study_sessions
        ]
        self.assertEqual(adapted_academic, original_academic)

    def test_repeat_is_identical_and_input_plan_is_not_mutated(self) -> None:
        before = copy.deepcopy(self.base)
        values = observation(
            continuous_sitting_minutes=65,
            posture_direction="leaning_left",
            poor_posture_duration_minutes=12,
        )
        first = self.adapter.adapt(self.base, values).to_dict()
        second = self.adapter.adapt(self.base, values).to_dict()
        self.assertEqual(first, second)
        self.assertEqual(self.base, before)

    def test_original_planner_warnings_are_preserved(self) -> None:
        original = copy.deepcopy(self.base)
        original["warnings"] = ["Original planner warning."]
        result = self.adapter.adapt(original, {"sensor_enabled": False})
        self.assertEqual(result.warnings, ("Original planner warning.",))

    def test_recent_posture_reminder_honors_cooldown(self) -> None:
        result = self.adapter.adapt(
            self.base,
            observation(
                posture_direction="leaning_forward",
                poor_posture_duration_minutes=12,
                minutes_since_last_reminder=5,
            ),
        )
        self.assertFalse(result.adaptation_applied)
        self.assertIn("recent posture reminder", result.sensor_notice.lower())


if __name__ == "__main__":
    unittest.main()
