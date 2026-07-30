"""Inspect the required local Ollama model and write a reproducible environment record."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "generation_config.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "local_llm_environment.json"


def _get_json(url: str) -> dict[str, Any]:
    with request.urlopen(url, timeout=10) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected response from {url}")
    return value


def _gpu_status(model_name: str, base_url: str) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "not_available", "execution": "not_loaded"}
    try:
        running = _get_json(f"{base_url}/api/ps").get("models", [])
        for model in running:
            if model.get("name") == model_name:
                size = int(model.get("size", 0) or 0)
                size_vram = int(model.get("size_vram", 0) or 0)
                result = {
                    "status": "available",
                    "execution": "gpu" if size_vram > 0 else "cpu",
                    "size_vram_bytes": size_vram,
                    "model_size_bytes": size,
                }
                break
    except (error.URLError, ValueError, TypeError):
        pass
    try:
        command = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode == 0 and completed.stdout.strip():
            result["nvidia_smi"] = completed.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def inspect_environment() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    base_url = config["ollama_base_url"].rstrip("/")
    model_name = config["model_name"]
    output: dict[str, Any] = {
        "local_only": True,
        "cloud_models_configured": False,
        "api_url": base_url,
        "api_status": "unavailable",
        "ollama_version": None,
        "model_name": model_name,
        "model_digest": None,
        "model_size_bytes": None,
        "model_size_gb": None,
        "gpu_usage": {"status": "not_available", "execution": "not_loaded"},
    }
    try:
        version = _get_json(f"{base_url}/api/version")
        tags = _get_json(f"{base_url}/api/tags")
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        output["error"] = str(exc)
        return output
    output["api_status"] = "responding"
    output["ollama_version"] = version.get("version")
    for model in tags.get("models", []):
        if model.get("name") == model_name or model.get("model") == model_name:
            size = int(model.get("size", 0))
            output["model_digest"] = model.get("digest")
            output["model_size_bytes"] = size
            output["model_size_gb"] = round(size / 1_000_000_000, 3)
            output["model_details"] = model.get("details", {})
            break
    output["gpu_usage"] = _gpu_status(model_name, base_url)
    return output


def main() -> int:
    environment = inspect_environment()
    OUTPUT_PATH.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(environment, indent=2))
    return 0 if environment["api_status"] == "responding" else 1


if __name__ == "__main__":
    raise SystemExit(main())
