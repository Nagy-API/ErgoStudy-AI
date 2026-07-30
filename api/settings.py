"""Environment-driven settings for the local ErgoStudy API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CORS_ORIGINS = ("http://localhost", "http://127.0.0.1")


def _boolean_environment(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _cors_origins() -> tuple[str, ...]:
    value = os.getenv("ERGOSTUDY_CORS_ORIGINS")
    if value is None:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
    if not origins:
        raise ValueError("ERGOSTUDY_CORS_ORIGINS must contain at least one origin")
    return origins


def load_generation_settings(project_root: Path) -> dict[str, Any]:
    path = project_root / "config" / "generation_config.json"
    values = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "request_timeout_seconds",
        "minimum_request_timeout_seconds",
        "maximum_request_timeout_seconds",
    }
    missing = required - values.keys()
    if missing:
        raise ValueError(
            "generation configuration is missing API timeout fields: "
            + ", ".join(sorted(missing))
        )
    minimum = values["minimum_request_timeout_seconds"]
    default = values["request_timeout_seconds"]
    maximum = values["maximum_request_timeout_seconds"]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (minimum, default, maximum)):
        raise ValueError("explanation timeout settings must be integers")
    if not 1 <= minimum <= default <= maximum <= 120:
        raise ValueError("explanation timeout settings must satisfy 1 <= minimum <= default <= maximum <= 120")
    return values


@dataclass(frozen=True)
class APISettings:
    """Validated settings that do not require an optional settings package."""

    project_root: Path
    api_version: str
    host: str
    port: int
    cors_origins: tuple[str, ...]
    cors_allow_credentials: bool
    default_explanation_timeout_seconds: int
    minimum_explanation_timeout_seconds: int
    maximum_explanation_timeout_seconds: int
    ollama_readiness_timeout_seconds: float

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "APISettings":
        root = (project_root or Path(__file__).resolve().parents[1]).resolve()
        generation = load_generation_settings(root)
        port_text = os.getenv("ERGOSTUDY_API_PORT", "8000")
        try:
            port = int(port_text)
        except ValueError as error:
            raise ValueError("ERGOSTUDY_API_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ValueError("ERGOSTUDY_API_PORT must be between 1 and 65535")
        readiness_timeout = float(os.getenv("ERGOSTUDY_OLLAMA_READINESS_TIMEOUT_SECONDS", "1.0"))
        if not 0.1 <= readiness_timeout <= 5.0:
            raise ValueError(
                "ERGOSTUDY_OLLAMA_READINESS_TIMEOUT_SECONDS must be between 0.1 and 5.0"
            )
        credentials = _boolean_environment("ERGOSTUDY_CORS_ALLOW_CREDENTIALS", False)
        origins = _cors_origins()
        if credentials and "*" in origins:
            raise ValueError("credentialed CORS cannot use a wildcard origin")
        return cls(
            project_root=root,
            api_version="v1",
            host=os.getenv("ERGOSTUDY_API_HOST", "127.0.0.1"),
            port=port,
            cors_origins=origins,
            cors_allow_credentials=credentials,
            default_explanation_timeout_seconds=generation["request_timeout_seconds"],
            minimum_explanation_timeout_seconds=generation[
                "minimum_request_timeout_seconds"
            ],
            maximum_explanation_timeout_seconds=generation[
                "maximum_request_timeout_seconds"
            ],
            ollama_readiness_timeout_seconds=readiness_timeout,
        )
