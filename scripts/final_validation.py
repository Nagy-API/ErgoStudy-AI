"""Run the final current-scope API scenarios and write reproducible evidence artifacts."""

from __future__ import annotations

import copy
import json
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app  # noqa: E402
from src.dataset_io import read_jsonl  # noqa: E402
from src.local_llm_client import OllamaUnavailableError  # noqa: E402


PROCESSED = PROJECT_ROOT / "data" / "processed"

SCHOOL = {
    "total_available_minutes": 150,
    "preferred_start_time": "16:00",
    "preferred_session_length": 40,
    "subjects": [
        {"name": "Mathematics", "topics": ["Equations and identities"], "difficulty": 4, "priority": 5, "workload": 4, "current_understanding": 2},
        {"name": "Biology", "topics": ["Cells and organization"], "difficulty": 3, "priority": 3, "workload": 3, "current_understanding": 3},
    ],
}
UNIVERSITY = {
    "total_available_minutes": 180,
    "preferred_start_time": "13:30",
    "preferred_session_length": 45,
    "subjects": [
        {"name": "Calculus 2", "topics": ["Integration"], "difficulty": 5, "priority": 5, "workload": 4, "current_understanding": 2},
        {"name": "CS", "topics": ["Algorithms"], "difficulty": 4, "priority": 4, "workload": 5, "current_understanding": 3},
    ],
}
SHORT = {
    "total_available_minutes": 30,
    "subjects": [
        {"name": "Chemistry", "difficulty": 5, "priority": 5, "workload": 4, "current_understanding": 1},
        {"name": "English Literature", "difficulty": 3, "priority": 2, "workload": 3, "current_understanding": 3},
    ],
}
UNKNOWN = {
    "total_available_minutes": 60,
    "preferred_session_length": 30,
    "subjects": [
        {"name": "Quantum Basket Weaving", "topics": ["Pattern review"], "difficulty": 3, "priority": 4, "workload": 3, "current_understanding": 2}
    ],
}


def _plan_checks(plan: dict, valid_record_ids: set[str]) -> dict[str, bool]:
    study = sum(item["duration_minutes"] for item in plan["sessions"] if item["session_type"] == "study")
    breaks = sum(item["duration_minutes"] for item in plan["sessions"] if item["session_type"] == "break")
    retrieved_ids = {
        record_id
        for item in plan["sessions"]
        for record_id in item.get("retrieved_record_ids", [])
    }
    return {
        "time_limit": plan["total_planned_minutes"] <= plan["total_available_minutes"],
        "positive_durations": all(item["duration_minutes"] > 0 for item in plan["sessions"]),
        "study_total": study == plan["total_study_minutes"],
        "break_total": breaks == plan["total_break_minutes"],
        "all_retrieved_ids_exist": retrieved_ids <= valid_record_ids,
    }


def _post(client: TestClient, path: str, body: dict) -> dict:
    response = client.post(path, json=body)
    if response.status_code != 200:
        raise AssertionError(f"{path} returned {response.status_code}: {response.text}")
    return response.json()


def main() -> int:
    corpus = read_jsonl(PROCESSED / "knowledge_corpus.jsonl")
    valid_ids = {record["record_id"] for record in corpus}
    if any("sensor" in json.dumps(record).casefold() for record in corpus):
        raise AssertionError("The active corpus contains obsolete sensor content")

    scenario_inputs = [
        {"id": "school_plan", "request": SCHOOL},
        {"id": "university_aliases_and_topics", "request": UNIVERSITY},
        {"id": "short_window_unscheduled", "request": SHORT},
        {"id": "unknown_subject_fallback", "request": UNKNOWN},
    ]
    outputs: list[dict] = []
    scenario_results: list[dict] = []
    latencies: list[float] = []

    with TestClient(app) as client:
        for scenario in scenario_inputs:
            started = time.perf_counter()
            payload = _post(client, "/api/v1/plans", scenario["request"])
            latencies.append((time.perf_counter() - started) * 1000)
            checks = _plan_checks(payload["plan"], valid_ids)
            if scenario["id"] == "short_window_unscheduled":
                checks["unscheduled_subject"] = bool(payload["plan"]["unscheduled_subjects"])
            if scenario["id"] == "unknown_subject_fallback":
                checks["knowledge_fallback"] = payload["fallback"]["used"]
            outputs.append({"id": scenario["id"], "response": payload})
            scenario_results.append({"id": scenario["id"], "checks": checks, "passed": all(checks.values())})

        first = _post(client, "/api/v1/plans", SCHOOL)["plan"]
        second = _post(client, "/api/v1/plans", SCHOOL)["plan"]
        repeat_checks = {
            "same_plan": first == second,
            "same_plan_id": first["plan_id"] == second["plan_id"],
            "normal_timer_breaks": any(item["session_type"] == "break" for item in first["sessions"]),
        }
        scenario_results.append({"id": "determinism_and_breaks", "checks": repeat_checks, "passed": all(repeat_checks.values())})

        full = _post(client, "/api/v1/plans/full", SCHOOL)
        full_checks = {
            "same_plan": full["original_plan"] == first,
            "same_sessions": full["final_sessions"] == first["sessions"],
        }
        outputs.append({"id": "full_plan", "response": full})
        scenario_results.append({"id": "full_plan", "checks": full_checks, "passed": all(full_checks.values())})

        with patch("api.dependencies.LocalLLMClient.generate", side_effect=OllamaUnavailableError("Local Ollama API unavailable")):
            explanation = _post(client, "/api/v1/explanations", {"plan": first})
        fallback_checks = {
            "http_success": explanation["generation_mode"] == "deterministic_fallback",
            "fallback_code": explanation["fallback_reason_code"] == "OLLAMA_UNAVAILABLE",
        }
        outputs.append({"id": "ollama_fallback", "response": explanation})
        scenario_results.append({"id": "ollama_fallback", "checks": fallback_checks, "passed": all(fallback_checks.values())})

        with patch("api.dependencies.LocalLLMClient.generate", side_effect=OllamaUnavailableError("Explanation timeout reached")):
            timeout = _post(client, "/api/v1/explanations", {"plan": first, "timeout_seconds": 1})
        timeout_checks = {"timeout_fallback": timeout["fallback_reason_code"] == "OLLAMA_TIMEOUT"}
        outputs.append({"id": "ollama_timeout", "response": timeout})
        scenario_results.append({"id": "ollama_timeout", "checks": timeout_checks, "passed": all(timeout_checks.values())})

        obsolete = copy.deepcopy(SCHOOL)
        obsolete["sensor_observation"] = {"sensor_enabled": True}
        obsolete_statuses = [
            client.post(path, json=obsolete).status_code
            for path in ("/api/v1/plans/full", "/api/v1/plans/full-with-explanation")
        ]
        removed_status = client.post("/api/v1/plans/adapt", json={}).status_code
        openapi = client.get("/openapi.json").json()
        expected_paths = {
            "/api/v1/health", "/api/v1/readiness", "/api/v1/plans", "/api/v1/plans/full",
            "/api/v1/explanations", "/api/v1/plans/full-with-explanation",
        }
        api_checks = {
            "obsolete_fields_rejected": obsolete_statuses == [422, 422],
            "adapt_route_removed": removed_status == 404,
            "exact_active_paths": set(openapi["paths"]) == expected_paths,
            "openapi_has_no_sensor_schema": "sensor" not in json.dumps(openapi).casefold(),
        }
        scenario_results.append({"id": "api_scope", "checks": api_checks, "passed": all(api_checks.values())})

    passed = all(item["passed"] for item in scenario_results)
    performance = {
        "operation": "/api/v1/plans",
        "sample_count": len(latencies),
        "average_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "minimum_ms": round(min(latencies), 3),
        "maximum_ms": round(max(latencies), 3),
    }
    report = {
        "passed": passed,
        "scenario_count": len(scenario_results),
        "passed_count": sum(item["passed"] for item in scenario_results),
        "failed_count": sum(not item["passed"] for item in scenario_results),
        "corpus_record_count": len(corpus),
        "scenarios": scenario_results,
    }
    (PROCESSED / "final_demo_inputs.json").write_text(json.dumps(scenario_inputs, indent=2) + "\n", encoding="utf-8")
    (PROCESSED / "final_demo_outputs.json").write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    (PROCESSED / "final_validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (PROCESSED / "final_performance_results.json").write_text(json.dumps(performance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": report, "performance": performance}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
