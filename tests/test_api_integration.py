"""Cross-endpoint, concurrency, and regression tests for Stage 8."""

from __future__ import annotations

import concurrent.futures
import copy
import unittest

from tests.api_fakes import (
    SCHOOL_REQUEST,
    TimeoutModelClient,
    VALID_SENSOR,
    generator_builder,
    make_client,
)


class APIIntegrationTests(unittest.TestCase):
    def test_full_without_sensor_returns_original_timeline(self) -> None:
        with make_client() as client:
            payload = client.post("/api/v1/plans/full", json=SCHOOL_REQUEST).json()
        self.assertIsNone(payload["adapted_plan"])
        self.assertEqual(payload["final_sessions"], payload["original_plan"]["sessions"])

    def test_demo_full_pipeline_keeps_plan_when_explanation_falls_back(self) -> None:
        body = copy.deepcopy(SCHOOL_REQUEST)
        body["sensor_observation"] = VALID_SENSOR
        with make_client(builder=generator_builder(TimeoutModelClient())) as client:
            response = client.post("/api/v1/plans/full-with-explanation", json=body)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["original_plan"]["sessions"])
        self.assertEqual(payload["explanation"]["generation_mode"], "deterministic_fallback")

    def test_concurrent_deterministic_plan_requests(self) -> None:
        with make_client() as client:
            def submit(_: int) -> tuple[int, str]:
                response = client.post("/api/v1/plans", json=SCHOOL_REQUEST)
                return response.status_code, response.json()["plan"]["plan_id"]

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(submit, range(8)))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(len({plan_id for _, plan_id in results}), 1)

    def test_existing_planner_and_sensor_outputs_are_unchanged(self) -> None:
        body = copy.deepcopy(SCHOOL_REQUEST)
        body["sensor_observation"] = VALID_SENSOR
        with make_client() as client:
            standalone = client.post("/api/v1/plans", json=SCHOOL_REQUEST).json()["plan"]
            full = client.post("/api/v1/plans/full", json=body).json()
            adapted = client.post("/api/v1/plans/adapt", json={
                "plan": standalone, "sensor_observation": VALID_SENSOR,
            }).json()["adapted_plan"]
        self.assertEqual(standalone, full["original_plan"])
        self.assertEqual(adapted, full["adapted_plan"])


if __name__ == "__main__":
    unittest.main()
