"""FastAPI lifespan initialization and reusable local services."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from fastapi import FastAPI

from api.settings import APISettings
from src.chroma_store import COLLECTION_NAME, close_client
from src.daily_planner import DailyPlanner
from src.grounded_generator import GroundedResponseGenerator, load_generation_config
from src.planner_config import load_planner_config
from src.retriever import RetrievalService


StatusMap = dict[str, dict[str, str]]


@dataclass
class AppServices:
    """Long-lived services shared safely by API requests."""

    settings: APISettings
    components: StatusMap
    planner: DailyPlanner | None = None
    retrieval_service: RetrievalService | Any | None = None
    generator_builder: Callable[[float], GroundedResponseGenerator | Any] | None = None
    operation_lock: RLock = field(default_factory=RLock)

    @property
    def deterministic_ready(self) -> bool:
        required = (
            "dataset",
            "chroma_collection",
            "embedding_model",
            "planner_config",
            "generation_config",
            "services",
        )
        return all(self.components.get(name, {}).get("status") == "ready" for name in required)

    def close(self) -> None:
        service = self.retrieval_service
        if service is not None and hasattr(service, "close"):
            service.close()


def _ready(detail: str) -> dict[str, str]:
    return {"status": "ready", "detail": detail}


def _unavailable(detail: str) -> dict[str, str]:
    return {"status": "unavailable", "detail": detail}


def initialize_services(settings: APISettings) -> AppServices:
    """Validate local artifacts and initialize the reusable deterministic pipeline."""
    root = settings.project_root
    components: StatusMap = {}
    required_dataset_files = (
        root / "data" / "processed" / "knowledge_corpus.jsonl",
        root / "data" / "processed" / "selected_embedding_model.json",
        root / "data" / "processed" / "retrieval_config.json",
        root / "data" / "processed" / "chroma_index_manifest.json",
    )
    if all(path.is_file() for path in required_dataset_files):
        components["dataset"] = _ready("Required processed dataset artifacts are available.")
    else:
        components["dataset"] = _unavailable("One or more required dataset artifacts are unavailable.")

    try:
        load_planner_config(root / "config" / "planner_config.json")
        components["planner_config"] = _ready("Planner configuration is valid.")
    except Exception:
        components["planner_config"] = _unavailable("Planner configuration is invalid or unavailable.")
    try:
        load_generation_config(root)
        components["generation_config"] = _ready("Generation configuration is valid.")
    except Exception:
        components["generation_config"] = _unavailable("Generation configuration is invalid or unavailable.")

    try:
        import json
        from huggingface_hub import snapshot_download

        selected = json.loads(
            (root / "data" / "processed" / "selected_embedding_model.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot_download(
            repo_id=selected["model_id"],
            revision=selected["model_revision"],
            local_files_only=True,
        )
        components["embedding_model"] = _ready("The selected embedding model is available locally.")
    except Exception:
        components["embedding_model"] = _unavailable("The selected embedding model is not available locally.")

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(root / "chroma_db"))
        try:
            collection = client.get_collection(COLLECTION_NAME, embedding_function=None)
            if collection.count() <= 0:
                raise ValueError("empty collection")
        finally:
            close_client(client)
        components["chroma_collection"] = _ready("The persistent Chroma collection is accessible.")
    except Exception:
        components["chroma_collection"] = _unavailable("The persistent Chroma collection is unavailable.")

    services = AppServices(settings=settings, components=components)
    prerequisites = all(item["status"] == "ready" for item in components.values())
    if not prerequisites:
        components["services"] = _unavailable("Deterministic services were not initialized because a prerequisite failed.")
        return services
    try:
        retrieval = RetrievalService.from_frozen_config(root, device="cpu")
        services.retrieval_service = retrieval
        services.planner = DailyPlanner(root, retrieval_service=retrieval)
        components["services"] = _ready("Reusable planner and retrieval services are initialized.")
    except Exception:
        services.close()
        services.retrieval_service = None
        services.planner = None
        components["services"] = _unavailable("Deterministic services could not be initialized.")
    return services


def create_lifespan(
    settings: APISettings,
    service_factory: Callable[[APISettings], AppServices] = initialize_services,
):
    """Create one explicit lifespan handler for production and test applications."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = service_factory(settings)
        app.state.services = services
        try:
            yield
        finally:
            services.close()

    return lifespan
