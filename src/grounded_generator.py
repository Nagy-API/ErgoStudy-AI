"""Orchestrate local grounded generation, one correction, and safe fallback."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable

from src.deterministic_response import deterministic_grounded_response
from src.generation_validator import validate_generated_response
from src.grounding_context import build_grounding_context
from src.local_llm_client import LocalLLMClient, OllamaError
from src.response_models import GenerationResult, OUTPUT_JSON_SCHEMA


SYSTEM_INSTRUCTION = """You are the local wording layer for ErgoStudy AI. /no_think
Use only the supplied structured data. The deterministic study plan is final.
Do not change, add, remove, or reorder subjects, sessions, durations, breaks, priorities,
or allocations. Do not invent inputs, record IDs, facts, or
educational claims. Do not diagnose conditions or give medical or treatment advice.
Return concise natural English as JSON matching the schema exactly. Use exact subject names,
allocated minutes, and session orders. Include one allocation explanation per scheduled subject
and one message per final session. Use no Markdown, no
hidden reasoning, no extra fields, and do not mention record IDs."""


def load_generation_config(project_root: Path) -> dict[str, Any]:
    path = project_root / "config" / "generation_config.json"
    values = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "model_name",
        "ollama_base_url",
        "request_timeout_seconds",
        "temperature",
        "context_size",
        "maximum_correction_attempts",
    }
    missing = required - values.keys()
    if missing:
        raise ValueError(f"generation configuration is missing: {', '.join(sorted(missing))}")
    if values["model_name"] != "qwen3:4b-instruct":
        raise ValueError("Stage 7 permits only qwen3:4b-instruct")
    if values.get("stream") is not False or values["temperature"] != 0:
        raise ValueError("Stage 7 requires stream=false and temperature=0")
    if values["maximum_correction_attempts"] != 1:
        raise ValueError("Stage 7 requires exactly one correction attempt")
    return values


def _initial_prompt(context: dict[str, Any]) -> str:
    return (
        "Create the grounded response from this structured data. Return JSON only.\n"
        + json.dumps(context, ensure_ascii=True, sort_keys=True)
    )


def _correction_prompt(context: dict[str, Any], errors: tuple[str, ...]) -> str:
    payload = {
        "task": "Correct the prior invalid response. Return only a new JSON object.",
        "validation_errors": list(errors),
        "original_structured_data": context,
        "required_schema": OUTPUT_JSON_SCHEMA,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class GroundedResponseGenerator:
    """Keep deterministic values authoritative around one local model call."""

    def __init__(self, project_root: Path, *, client: LocalLLMClient | Any | None = None) -> None:
        self.project_root = project_root.resolve()
        self.config = load_generation_config(self.project_root)
        self.client = client or LocalLLMClient(
            base_url=self.config["ollama_base_url"],
            model_name=self.config["model_name"],
            timeout_seconds=self.config["request_timeout_seconds"],
            temperature=self.config["temperature"],
            context_size=self.config["context_size"],
        )

    def generate(
        self,
        original_user_input: dict[str, Any],
        plan: Any,
        *,
        retrieved_record_summaries: Iterable[dict[str, Any]] = (),
    ) -> GenerationResult:
        context = build_grounding_context(
            original_user_input,
            plan,
            retrieved_record_summaries=retrieved_record_summaries,
        )
        started = time.perf_counter()
        collected_errors: list[str] = []
        try:
            first = self.client.generate(
                system_instruction=SYSTEM_INSTRUCTION,
                user_prompt=_initial_prompt(context),
                output_schema=OUTPUT_JSON_SCHEMA,
            )
            first_validation = validate_generated_response(first.content, context)
            if first_validation.valid and first_validation.response is not None:
                return GenerationResult(
                    response=first_validation.response,
                    generation_mode="local_llm",
                    attempt_count=1,
                    latency_seconds=time.perf_counter() - started,
                )
            collected_errors.extend(first_validation.errors)
            corrected = self.client.generate(
                system_instruction=SYSTEM_INSTRUCTION,
                user_prompt=_correction_prompt(context, first_validation.errors),
                output_schema=OUTPUT_JSON_SCHEMA,
            )
            correction_validation = validate_generated_response(corrected.content, context)
            if correction_validation.valid and correction_validation.response is not None:
                return GenerationResult(
                    response=correction_validation.response,
                    generation_mode="local_llm_corrected",
                    attempt_count=2,
                    latency_seconds=time.perf_counter() - started,
                    validation_errors=tuple(collected_errors),
                )
            collected_errors.extend(correction_validation.errors)
            attempts = 2
        except OllamaError as exc:
            collected_errors.append(str(exc))
            attempts = 0
        fallback = deterministic_grounded_response(context)
        fallback_validation = validate_generated_response(fallback.to_dict(), context)
        if not fallback_validation.valid:
            raise AssertionError(
                "deterministic fallback failed validation: " + "; ".join(fallback_validation.errors)
            )
        return GenerationResult(
            response=fallback,
            generation_mode="deterministic_fallback",
            attempt_count=attempts,
            latency_seconds=time.perf_counter() - started,
            validation_errors=tuple(collected_errors),
        )


def generate_grounded_response(
    project_root: Path,
    original_user_input: dict[str, Any],
    plan: Any,
    **kwargs: Any,
) -> GenerationResult:
    return GroundedResponseGenerator(project_root).generate(original_user_input, plan, **kwargs)
