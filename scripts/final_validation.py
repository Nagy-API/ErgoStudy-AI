"""Run the final ErgoStudy end-to-end scenarios and local API benchmarks."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import create_app  # noqa: E402
from api.settings import APISettings  # noqa: E402
from src.grounded_generator import GroundedResponseGenerator  # noqa: E402
from src.local_llm_client import OllamaUnavailableError  # noqa: E402


PROJECT_VERSION = "1.0.0-prototype"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INPUTS_PATH = PROCESSED_DIR / "final_demo_inputs.json"
OUTPUTS_PATH = PROCESSED_DIR / "final_demo_outputs.json"
EVALUATION_PATH = PROCESSED_DIR / "final_evaluation_results.json"
PERFORMANCE_PATH = PROCESSED_DIR / "final_performance_results.json"
VALIDATION_PATH = PROCESSED_DIR / "final_validation_report.json"
MEASURED_REQUESTS = 20


class SimulatedTimeoutClient:
    """Exercise the API timeout classification without waiting for a real deadline."""

    def generate(self, **_: Any) -> Any:
        raise OllamaUnavailableError("Explanation timeout reached")


class SimulatedUnavailableClient:
    """Exercise the fast deterministic explanation fallback."""

    def generate(self, **_: Any) -> Any:
        raise OllamaUnavailableError("Local Ollama API unavailable: simulated connection failure")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def corpus_record_ids() -> set[str]:
    ids: set[str] = set()
    path = PROCESSED_DIR / "knowledge_corpus.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["record_id"])
    return ids


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(proportion * len(ordered)) - 1)
    return ordered[index]


def latency_statistics(values: list[float]) -> dict[str, Any]:
    return {
        "request_count": len(values),
        "average_ms": round(statistics.fmean(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "minimum_ms": round(min(values), 3),
        "maximum_ms": round(max(values), 3),
    }


def request_with_latency(
    client: TestClient,
    method: str,
    endpoint: str,
    body: dict[str, Any] | None = None,
) -> tuple[Any, float]:
    started = time.perf_counter()
    if method == "GET":
        response = client.get(endpoint)
    else:
        response = client.post(endpoint, json=body)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response, elapsed_ms


def response_has_sensitive_text(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False).casefold()
    forbidden = (
        str(PROJECT_ROOT).casefold(),
        "n:\\coding\\",
        "c:\\users\\",
        "api_key",
        "access_token",
        "private_key",
        "bearer ",
    )
    return any(item in serialized for item in forbidden)


def response_has_medical_language(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False).casefold()
    forbidden = (
        "diagnose",
        "diagnosis",
        "medical condition",
        "treatment advice",
        "you have an injury",
        "you have a disorder",
    )
    return any(item in serialized for item in forbidden)


def retrieved_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "retrieved_record_ids" and isinstance(nested, list):
                found.update(item for item in nested if isinstance(item, str))
            else:
                found.update(retrieved_ids(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(retrieved_ids(nested))
    return found


def plan_checks(plan: dict[str, Any], valid_ids: set[str]) -> dict[str, bool]:
    sessions = plan["sessions"]
    study = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "study")
    breaks = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "break")
    ids = retrieved_ids(plan)
    return {
        "time_not_exceeded": plan["total_planned_minutes"] <= plan["total_available_minutes"],
        "durations_positive": all(item["duration_minutes"] > 0 for item in sessions),
        "totals_consistent": (
            study == plan["total_study_minutes"]
            and breaks == plan["total_break_minutes"]
            and study + breaks == plan["total_planned_minutes"]
        ),
        "session_orders_valid": [item["order"] for item in sessions] == list(range(1, len(sessions) + 1)),
        "retrieved_ids_exist": ids <= valid_ids,
    }


def adapted_plan_checks(
    original: dict[str, Any],
    adapted: dict[str, Any],
    valid_ids: set[str],
) -> dict[str, bool]:
    sessions = adapted["sessions"]
    study = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "study")
    breaks = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "break")
    original_subject_order = [
        item["subject"] for item in original["sessions"] if item["session_type"] == "study"
    ]
    adapted_subject_order = [
        item["subject"] for item in sessions if item["session_type"] == "study"
    ]
    remaining = iter(original_subject_order)
    priorities_unchanged = all(any(candidate == subject for candidate in remaining) for subject in adapted_subject_order)
    return {
        "time_not_exceeded": adapted["total_planned_minutes"] <= adapted["total_available_minutes"],
        "durations_positive": all(item["duration_minutes"] > 0 for item in sessions),
        "totals_consistent": (
            study == adapted["total_study_minutes"]
            and breaks == adapted["total_break_minutes"]
            and study + breaks == adapted["total_planned_minutes"]
        ),
        "session_orders_valid": [item["order"] for item in sessions] == list(range(1, len(sessions) + 1)),
        "retrieved_ids_exist": retrieved_ids(adapted) <= valid_ids,
        "subject_priorities_unchanged": priorities_unchanged,
        "original_plan_id_preserved": adapted["original_plan_id"] == original["plan_id"],
    }


def explanation_checks(payload: dict[str, Any], plan: dict[str, Any]) -> dict[str, bool]:
    explanation = payload.get("explanation", payload)
    grounded = explanation["grounded_response"]
    expected_allocations = {
        item["subject"]: item["allocated_study_minutes"] for item in plan["scheduled_subjects"]
    }
    actual_allocations = {
        item["subject"]: item["allocated_minutes"] for item in grounded["allocation_explanations"]
    }
    return {
        "deterministic_allocations_unchanged": actual_allocations == expected_allocations,
        "explanation_schema_valid": explanation["validation_status"] in {
            "valid", "corrected_valid", "fallback_valid"
        },
        "safe_generation_mode": explanation["generation_mode"] in {
            "local_llm", "local_llm_corrected", "deterministic_fallback"
        },
    }


def evaluate_response(
    scenario: dict[str, Any],
    status_code: int,
    payload: dict[str, Any],
    valid_ids: set[str],
) -> tuple[dict[str, bool], bool]:
    expected_status = scenario.get("expected_status", 200)
    checks: dict[str, bool] = {
        "expected_http_status": status_code == expected_status,
        "no_local_paths_or_secrets": not response_has_sensitive_text(payload),
        "no_medical_or_diagnostic_language": not response_has_medical_language(payload),
    }
    if expected_status != 200:
        checks["safe_error_envelope"] = (
            isinstance(payload.get("error"), dict)
            and payload["error"].get("code") == "INVALID_REQUEST"
            and "request_id" in payload
        )
        return checks, all(checks.values())

    plan = payload.get("plan") or payload.get("original_plan")
    if isinstance(plan, dict):
        checks.update(plan_checks(plan, valid_ids))
    adapted = payload.get("adapted_plan")
    if isinstance(plan, dict) and isinstance(adapted, dict):
        checks.update(adapted_plan_checks(plan, adapted, valid_ids))
    if "grounded_response" in payload or "explanation" in payload:
        assert isinstance(plan, dict) or scenario["id"] == "ollama_timeout_fallback"
        explanation_plan = plan if isinstance(plan, dict) else scenario["_source_plan"]
        checks.update(explanation_checks(payload, explanation_plan))
    if scenario["id"] == "short_window_unscheduled" and isinstance(plan, dict):
        checks["has_unscheduled_subject"] = bool(plan["unscheduled_subjects"])
    if scenario["id"] == "unknown_subject_fallback":
        checks["knowledge_fallback_used"] = payload["fallback"]["used"] is True
    if scenario["id"] == "stale_sensor_fallback" and isinstance(adapted, dict):
        checks["stale_sensor_safe_fallback"] = adapted["adaptation_applied"] is False
    if scenario["id"] in {"long_sitting_adaptation", "pressure_imbalance_adaptation"}:
        checks["sensor_adaptation_applied"] = isinstance(adapted, dict) and adapted["adaptation_applied"] is True
    if scenario["id"] == "ollama_timeout_fallback":
        checks["timeout_fallback_classified"] = (
            payload["generation_mode"] == "deterministic_fallback"
            and payload["fallback_reason_code"] == "OLLAMA_TIMEOUT"
        )
    return checks, all(checks.values())


def cold_start_measurement(settings: APISettings, body: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    app = create_app(settings=settings)
    with TestClient(app) as client:
        ready_at = time.perf_counter()
        response, request_ms = request_with_latency(client, "POST", "/api/v1/plans", body)
    finished = time.perf_counter()
    return {
        "definition": "Application creation, lifespan initialization, and first deterministic plan request.",
        "startup_to_ready_ms": round((ready_at - started) * 1000, 3),
        "first_request_ms": round(request_ms, 3),
        "combined_ms": round((finished - started) * 1000, 3),
        "status_code": response.status_code,
    }


def measure_endpoint(
    client: TestClient,
    endpoint: str,
    body: dict[str, Any] | None,
    *,
    method: str = "POST",
) -> dict[str, Any]:
    warmup, _ = request_with_latency(client, method, endpoint, body)
    if warmup.status_code != 200:
        raise RuntimeError(f"Warm-up failed for {endpoint}: {warmup.status_code} {warmup.text}")
    values: list[float] = []
    for _ in range(MEASURED_REQUESTS):
        response, elapsed = request_with_latency(client, method, endpoint, body)
        if response.status_code != 200:
            raise RuntimeError(f"Measured request failed for {endpoint}: {response.status_code}")
        values.append(elapsed)
    return latency_statistics(values)


def benchmark_api(
    client: TestClient,
    school_request: dict[str, Any],
    plan: dict[str, Any],
    real_ollama_latency_ms: float | None,
    cold_start: dict[str, Any],
) -> dict[str, Any]:
    sensor = {
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
    full_request = copy.deepcopy(school_request)
    full_request["sensor_observation"] = sensor
    adapt_request = {"plan": plan, "sensor_observation": sensor}

    results = {
        "project_version": PROJECT_VERSION,
        "measured_at": utc_now(),
        "environment_note": "Local prototype measurement on the presentation development machine; not a production capacity claim.",
        "method": {
            "warmup_requests_per_endpoint": 1,
            "measured_requests_per_endpoint": MEASURED_REQUESTS,
            "clock": "time.perf_counter wall-clock latency around FastAPI TestClient",
            "percentile": "nearest-rank p95",
        },
        "cold_start": cold_start,
        "warm_endpoints": {
            "plans": measure_endpoint(client, "/api/v1/plans", school_request),
            "plans_adapt": measure_endpoint(client, "/api/v1/plans/adapt", adapt_request),
            "plans_full": measure_endpoint(client, "/api/v1/plans/full", full_request),
            "readiness": measure_endpoint(client, "/api/v1/readiness", None, method="GET"),
        },
    }

    services = client.app.state.services
    original_builder = services.generator_builder
    try:
        services.generator_builder = lambda timeout: GroundedResponseGenerator(
            PROJECT_ROOT, client=SimulatedUnavailableClient()
        )
        fallback_body = {"plan": plan, "timeout_seconds": 1}
        results["deterministic_fallback"] = measure_endpoint(
            client, "/api/v1/explanations", fallback_body
        )
        results["deterministic_fallback"]["method_note"] = (
            "Simulated immediate local connection failure; the real deterministic response and validation path ran."
        )
    finally:
        services.generator_builder = original_builder

    def concurrent_request(_: int) -> tuple[int, str | None]:
        response = client.post("/api/v1/plans", json=school_request)
        payload = response.json()
        return response.status_code, payload.get("plan", {}).get("plan_id")

    concurrent_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        concurrent_results = list(pool.map(concurrent_request, range(5)))
    concurrent_elapsed = (time.perf_counter() - concurrent_started) * 1000
    results["concurrent_batch"] = {
        "request_count": 5,
        "worker_count": 5,
        "batch_elapsed_ms": round(concurrent_elapsed, 3),
        "successful_requests": sum(status == 200 for status, _ in concurrent_results),
        "consistent_plan_id": len({plan_id for _, plan_id in concurrent_results}) == 1,
        "capacity_note": "Small correctness smoke only; not a production-scale load test.",
    }
    results["real_ollama_explanation"] = {
        "measured_request_count": 1 if real_ollama_latency_ms is not None else 0,
        "latency_ms": None if real_ollama_latency_ms is None else round(real_ollama_latency_ms, 3),
        "note": "One optional real local-model demo request; it is not a distribution benchmark.",
    }
    plans_average = results["warm_endpoints"]["plans"]["average_ms"]
    full_average = results["warm_endpoints"]["plans_full"]["average_ms"]
    results["plans_vs_full_investigation"] = {
        "plans_average_ms": plans_average,
        "plans_full_average_ms": full_average,
        "difference_ms": round(plans_average - full_average, 3),
        "finding": (
            "The repeated measurement does not reproduce a material /plans slowdown."
            if plans_average <= full_average * 1.1
            else "The repeated measurement still shows /plans slower; no implementation defect was found, so planner behavior was not changed."
        ),
    }
    return results


def run_scenarios(
    client: TestClient,
    scenarios: list[dict[str, Any]],
    *,
    skip_real_ollama: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float | None]:
    valid_ids = corpus_record_ids()
    results: list[dict[str, Any]] = []
    demo_outputs: list[dict[str, Any]] = []
    response_by_id: dict[str, dict[str, Any]] = {}
    real_ollama_latency_ms: float | None = None

    for source in scenarios:
        scenario = copy.deepcopy(source)
        mode = scenario.get("mode")
        if scenario["id"] == "ollama_available_explanation" and skip_real_ollama:
            results.append({
                "id": scenario["id"],
                "title": scenario["title"],
                "status": "not_run",
                "reason": "Real Ollama request was explicitly skipped.",
            })
            continue

        services = client.app.state.services
        original_builder = services.generator_builder
        try:
            if mode == "simulated_timeout":
                services.generator_builder = lambda timeout: GroundedResponseGenerator(
                    PROJECT_ROOT, client=SimulatedTimeoutClient()
                )
                source_plan = response_by_id[scenario["request_from"]]["plan"]
                scenario["request"] = {"plan": source_plan, "timeout_seconds": 1}
                scenario["_source_plan"] = source_plan
            response, elapsed_ms = request_with_latency(
                client, "POST", scenario["endpoint"], scenario["request"]
            )
        finally:
            services.generator_builder = original_builder

        payload = response.json()
        checks, passed = evaluate_response(scenario, response.status_code, payload, valid_ids)
        status = "passed" if passed else "failed"
        result = {
            "id": scenario["id"],
            "title": scenario["title"],
            "status": status,
            "http_status": response.status_code,
            "wall_time_ms": round(elapsed_ms, 3),
            "checks": checks,
        }
        if scenario["id"] == "ollama_available_explanation":
            real_ollama_latency_ms = elapsed_ms
            explanation = payload["explanation"]
            result["generation_mode"] = explanation["generation_mode"]
            result["model_status"] = explanation["model_status"]
            result["fallback_reason_code"] = explanation["fallback_reason_code"]
        results.append(result)
        output = {
            "id": scenario["id"],
            "title": scenario["title"],
            "endpoint": scenario["endpoint"],
            "http_status": response.status_code,
            "response": payload,
        }
        demo_outputs.append(output)
        response_by_id[scenario["id"]] = payload

    return results, demo_outputs, real_ollama_latency_ms


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-performance", action="store_true")
    parser.add_argument("--skip-real-ollama", action="store_true")
    args = parser.parse_args()

    inputs = load_json(INPUTS_PATH)
    scenarios = inputs["scenarios"]
    school_request = scenarios[0]["request"]
    settings = APISettings.from_environment(PROJECT_ROOT)
    cold_start = cold_start_measurement(settings, school_request)

    app = create_app(settings=settings)
    with TestClient(app) as client:
        if not client.app.state.services.deterministic_ready:
            raise RuntimeError("Deterministic API services are not ready")
        scenario_results, demo_outputs, real_ollama_latency = run_scenarios(
            client,
            scenarios,
            skip_real_ollama=args.skip_real_ollama,
        )
        school_output = next(item for item in demo_outputs if item["id"] == "secondary_without_sensor")
        performance = None
        if not args.skip_performance:
            performance = benchmark_api(
                client,
                school_request,
                school_output["response"]["plan"],
                real_ollama_latency,
                cold_start,
            )

        openapi = client.app.openapi()

    passed = sum(item["status"] == "passed" for item in scenario_results)
    failed = sum(item["status"] == "failed" for item in scenario_results)
    not_run = sum(item["status"] == "not_run" for item in scenario_results)
    evaluation = {
        "project_version": PROJECT_VERSION,
        "evaluated_at": utc_now(),
        "scenario_count": len(scenario_results),
        "passed": passed,
        "failed": failed,
        "not_run": not_run,
        "all_blocking_scenarios_passed": failed == 0,
        "scenarios": scenario_results,
    }
    outputs = {
        "project_version": PROJECT_VERSION,
        "generated_at": utc_now(),
        "outputs": demo_outputs,
    }
    validation = {
        "project_version": PROJECT_VERSION,
        "validated_at": utc_now(),
        "blocking_checks_passed": failed == 0 and not_run == 0,
        "checks": {
            "deterministic_services_ready": True,
            "end_to_end_scenarios_failed": failed,
            "end_to_end_scenarios_not_run": not_run,
            "openapi_version": openapi.get("openapi"),
            "openapi_path_count": len(openapi.get("paths", {})),
            "required_openapi_paths_present": all(
                path in openapi.get("paths", {})
                for path in (
                    "/api/v1/health",
                    "/api/v1/readiness",
                    "/api/v1/plans",
                    "/api/v1/plans/adapt",
                    "/api/v1/plans/full",
                    "/api/v1/explanations",
                    "/api/v1/plans/full-with-explanation",
                )
            ),
            "performance_measurements_completed": performance is not None,
            "concurrent_batch_successful": (
                performance is not None
                and performance["concurrent_batch"]["successful_requests"] == 5
                and performance["concurrent_batch"]["consistent_plan_id"]
            ),
        },
        "scope_note": "Repository tests, notebook execution, compilation, scans, and package audit are recorded during finalization after this script completes.",
    }
    write_json(OUTPUTS_PATH, outputs)
    write_json(EVALUATION_PATH, evaluation)
    if performance is not None:
        write_json(PERFORMANCE_PATH, performance)
    write_json(VALIDATION_PATH, validation)

    print(f"End-to-end scenarios: {passed} passed, {failed} failed, {not_run} not run")
    if performance is not None:
        for name, values in performance["warm_endpoints"].items():
            print(
                f"{name}: average={values['average_ms']:.3f} ms, "
                f"median={values['median_ms']:.3f} ms, p95={values['p95_ms']:.3f} ms"
            )
        batch = performance["concurrent_batch"]
        print(
            f"Concurrent batch: {batch['successful_requests']}/5 succeeded in "
            f"{batch['batch_elapsed_ms']:.3f} ms"
        )
    return 1 if failed or not_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
