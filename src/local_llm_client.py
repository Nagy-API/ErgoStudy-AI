"""Small standard-library client for the local Ollama API."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class OllamaError(RuntimeError):
    """Base error for a local Ollama request."""


class OllamaUnavailableError(OllamaError):
    """Raised when the local API cannot be reached."""


@dataclass(frozen=True)
class LocalLLMResponse:
    content: str
    latency_seconds: float
    model: str
    total_duration_nanoseconds: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None


class LocalLLMClient:
    """Call one explicitly configured local model with deterministic options."""

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: int = 180,
        temperature: float = 0,
        context_size: int = 4096,
    ) -> None:
        if not base_url.startswith(("http://127.0.0.1", "http://localhost")):
            raise ValueError("Ollama base_url must be local")
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.context_size = context_size

    def _json_request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, OSError) as exc:
            raise OllamaUnavailableError(f"Local Ollama API unavailable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama returned an unexpected response shape")
        return parsed

    def api_version(self) -> str:
        value = self._json_request("/api/version").get("version")
        if not isinstance(value, str) or not value:
            raise OllamaError("Ollama version response is missing version")
        return value

    def model_details(self) -> dict[str, Any]:
        return self._json_request("/api/show", {"model": self.model_name})

    def running_models(self) -> dict[str, Any]:
        return self._json_request("/api/ps")

    def generate(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> LocalLLMResponse:
        payload = {
            "model": self.model_name,
            "stream": False,
            "format": output_schema,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.context_size,
            },
        }
        started = time.perf_counter()
        response = self._json_request("/api/chat", payload)
        latency = time.perf_counter() - started
        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama response is missing message content")
        return LocalLLMResponse(
            content=content,
            latency_seconds=latency,
            model=str(response.get("model", self.model_name)),
            total_duration_nanoseconds=(
                response.get("total_duration")
                if isinstance(response.get("total_duration"), int)
                else None
            ),
            prompt_eval_count=(
                response.get("prompt_eval_count")
                if isinstance(response.get("prompt_eval_count"), int)
                else None
            ),
            eval_count=response.get("eval_count") if isinstance(response.get("eval_count"), int) else None,
        )
