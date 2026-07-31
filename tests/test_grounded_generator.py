"""Tests for local generation, correction, and fallback orchestration."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from src.grounded_generator import GroundedResponseGenerator
from src.local_llm_client import LocalLLMResponse, OllamaUnavailableError


ROOT = Path(__file__).resolve().parents[1]


def request_and_plan() -> tuple[dict, dict]:
    request = {
        "total_available_minutes": 70,
        "subjects": [{"name": "Mathematics", "difficulty": 4, "priority": 5, "workload": 3, "current_understanding": 2}],
    }
    plan = {
        "total_available_minutes": 70,
        "total_study_minutes": 60,
        "total_break_minutes": 10,
        "scheduled_subjects": [{"subject": "Mathematics", "allocated_study_minutes": 60, "reason": "High priority.", "retrieved_record_ids": []}],
        "unscheduled_subjects": [],
        "sessions": [
            {"order": 1, "session_type": "study", "duration_minutes": 60, "subject": "Mathematics", "recommended_methods": ["practice"], "retrieved_record_ids": []},
            {"order": 2, "session_type": "break", "duration_minutes": 10, "subject": None, "recommended_methods": [], "retrieved_record_ids": []},
        ],
        "warnings": [],
    }
    return request, plan


def valid_json() -> str:
    return json.dumps(
        {
            "summary": "Today's plan has one scheduled subject.",
            "allocation_explanations": [{"subject": "Mathematics", "allocated_minutes": 60, "reason": "This reflects its high priority."}],
            "session_messages": [
                {"session_order": 1, "message": "Study Mathematics for 60 minutes."},
                {"session_order": 2, "message": "Take the planned 10-minute break."},
            ],
            "unscheduled_message": None,
            "warnings": [],
        }
    )


class SequenceClient:
    def __init__(self, values: list[str]) -> None:
        self.values = values
        self.prompts: list[str] = []

    def generate(self, **kwargs) -> LocalLLMResponse:
        self.prompts.append(kwargs["user_prompt"])
        value = self.values.pop(0)
        return LocalLLMResponse(value, 0.01, "qwen3:4b-instruct")


class UnavailableClient:
    def generate(self, **kwargs) -> LocalLLMResponse:
        raise OllamaUnavailableError("Local Ollama API unavailable")


class GroundedGeneratorTests(unittest.TestCase):
    def test_valid_first_response_uses_local_llm_mode(self) -> None:
        client = SequenceClient([valid_json()])
        request, plan = request_and_plan()
        result = GroundedResponseGenerator(ROOT, client=client).generate(request, plan)
        self.assertEqual(result.generation_mode, "local_llm")
        self.assertEqual(result.attempt_count, 1)

    def test_one_retry_corrects_invalid_response(self) -> None:
        client = SequenceClient(["{bad", valid_json()])
        request, plan = request_and_plan()
        result = GroundedResponseGenerator(ROOT, client=client).generate(request, plan)
        self.assertEqual(result.generation_mode, "local_llm_corrected")
        self.assertEqual(len(client.prompts), 2)
        self.assertIn("validation_errors", client.prompts[1])
        self.assertIn("required_schema", client.prompts[1])

    def test_second_invalid_response_uses_deterministic_fallback(self) -> None:
        client = SequenceClient(["{bad", "{still bad"])
        request, plan = request_and_plan()
        result = GroundedResponseGenerator(ROOT, client=client).generate(request, plan)
        self.assertEqual(result.generation_mode, "deterministic_fallback")
        self.assertEqual(result.attempt_count, 2)

    def test_ollama_unavailable_uses_fallback_without_failing(self) -> None:
        request, plan = request_and_plan()
        result = GroundedResponseGenerator(ROOT, client=UnavailableClient()).generate(request, plan)
        self.assertEqual(result.generation_mode, "deterministic_fallback")
        self.assertEqual(result.attempt_count, 0)

    def test_inputs_are_not_mutated(self) -> None:
        request, plan = request_and_plan()
        before = copy.deepcopy((request, plan))
        GroundedResponseGenerator(ROOT, client=SequenceClient([valid_json()])).generate(request, plan)
        self.assertEqual((request, plan), before)

    def test_optional_record_inputs_are_not_mutated(self) -> None:
        request, plan = request_and_plan()
        records = [{
            "record_id": "subject-mathematics-cross-level-v1",
            "title": "Mathematics",
            "document_family": "subject_profile",
            "summary": "A supplied record summary.",
        }]
        before = copy.deepcopy((request, plan, records))
        GroundedResponseGenerator(ROOT, client=UnavailableClient()).generate(
            request,
            plan,
            retrieved_record_summaries=records,
        )
        self.assertEqual((request, plan, records), before)


if __name__ == "__main__":
    unittest.main()
