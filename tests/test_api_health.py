"""Health, readiness, and OpenAPI tests for Stage 8."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.local_llm_client import OllamaUnavailableError
from tests.api_fakes import make_client


class APIHealthTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        with make_client() as client:
            response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("X-Request-ID", response.headers)

    @patch("api.main.LocalLLMClient.api_version", return_value="0.32.5")
    def test_readiness_with_ollama_available(self, mocked) -> None:
        with make_client() as client:
            payload = client.get("/api/v1/readiness").json()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["ollama"]["status"], "ready")

    @patch(
        "api.main.LocalLLMClient.api_version",
        side_effect=OllamaUnavailableError("offline"),
    )
    def test_readiness_with_ollama_unavailable_stays_ready(self, mocked) -> None:
        with make_client() as client:
            response = client.get("/api/v1/readiness")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ready"])
        self.assertEqual(response.json()["ollama"]["status"], "unavailable")

    def test_openapi_schema_contains_all_versioned_endpoints(self) -> None:
        with make_client() as client:
            schema = client.get("/openapi.json").json()
        expected = {
            "/api/v1/health",
            "/api/v1/readiness",
            "/api/v1/plans",
            "/api/v1/plans/adapt",
            "/api/v1/plans/full",
            "/api/v1/explanations",
            "/api/v1/plans/full-with-explanation",
        }
        self.assertTrue(expected.issubset(schema["paths"]))


if __name__ == "__main__":
    unittest.main()
