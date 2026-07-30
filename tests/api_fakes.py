"""Shared fast fixtures for Stage 8 API tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient

from api.lifecycle import AppServices
from api.main import create_app
from api.settings import APISettings
from src.daily_planner import DailyPlanner
from src.deterministic_response import deterministic_grounded_response
from src.grounded_generator import GroundedResponseGenerator
from src.local_llm_client import LocalLLMResponse, OllamaUnavailableError
from src.sensor_adapter import SensorPlanAdapter
from tests.planner_fakes import FakeRetrievalService


ROOT = Path(__file__).resolve().parents[1]


SCHOOL_REQUEST = {
    "total_available_minutes": 150,
    "preferred_start_time": "16:00",
    "preferred_session_length": 40,
    "subjects": [
        {
            "name": "Mathematics",
            "topics": ["Equations and identities"],
            "difficulty": 4,
            "priority": 5,
            "workload": 4,
            "current_understanding": 2,
        },
        {
            "name": "Biology",
            "difficulty": 3,
            "priority": 3,
            "workload": 3,
            "current_understanding": 3,
        },
    ],
}


UNIVERSITY_REQUEST = {
    "total_available_minutes": 180,
    "preferred_start_time": "13:30",
    "preferred_session_length": 45,
    "subjects": [
        {
            "name": "Calculus 2",
            "topics": ["Integration"],
            "difficulty": 5,
            "priority": 5,
            "workload": 4,
            "current_understanding": 2,
        },
        {
            "name": "CS",
            "topics": ["Algorithms"],
            "difficulty": 4,
            "priority": 4,
            "workload": 5,
            "current_understanding": 3,
        },
    ],
}


VALID_SENSOR = {
    "sensor_enabled": True,
    "connection_status": "connected",
    "observation_status": "valid",
    "continuous_sitting_minutes": 65,
    "poor_posture_duration_minutes": 12,
    "posture_direction": "leaning_right",
    "pressure_imbalance_detected": True,
    "reading_age_seconds": 5,
    "current_session_order": 1,
    "elapsed_session_minutes": 20,
}


def component_statuses() -> dict[str, dict[str, str]]:
    return {
        "dataset": {"status": "ready", "detail": "Dataset ready."},
        "chroma_collection": {"status": "ready", "detail": "Chroma ready."},
        "embedding_model": {"status": "ready", "detail": "Embedding model ready."},
        "planner_config": {"status": "ready", "detail": "Planner config ready."},
        "sensor_policy": {"status": "ready", "detail": "Sensor policy ready."},
        "generation_config": {"status": "ready", "detail": "Generation config ready."},
        "services": {"status": "ready", "detail": "Services ready."},
    }


class GroundedModelClient:
    """Return the deterministic wording through the model-validation path."""

    def generate(self, **kwargs: Any) -> LocalLLMResponse:
        prompt = kwargs["user_prompt"]
        prefix = "Create the grounded response from this structured data. Return JSON only.\n"
        if prompt.startswith(prefix):
            context = json.loads(prompt[len(prefix) :])
        else:
            context = json.loads(prompt)["original_structured_data"]
        content = json.dumps(deterministic_grounded_response(context).to_dict())
        return LocalLLMResponse(content, 0.001, "qwen3:4b-instruct")


class CorrectingModelClient(GroundedModelClient):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, **kwargs: Any) -> LocalLLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LocalLLMResponse("{bad", 0.001, "qwen3:4b-instruct")
        return super().generate(**kwargs)


class InvalidModelClient:
    def generate(self, **kwargs: Any) -> LocalLLMResponse:
        return LocalLLMResponse("{bad", 0.001, "qwen3:4b-instruct")


class UnavailableModelClient:
    def generate(self, **kwargs: Any) -> LocalLLMResponse:
        raise OllamaUnavailableError("Local Ollama API unavailable")


class TimeoutModelClient:
    def generate(self, **kwargs: Any) -> LocalLLMResponse:
        raise OllamaUnavailableError("Explanation timeout reached")


def generator_builder(client: Any) -> Callable[[float], GroundedResponseGenerator]:
    return lambda timeout: GroundedResponseGenerator(ROOT, client=client)


def make_services(
    settings: APISettings,
    *,
    builder: Callable[[float], GroundedResponseGenerator] | None = None,
) -> AppServices:
    retrieval = FakeRetrievalService()
    return AppServices(
        settings=settings,
        components=component_statuses(),
        planner=DailyPlanner(ROOT, retrieval_service=retrieval),
        sensor_adapter=SensorPlanAdapter(ROOT),
        retrieval_service=retrieval,
        generator_builder=builder or generator_builder(UnavailableModelClient()),
    )


def make_client(
    *, builder: Callable[[float], GroundedResponseGenerator] | None = None
) -> TestClient:
    settings = APISettings.from_environment(ROOT)

    def factory(supplied: APISettings) -> AppServices:
        return make_services(supplied, builder=builder)

    return TestClient(create_app(settings=settings, service_factory=factory))


def generated_plan(client: TestClient, request: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post("/api/v1/plans", json=copy.deepcopy(request or SCHOOL_REQUEST))
    assert response.status_code == 200, response.text
    return response.json()["plan"]
