"""Run a local Stage 8 smoke check and generate Flutter-ready demo artifacts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app  # noqa: E402
from src.local_llm_client import OllamaUnavailableError  # noqa: E402


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
            "topics": ["Cells and organization"],
            "difficulty": 3,
            "priority": 3,
            "workload": 3,
            "current_understanding": 3,
        },
    ],
}

SENSOR_OBSERVATION = {
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


def checked_json(response) -> dict:
    if response.status_code != 200:
        raise RuntimeError(f"API smoke request failed with HTTP {response.status_code}: {response.text}")
    return response.json()


def run(real_ollama: bool) -> tuple[list[dict], list[dict]]:
    requests: list[dict] = []
    responses: list[dict] = []
    with TestClient(app) as client:
        health = checked_json(client.get("/api/v1/health"))
        readiness = checked_json(client.get("/api/v1/readiness"))
        requests.extend([
            {"example_id": "health", "method": "GET", "path": "/api/v1/health", "body": None},
            {"example_id": "readiness", "method": "GET", "path": "/api/v1/readiness", "body": None},
        ])
        responses.extend([
            {"example_id": "health", "response": health},
            {"example_id": "readiness", "response": readiness},
        ])

        plan_payload = checked_json(client.post("/api/v1/plans", json=SCHOOL_REQUEST))
        plan = plan_payload["plan"]
        adapt_body = {"plan": plan, "sensor_observation": SENSOR_OBSERVATION}
        full_body = copy.deepcopy(SCHOOL_REQUEST)
        full_body["sensor_observation"] = SENSOR_OBSERVATION
        adapt_payload = checked_json(client.post("/api/v1/plans/adapt", json=adapt_body))
        full_payload = checked_json(client.post("/api/v1/plans/full", json=full_body))
        requests.extend([
            {"example_id": "school_plan", "method": "POST", "path": "/api/v1/plans", "body": SCHOOL_REQUEST},
            {"example_id": "sensor_adaptation", "method": "POST", "path": "/api/v1/plans/adapt", "body": adapt_body},
            {"example_id": "full_deterministic", "method": "POST", "path": "/api/v1/plans/full", "body": full_body},
        ])
        responses.extend([
            {"example_id": "school_plan", "response": plan_payload},
            {"example_id": "sensor_adaptation", "response": adapt_payload},
            {"example_id": "full_deterministic", "response": full_payload},
        ])

        explanation_body = {
            "plan": plan,
            "adapted_plan": adapt_payload["adapted_plan"],
            "timeout_seconds": 30,
        }
        if real_ollama:
            explanation_payload = checked_json(
                client.post("/api/v1/explanations", json=explanation_body)
            )
        else:
            with patch(
                "api.dependencies.LocalLLMClient.generate",
                side_effect=OllamaUnavailableError("Local Ollama API unavailable"),
            ):
                explanation_payload = checked_json(
                    client.post("/api/v1/explanations", json=explanation_body)
                )
        requests.append({
            "example_id": "grounded_explanation",
            "method": "POST",
            "path": "/api/v1/explanations",
            "body": explanation_body,
        })
        responses.append({"example_id": "grounded_explanation", "response": explanation_payload})
    return requests, responses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-ollama",
        action="store_true",
        help="Make one real local explanation request instead of forcing the fallback.",
    )
    arguments = parser.parse_args()
    requests, responses = run(arguments.real_ollama)
    output_directory = PROJECT_ROOT / "data" / "processed"
    (output_directory / "api_demo_requests.json").write_text(
        json.dumps(requests, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_directory / "api_demo_responses.json").write_text(
        json.dumps(responses, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    latency = {
        item["example_id"]: item["response"].get(
            "processing_time_ms", item["response"].get("generation_latency_ms")
        )
        for item in responses
    }
    print(json.dumps({"examples": len(responses), "latency_ms": latency}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
