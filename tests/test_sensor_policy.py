"""Tests for the configurable prototype sensor policy."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.sensor_policy import SensorPolicy, default_sensor_policy, load_sensor_policy


ROOT = Path(__file__).resolve().parents[1]


class SensorPolicyTests(unittest.TestCase):
    def test_default_policy_contains_expected_prototype_values(self) -> None:
        policy = default_sensor_policy(ROOT)
        self.assertEqual(policy.thresholds.long_continuous_sitting_minutes, 45)
        self.assertEqual(policy.thresholds.extended_continuous_sitting_minutes, 60)
        self.assertEqual(policy.adaptation.minimum_adapted_study_session_minutes, 20)
        self.assertIn("non-medical", policy.policy_status.lower())
        self.assertIn("hardware-team confirmation", policy.policy_status)

    def test_invalid_threshold_order_is_rejected(self) -> None:
        values = default_sensor_policy(ROOT).to_dict()
        values["thresholds"]["extended_continuous_sitting_minutes"] = 45
        with self.assertRaisesRegex(ValueError, "extended sitting threshold"):
            SensorPolicy.from_dict(values)

    def test_invalid_break_order_is_rejected(self) -> None:
        values = default_sensor_policy(ROOT).to_dict()
        values["adaptation"]["extended_movement_break_minutes"] = 4
        with self.assertRaisesRegex(ValueError, "extended movement break"):
            SensorPolicy.from_dict(values)

    def test_policy_loads_from_utf8_json(self) -> None:
        values = default_sensor_policy(ROOT).to_dict()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            self.assertEqual(load_sensor_policy(path), default_sensor_policy(ROOT))


if __name__ == "__main__":
    unittest.main()
