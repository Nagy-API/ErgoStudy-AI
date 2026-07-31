"""Strict request validation and safe error-contract tests."""

from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from tests.api_fakes import SCHOOL_REQUEST, make_client


class APIValidationTests(unittest.TestCase):
    def assert_invalid(self, request: dict) -> dict:
        with make_client() as client:
            response = client.post("/api/v1/plans", json=request)
        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "INVALID_REQUEST")
        self.assertIn("request_id", payload)
        return payload

    def test_invalid_available_time(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["total_available_minutes"] = 29
        self.assert_invalid(request)

    def test_invalid_rating(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["subjects"][0]["priority"] = 6
        self.assert_invalid(request)

    def test_empty_subject_name(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["subjects"][0]["name"] = "   "
        self.assert_invalid(request)

    def test_unknown_fields_are_rejected(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["cloud_api_key"] = "not-accepted"
        payload = self.assert_invalid(request)
        self.assertIn("cloud_api_key", json.dumps(payload))

    def test_obsolete_sensor_fields_are_rejected(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["sensor_observation"] = {"sensor_enabled": True}
        with make_client() as client:
            for path in ("/api/v1/plans/full", "/api/v1/plans/full-with-explanation"):
                response = client.post(path, json=request)
                self.assertEqual(response.status_code, 422)
                self.assertIn("sensor_observation", response.text)

    def test_removed_adaptation_endpoint_returns_404(self) -> None:
        with make_client() as client:
            response = client.post("/api/v1/plans/adapt", json={})
        self.assertEqual(response.status_code, 404)

    def test_invalid_clock_time(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["preferred_start_time"] = "25:00"
        self.assert_invalid(request)

    def test_errors_do_not_expose_local_paths(self) -> None:
        payload = self.assert_invalid({"subjects": []})
        serialized = json.dumps(payload).casefold()
        self.assertNotIn("conferece_sbs", serialized)
        self.assertNotIn("users\\", serialized)
        self.assertNotIn("traceback", serialized)

    @patch("api.main.LocalLLMClient.api_version", return_value="0.32.5")
    def test_success_responses_do_not_expose_local_paths(self, mocked) -> None:
        with make_client() as client:
            responses = [
                client.get("/api/v1/health").json(),
                client.get("/api/v1/readiness").json(),
                client.post("/api/v1/plans", json=SCHOOL_REQUEST).json(),
            ]
        serialized = json.dumps(responses).casefold()
        self.assertNotIn("conferece_sbs", serialized)
        self.assertNotIn("users\\", serialized)
        self.assertNotIn("huggingface", serialized)
        self.assertNotIn("traceback", serialized)


if __name__ == "__main__":
    unittest.main()
