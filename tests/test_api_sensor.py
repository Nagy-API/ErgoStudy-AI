"""Sensor adaptation endpoint tests."""

from __future__ import annotations

import copy
import unittest

from tests.api_fakes import VALID_SENSOR, generated_plan, make_client


class APISensorTests(unittest.TestCase):
    def test_sensor_disabled(self) -> None:
        with make_client() as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/plans/adapt", json={
                "plan": plan, "sensor_observation": {"sensor_enabled": False},
            })
        adapted = response.json()["adapted_plan"]
        self.assertFalse(adapted["adaptation_applied"])
        self.assertEqual(adapted["mode"], "non_sensor")

    def test_valid_sensor_adaptation(self) -> None:
        with make_client() as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/plans/adapt", json={
                "plan": plan, "sensor_observation": VALID_SENSOR,
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["adapted_plan"]["adaptation_applied"])

    def test_missing_sensor_observation_falls_back(self) -> None:
        with make_client() as client:
            plan = generated_plan(client)
            adapted = client.post("/api/v1/plans/adapt", json={"plan": plan}).json()["adapted_plan"]
        self.assertEqual(adapted["triggers"], ["missing_observation"])

    def test_stale_sensor_data_preserves_plan(self) -> None:
        observation = copy.deepcopy(VALID_SENSOR)
        observation["reading_age_seconds"] = 31
        with make_client() as client:
            plan = generated_plan(client)
            adapted = client.post("/api/v1/plans/adapt", json={
                "plan": plan, "sensor_observation": observation,
            }).json()["adapted_plan"]
        self.assertFalse(adapted["adaptation_applied"])
        self.assertIn("stale_observation", adapted["triggers"])

    def test_invalid_sensor_data_is_rejected(self) -> None:
        with make_client() as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/plans/adapt", json={
                "plan": plan, "sensor_observation": {"sensor_enabled": True, "reading_age_seconds": -1},
            })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "INVALID_REQUEST")

    def test_full_deterministic_pipeline_with_sensor(self) -> None:
        from tests.api_fakes import SCHOOL_REQUEST
        body = copy.deepcopy(SCHOOL_REQUEST)
        body["sensor_observation"] = VALID_SENSOR
        with make_client() as client:
            response = client.post("/api/v1/plans/full", json=body)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["adapted_plan"])


if __name__ == "__main__":
    unittest.main()
