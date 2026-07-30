"""Local FastAPI application exposing the ErgoStudy deterministic pipeline."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import (
    generate_explanation,
    get_services,
    original_input_from_plan,
    plan_fallback_information,
    request_id,
    require_deterministic_services,
)
from api.error_handlers import register_error_handlers
from api.lifecycle import AppServices, create_lifespan, initialize_services
from api.schemas import (
    AdaptPlanRequest,
    AdaptPlanResponse,
    ExplanationRequest,
    ExplanationResponse,
    ErrorResponse,
    FullPlanRequest,
    FullPlanResponse,
    FullWithExplanationRequest,
    FullWithExplanationResponse,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    ReadinessResponse,
)
from api.settings import APISettings
from src.grounded_generator import load_generation_config
from src.local_llm_client import LocalLLMClient, OllamaError


ServicesDependency = Annotated[AppServices, Depends(get_services)]
COMMON_ERROR_RESPONSES = {
    422: {"model": ErrorResponse, "description": "Invalid request"},
    503: {"model": ErrorResponse, "description": "Deterministic services unavailable"},
}


def _milliseconds(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _plan_values(request: PlanRequest | FullPlanRequest | FullWithExplanationRequest) -> dict[str, Any]:
    return request.model_dump(
        exclude={"sensor_observation", "explanation_timeout_seconds"},
        exclude_none=True,
    )


def _make_plan(services: AppServices, values: dict[str, Any]) -> dict[str, Any]:
    require_deterministic_services(services)
    assert services.planner is not None
    with services.operation_lock:
        return services.planner.plan(values).to_dict()


def _adapt_plan(
    services: AppServices,
    plan: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    require_deterministic_services(services)
    assert services.sensor_adapter is not None
    with services.operation_lock:
        return services.sensor_adapter.adapt(plan, observation).to_dict()


def _explanation_payload(
    result,
    fallback_reason: str | None,
    model_status: str,
    validation_status: str,
    current_request_id: str,
) -> dict[str, Any]:
    return {
        "grounded_response": result.response.to_dict(),
        "generation_mode": result.generation_mode,
        "model_status": model_status,
        "validation_status": validation_status,
        "fallback_reason_code": fallback_reason,
        "attempt_count": result.attempt_count,
        "generation_latency_ms": round(result.latency_seconds * 1000, 3),
        "request_id": current_request_id,
        "api_version": "v1",
    }


def create_app(
    *,
    settings: APISettings | None = None,
    service_factory: Callable[[APISettings], AppServices] = initialize_services,
) -> FastAPI:
    api_settings = settings or APISettings.from_environment()
    application = FastAPI(
        title="ErgoStudy AI Local API",
        summary="Deterministic one-day planning, optional sensor adaptation, and grounded explanations.",
        description=(
            "The deterministic planner and sensor adapter own all schedule values. "
            "Explanation endpoints may use local Ollama and always retain a validated deterministic fallback."
        ),
        version="1.0.0-prototype",
        lifespan=create_lifespan(api_settings, service_factory),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(api_settings.cors_origins),
        allow_credentials=api_settings.cors_allow_credentials,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept", "X-Request-ID"],
    )

    @application.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    register_error_handlers(application)

    @application.get(
        "/api/v1/health",
        response_model=HealthResponse,
        tags=["service"],
        summary="Check basic process health without loading models",
    )
    async def health(request: Request) -> dict[str, Any]:
        return {"status": "ok", "api_version": "v1", "request_id": request_id(request)}

    @application.get(
        "/api/v1/readiness",
        response_model=ReadinessResponse,
        tags=["service"],
        summary="Check deterministic prerequisites and Ollama separately",
    )
    async def readiness(request: Request, services: ServicesDependency) -> dict[str, Any]:
        try:
            config = load_generation_config(api_settings.project_root)
            client = LocalLLMClient(
                base_url=config["ollama_base_url"],
                model_name=config["model_name"],
                timeout_seconds=api_settings.ollama_readiness_timeout_seconds,
                temperature=config["temperature"],
                context_size=config["context_size"],
            )
            version = await asyncio.to_thread(client.api_version)
            ollama = {"status": "ready", "detail": f"Local Ollama API version {version} is available."}
        except OllamaError:
            ollama = {
                "status": "unavailable",
                "detail": "Local Ollama is unavailable; deterministic planning remains ready.",
            }
        return {
            "ready": services.deterministic_ready,
            "components": services.components,
            "ollama": ollama,
            "api_version": "v1",
            "request_id": request_id(request),
        }

    @application.post(
        "/api/v1/plans",
        response_model=PlanResponse,
        tags=["plans"],
        summary="Create one deterministic daily plan",
        description="Fast deterministic endpoint. It never calls Ollama.",
        responses=COMMON_ERROR_RESPONSES,
    )
    async def create_plan(
        body: PlanRequest,
        request: Request,
        services: ServicesDependency,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        plan = await asyncio.to_thread(_make_plan, services, _plan_values(body))
        return {
            "plan": plan,
            "request_id": request_id(request),
            "processing_time_ms": _milliseconds(started),
            "fallback": plan_fallback_information(plan),
            "api_version": "v1",
        }

    @application.post(
        "/api/v1/plans/adapt",
        response_model=AdaptPlanResponse,
        tags=["plans"],
        summary="Apply deterministic sensor adaptation to an existing plan",
        description="Fast deterministic endpoint. It never calls Ollama.",
        responses=COMMON_ERROR_RESPONSES,
    )
    async def adapt_plan(
        body: AdaptPlanRequest,
        request: Request,
        services: ServicesDependency,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        observation = (
            body.sensor_observation.model_dump(exclude_none=True)
            if body.sensor_observation is not None
            else {
                "sensor_enabled": True,
                "connection_status": "connected",
                "observation_status": "missing",
            }
        )
        adapted = await asyncio.to_thread(
            _adapt_plan,
            services,
            body.plan.model_dump(),
            observation,
        )
        return {
            "adapted_plan": adapted,
            "request_id": request_id(request),
            "processing_time_ms": _milliseconds(started),
            "api_version": "v1",
        }

    @application.post(
        "/api/v1/plans/full",
        response_model=FullPlanResponse,
        tags=["plans"],
        summary="Create and optionally adapt a deterministic plan",
        description="Fast deterministic convenience endpoint. It never calls Ollama.",
        responses=COMMON_ERROR_RESPONSES,
    )
    async def full_plan(
        body: FullPlanRequest,
        request: Request,
        services: ServicesDependency,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        plan = await asyncio.to_thread(_make_plan, services, _plan_values(body))
        adapted = None
        if body.sensor_observation is not None:
            adapted = await asyncio.to_thread(
                _adapt_plan,
                services,
                plan,
                body.sensor_observation.model_dump(exclude_none=True),
            )
        return {
            "original_plan": plan,
            "adapted_plan": adapted,
            "final_sessions": adapted["sessions"] if adapted is not None else plan["sessions"],
            "request_id": request_id(request),
            "processing_time_ms": _milliseconds(started),
            "fallback": plan_fallback_information(plan),
            "api_version": "v1",
        }

    @application.post(
        "/api/v1/explanations",
        response_model=ExplanationResponse,
        tags=["explanations"],
        summary="Explain an existing deterministic plan",
        description=(
            "Potentially slow local-LLM endpoint. Timeout, connection, malformed-output, and "
            "validation failures return a deterministic fallback with HTTP 200."
        ),
        responses=COMMON_ERROR_RESPONSES,
    )
    async def explanation(
        body: ExplanationRequest,
        request: Request,
        services: ServicesDependency,
    ) -> dict[str, Any]:
        require_deterministic_services(services)
        plan = body.plan.model_dump()
        adapted = body.adapted_plan.model_dump() if body.adapted_plan is not None else None
        result, reason, model_status, validation_status = await asyncio.to_thread(
            generate_explanation,
            services,
            original_input_from_plan(plan),
            plan,
            adapted,
            body.timeout_seconds,
        )
        return _explanation_payload(
            result,
            reason,
            model_status,
            validation_status,
            request_id(request),
        )

    @application.post(
        "/api/v1/plans/full-with-explanation",
        response_model=FullWithExplanationResponse,
        tags=["demos"],
        summary="Run the full demo pipeline",
        description=(
            "Demo-only and slower than /api/v1/plans/full because it may wait for local Ollama. "
            "The plan remains valid when explanation generation falls back."
        ),
        responses=COMMON_ERROR_RESPONSES,
    )
    async def full_with_explanation(
        body: FullWithExplanationRequest,
        request: Request,
        services: ServicesDependency,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        original_input = _plan_values(body)
        plan = await asyncio.to_thread(_make_plan, services, original_input)
        adapted = None
        if body.sensor_observation is not None:
            adapted = await asyncio.to_thread(
                _adapt_plan,
                services,
                plan,
                body.sensor_observation.model_dump(exclude_none=True),
            )
        result, reason, model_status, validation_status = await asyncio.to_thread(
            generate_explanation,
            services,
            original_input,
            plan,
            adapted,
            body.explanation_timeout_seconds,
        )
        current_request_id = request_id(request)
        return {
            "original_plan": plan,
            "adapted_plan": adapted,
            "explanation": _explanation_payload(
                result,
                reason,
                model_status,
                validation_status,
                current_request_id,
            ),
            "request_id": current_request_id,
            "processing_time_ms": _milliseconds(started),
            "fallback": plan_fallback_information(plan),
            "api_version": "v1",
        }

    return application


app = create_app()
