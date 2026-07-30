"""Scalar Chroma metadata projection for ErgoStudy knowledge records."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


PROJECTION_FIELDS = (
    "document_family",
    "subject_family",
    "evidence_level",
    "review_tier",
    "reviewed",
    "synthetic",
    "safety_scope",
    "dataset_version",
    "supports_school",
    "supports_university",
    "sensor_mode",
    "learning_task",
    "cognitive_demand",
    "canonical_subject_record_id",
    "derived_from_record_id",
    "primary_source_id",
    "source_count",
    "source_ids_json",
)


def project_metadata(record: dict[str, Any]) -> dict[str, str | int | bool]:
    """Flatten one source record to a complete, consistently typed projection."""
    source_ids_in_source_order = [str(value) for value in record.get("source_ids", [])]
    source_ids = sorted(source_ids_in_source_order)
    educational_levels = set(record.get("educational_level", []))
    projection: dict[str, str | int | bool] = {
        "document_family": str(record["document_family"]),
        "subject_family": str(record.get("subject_family") or "not_applicable"),
        "evidence_level": str(record["evidence_level"]),
        "review_tier": str(record["review_tier"]),
        "reviewed": bool(record["reviewed"]),
        "synthetic": bool(record["synthetic"]),
        "safety_scope": str(record["safety_scope"]),
        "dataset_version": str(record["dataset_version"]),
        "supports_school": bool("school" in educational_levels or "cross_level" in educational_levels),
        "supports_university": bool("university" in educational_levels or "cross_level" in educational_levels),
        "sensor_mode": str(record.get("sensor_mode") or "not_applicable"),
        "learning_task": str(record.get("learning_task") or ""),
        "cognitive_demand": str(record.get("cognitive_demand") or ""),
        "canonical_subject_record_id": str(record.get("canonical_subject_record_id") or ""),
        "derived_from_record_id": str(record.get("derived_from_record_id") or ""),
        "primary_source_id": source_ids_in_source_order[0] if source_ids_in_source_order else "",
        "source_count": len(source_ids),
        "source_ids_json": json.dumps(source_ids, ensure_ascii=False, separators=(",", ":")),
    }
    if tuple(projection) != PROJECTION_FIELDS:
        raise AssertionError("Projection field order changed unexpectedly")
    validate_metadata_scalars(projection)
    return projection


def validate_metadata_scalars(metadata: dict[str, Any]) -> None:
    """Reject values Chroma cannot safely store as scalar metadata."""
    allowed = (str, int, float, bool)
    for key, value in metadata.items():
        if value is None or not isinstance(value, allowed):
            raise TypeError(f"Metadata field {key!r} is not a scalar: {type(value).__name__}")


def projection_hash(records: Iterable[dict[str, Any]]) -> str:
    """Hash ordered record IDs and their deterministic projected metadata."""
    payload = [
        {"record_id": record["record_id"], "metadata": project_metadata(record)}
        for record in records
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
