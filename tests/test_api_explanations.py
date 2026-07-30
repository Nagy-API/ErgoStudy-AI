"""Grounded explanation and fallback API tests."""

from __future__ import annotations

import copy
import unittest

from tests.api_fakes import (
    CorrectingModelClient,
    GroundedModelClient,
    InvalidModelClient,
    TimeoutModelClient,
    UnavailableModelClient,
    generated_plan,
    generator_builder,
    make_client,
)


class APIExplanationTests(unittest.TestCase):
    def test_valid_local_llm_explanation_mock(self) -> None:
        with make_client(builder=generator_builder(GroundedModelClient())) as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["generation_mode"], "local_llm")

    def test_corrected_response_reports_corrected_mode(self) -> None:
        model = CorrectingModelClient()
        with make_client(builder=generator_builder(model)) as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.json()["generation_mode"], "local_llm_corrected")
        self.assertEqual(response.json()["validation_status"], "corrected_valid")

    def test_ollama_timeout_returns_http_200_fallback(self) -> None:
        with make_client(builder=generator_builder(TimeoutModelClient())) as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fallback_reason_code"], "OLLAMA_TIMEOUT")

    def test_ollama_unavailable_returns_http_200_fallback(self) -> None:
        with make_client(builder=generator_builder(UnavailableModelClient())) as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fallback_reason_code"], "OLLAMA_UNAVAILABLE")

    def test_invalid_model_json_and_correction_failure_fall_back(self) -> None:
        with make_client(builder=generator_builder(InvalidModelClient())) as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fallback_reason_code"], "MODEL_VALIDATION_FAILED")
        self.assertEqual(response.json()["attempt_count"], 2)

    def test_explanation_does_not_mutate_plan_values(self) -> None:
        with make_client(builder=generator_builder(GroundedModelClient())) as client:
            plan = generated_plan(client)
            before = copy.deepcopy(plan)
            response = client.post("/api/v1/explanations", json={"plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(plan, before)
        allocations = response.json()["grounded_response"]["allocation_explanations"]
        self.assertEqual(
            {item["subject"]: item["allocated_minutes"] for item in allocations},
            {item["subject"]: item["allocated_study_minutes"] for item in plan["scheduled_subjects"]},
        )

    def test_timeout_override_must_fit_configured_safe_range(self) -> None:
        with make_client() as client:
            plan = generated_plan(client)
            response = client.post("/api/v1/explanations", json={"plan": plan, "timeout_seconds": 61})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
