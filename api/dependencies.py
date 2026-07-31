"""Request dependencies and API-facing pipeline operations."""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request

from api.lifecycle import AppServices
from src.deterministic_response import deterministic_grounded_response
from src.grounded_generator import GroundedResponseGenerator, load_generation_config
from src.grounding_context import build_grounding_context
from src.local_llm_client import LocalLLMClient, OllamaUnavailableError
from src.response_models import GenerationResult


class ServiceUnavailableError(RuntimeError):
    """Raised when deterministic startup prerequisites are not ready."""


class InvalidAPIRequestError(ValueError):
    """Raised for cross-field or configured-boundary API validation failures."""


class DeadlineLLMClient:
    """Apply one wall-clock deadline across the initial and correction calls."""

    def __init__(self, client: LocalLLMClient, timeout_seconds: float) -> None:
        self.client = client
        self.deadline = time.monotonic() + timeout_seconds

    def generate(self, **kwargs: Any):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise OllamaUnavailableError("Explanation timeout reached")
        self.client.timeout_seconds = max(0.05, remaining)
        return self.client.generate(**kwargs)


def get_services(request: Request) -> AppServices:
    services = getattr(request.app.state, "services", None)
    if not isinstance(services, AppServices):
        raise ServiceUnavailableError("API services are not initialized")
    return services


def request_id(request: Request) -> str:
    return str(request.state.request_id)


def require_deterministic_services(services: AppServices) -> None:
    if not services.deterministic_ready or services.planner is None:
        raise ServiceUnavailableError("The deterministic planning pipeline is not ready")


def plan_fallback_information(plan: dict[str, Any]) -> dict[str, Any]:
    subjects = [
        item["subject"] for item in plan.get("scheduled_subjects", []) if item.get("used_fallback")
    ]
    return {
        "used": bool(subjects),
        "reason_codes": ["KNOWLEDGE_FALLBACK"] if subjects else [],
        "subjects": subjects,
    }


def original_input_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    subjects = [
        {"name": item["subject"]}
        for item in [*plan.get("scheduled_subjects", []), *plan.get("unscheduled_subjects", [])]
    ]
    return {
        "total_available_minutes": plan.get("total_available_minutes"),
        "subjects": subjects,
    }


def relevant_record_summaries(services: AppServices, plan: dict[str, Any]) -> list[dict[str, Any]]:
    retrieval = services.retrieval_service
    records = getattr(retrieval, "records_by_id", {}) if retrieval is not None else {}
    ids: set[str] = set()
    for subject in plan.get("scheduled_subjects", []):
        ids.update(subject.get("retrieved_record_ids", []))
    for session in plan.get("sessions", []):
        ids.update(session.get("retrieved_record_ids", []))
    return [records[record_id] for record_id in sorted(ids) if record_id in records]


def build_generator(services: AppServices, timeout_seconds: float):
    if services.generator_builder is not None:
        return services.generator_builder(timeout_seconds)
    config = load_generation_config(services.settings.project_root)
    client = LocalLLMClient(
        base_url=config["ollama_base_url"],
        model_name=config["model_name"],
        timeout_seconds=timeout_seconds,
        temperature=config["temperature"],
        context_size=config["context_size"],
    )
    return GroundedResponseGenerator(
        services.settings.project_root,
        client=DeadlineLLMClient(client, timeout_seconds),
    )


def configured_timeout(services: AppServices, override: int | None) -> int:
    timeout = override or services.settings.default_explanation_timeout_seconds
    if not (
        services.settings.minimum_explanation_timeout_seconds
        <= timeout
        <= services.settings.maximum_explanation_timeout_seconds
    ):
        raise InvalidAPIRequestError(
            "timeout_seconds must be between "
            f"{services.settings.minimum_explanation_timeout_seconds} and "
            f"{services.settings.maximum_explanation_timeout_seconds}"
        )
    return timeout


def generate_explanation(
    services: AppServices,
    original_input: dict[str, Any],
    plan: dict[str, Any],
    timeout_seconds: int | None,
) -> tuple[GenerationResult, str | None, str, str]:
    """Generate an explanation or a validated deterministic fallback."""
    timeout = configured_timeout(services, timeout_seconds)
    started = time.perf_counter()
    try:
        generator = build_generator(services, timeout)
        result = generator.generate(
            original_input,
            plan,
            retrieved_record_summaries=relevant_record_summaries(services, plan),
        )
    except Exception:
        context = build_grounding_context(original_input, plan)
        result = GenerationResult(
            response=deterministic_grounded_response(context),
            generation_mode="deterministic_fallback",
            attempt_count=0,
            latency_seconds=time.perf_counter() - started,
            validation_errors=("api_generation_failure",),
        )

    if result.generation_mode == "local_llm":
        return result, None, "available", "valid"
    if result.generation_mode == "local_llm_corrected":
        return result, None, "available", "corrected_valid"
    combined = " ".join(result.validation_errors).casefold()
    if "timeout" in combined or "timed out" in combined:
        return result, "OLLAMA_TIMEOUT", "timed_out", "fallback_valid"
    if result.attempt_count == 2:
        return result, "MODEL_VALIDATION_FAILED", "invalid_output", "fallback_valid"
    if "unavailable" in combined or "connection" in combined or "refused" in combined:
        return result, "OLLAMA_UNAVAILABLE", "unavailable", "fallback_valid"
    return result, "GENERATION_FAILED", "failed", "fallback_valid"
