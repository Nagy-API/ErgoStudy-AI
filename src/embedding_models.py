"""Embedding configuration, preprocessing, and local model helpers."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class EmbeddingConfiguration:
    """One model plus its model-specific retrieval formatting."""

    config_id: str
    model_id: str
    query_prefix: str
    document_prefix: str
    normalize_embeddings: bool = True

    def format_query(self, text: str) -> str:
        return f"{self.query_prefix}{text}"

    def format_document(self, text: str) -> str:
        return f"{self.document_prefix}{text}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_embedding_configurations(path: Path) -> tuple[dict[str, Any], list[EmbeddingConfiguration]]:
    """Load the shared benchmark settings and ordered configurations."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    configurations = [EmbeddingConfiguration(**item) for item in raw["configurations"]]
    return raw, configurations


def normalize_rows(values: np.ndarray) -> np.ndarray:
    """Return deterministic float32 row-wise L2 normalized vectors."""
    array = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Cannot normalize an all-zero embedding")
    return np.asarray(array / norms, dtype=np.float32)


def configure_deterministic_inference(seed: int = 20260730) -> None:
    """Configure repeatable inference without enabling slower training-only paths."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.set_grad_enabled(False)
    except ImportError:
        return


def select_device() -> str:
    """Choose CUDA when PyTorch can safely use it, otherwise use the CPU."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def load_sentence_transformer(
    model_id: str,
    device: str,
    *,
    revision: str | None = None,
    local_files_only: bool = False,
):
    """Load a SentenceTransformer lazily so unit tests need no model download."""
    from sentence_transformers import SentenceTransformer

    model_source = model_id
    model_revision = revision
    if local_files_only:
        from huggingface_hub import snapshot_download

        model_source = str(
            snapshot_download(
                repo_id=model_id,
                revision=revision,
                local_files_only=True,
            )
        )
        model_revision = None
    return SentenceTransformer(
        model_source,
        device=device,
        revision=model_revision,
        local_files_only=local_files_only,
    )


def encode_texts(
    model: Any,
    texts: Iterable[str],
    *,
    batch_size: int,
    normalize_embeddings: bool,
) -> np.ndarray:
    """Encode text as normalized float32 NumPy rows."""
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize_embeddings,
    )
    array = np.asarray(embeddings, dtype=np.float32)
    return normalize_rows(array) if normalize_embeddings else array


def token_length_report(model: Any, record_ids: list[str], texts: list[str]) -> dict[str, Any]:
    """Check complete token lengths before encoding and report truncation risks."""
    tokenizer = model.tokenizer
    maximum = int(model.max_seq_length)
    affected: list[dict[str, Any]] = []
    maximum_seen = 0
    for record_id, text in zip(record_ids, texts, strict=True):
        token_ids = tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
        length = len(token_ids)
        maximum_seen = max(maximum_seen, length)
        if length > maximum:
            affected.append({"record_id": record_id, "token_count": length})
    return {
        "maximum_sequence_length": maximum,
        "maximum_observed_token_count": maximum_seen,
        "truncation_count": len(affected),
        "truncated_record_ids": affected,
    }


def measure_query_latencies(
    model: Any,
    texts: list[str],
    *,
    normalize_embeddings: bool,
) -> tuple[np.ndarray, dict[str, float]]:
    """Encode each development query once and record device-synchronized latency."""
    import torch

    if texts:
        encode_texts(model, [texts[0]], batch_size=1, normalize_embeddings=normalize_embeddings)
    rows: list[np.ndarray] = []
    latencies: list[float] = []
    for text in texts:
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        started = perf_counter()
        row = encode_texts(model, [text], batch_size=1, normalize_embeddings=normalize_embeddings)[0]
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        latencies.append((perf_counter() - started) * 1000.0)
        rows.append(row)
    values = np.asarray(latencies, dtype=np.float64)
    return np.asarray(rows, dtype=np.float32), {
        "average_query_latency_ms": float(np.mean(values)),
        "median_query_latency_ms": float(np.median(values)),
        "p95_query_latency_ms": float(np.percentile(values, 95)),
    }
