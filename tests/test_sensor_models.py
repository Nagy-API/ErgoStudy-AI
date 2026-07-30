"""Tests for normalized sensor input and JSON-compatible output models."""

from __future__ import annotations

import unittest

from src.sensor_models import AdaptationAction, AdaptedStudyPlan, SensorObservation


class SensorModelTests(unittest.TestCase):
    def test_valid_observation_accepts_supported_normalized_fields(self) -> None:
        observation = SensorObservation.from_dict(
            {
                "sensor_enabled": True,
                "connection_status": "connected",
                "observation_status": "valid",
                "continuous_sitting_minutes": 50,
                "poor_posture_duration_minutes": 12,
                "posture_direction": "leaning_right",
                "pressure_imbalance_detected": True,
                "reading_age_seconds": 5,
                "current_session_order": 3,
                "elapsed_session_minutes": 25,
            }
        )
        self.assertEqual(observation.posture_direction, "leaning_right")
        self.assertEqual(observation.current_session_order, 3)

    def test_optional_fields_may_be_absent(self) -> None:
        observation = SensorObservation.from_dict({"sensor_enabled": False})
        self.assertIsNone(observation.connection_status)

    def test_invalid_enums_and_raw_numeric_shapes_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "posture_direction"):
            SensorObservation.from_dict(
                {"sensor_enabled": True, "posture_direction": "tilted_7_degrees"}
            )
        with self.assertRaisesRegex(ValueError, "continuous_sitting_minutes"):
            SensorObservation.from_dict(
                {"sensor_enabled": True, "continuous_sitting_minutes": -1}
            )
        with self.assertRaisesRegex(ValueError, "pressure_imbalance"):
            SensorObservation.from_dict(
                {"sensor_enabled": True, "pressure_imbalance_detected": 1}
            )

    def test_output_is_json_compatible(self) -> None:
        result = AdaptedStudyPlan(
            original_plan_id="plan-1",
            adapted_plan_id="adapted-1",
            adaptation_applied=False,
            mode="non_sensor",
            severity="normal",
            triggers=(),
            actions=(AdaptationAction("test_action", duration_minutes=5),),
            sessions=(),
            total_available_minutes=30,
            total_study_minutes=0,
            total_break_minutes=0,
            total_planned_minutes=0,
            unallocated_minutes=30,
            deferred_study_minutes=0,
            sensor_notice="Timer plan active.",
        ).to_dict()
        self.assertEqual(result["actions"][0], {"action": "test_action", "duration_minutes": 5})
        self.assertIsInstance(result["sessions"], list)


if __name__ == "__main__":
    unittest.main()
