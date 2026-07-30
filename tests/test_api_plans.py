"""Deterministic planning endpoint tests."""

from __future__ import annotations

import copy
import unittest

from tests.api_fakes import SCHOOL_REQUEST, UNIVERSITY_REQUEST, make_client


class APIPlanTests(unittest.TestCase):
    def test_valid_school_plan(self) -> None:
        with make_client() as client:
            response = client.post("/api/v1/plans", json=SCHOOL_REQUEST)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan"]["total_planned_minutes"], 150)
        self.assertEqual(payload["api_version"], "v1")

    def test_valid_university_plan(self) -> None:
        with make_client() as client:
            response = client.post("/api/v1/plans", json=UNIVERSITY_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["plan"]["scheduled_subjects"]), 2)

    def test_subject_alias_is_preserved_and_resolved(self) -> None:
        request = copy.deepcopy(UNIVERSITY_REQUEST)
        request["subjects"] = [request["subjects"][1]]
        request["total_available_minutes"] = 60
        with make_client() as client:
            plan = client.post("/api/v1/plans", json=request).json()["plan"]
        self.assertEqual(plan["scheduled_subjects"][0]["subject"], "CS")

    def test_topics_are_optional(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["subjects"][0].pop("topics")
        with make_client() as client:
            response = client.post("/api/v1/plans", json=request)
        self.assertEqual(response.status_code, 200)

    def test_shortest_valid_window(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["total_available_minutes"] = 30
        request["subjects"] = [request["subjects"][0]]
        request.pop("preferred_session_length")
        with make_client() as client:
            plan = client.post("/api/v1/plans", json=request).json()["plan"]
        self.assertLessEqual(plan["total_planned_minutes"], 30)

    def test_plan_endpoint_never_builds_generator(self) -> None:
        def fail_builder(timeout: float):
            raise AssertionError("Ollama generator must not be built")
        with make_client(builder=fail_builder) as client:
            response = client.post("/api/v1/plans", json=SCHOOL_REQUEST)
        self.assertEqual(response.status_code, 200)

    def test_unknown_subject_reports_fallback(self) -> None:
        request = copy.deepcopy(SCHOOL_REQUEST)
        request["subjects"] = [{
            "name": "Quantum Basket Weaving", "difficulty": 3, "priority": 4,
            "workload": 3, "current_understanding": 2,
        }]
        request["total_available_minutes"] = 60
        with make_client() as client:
            payload = client.post("/api/v1/plans", json=request).json()
        self.assertTrue(payload["fallback"]["used"])
        self.assertEqual(payload["fallback"]["reason_codes"], ["KNOWLEDGE_FALLBACK"])


if __name__ == "__main__":
    unittest.main()
