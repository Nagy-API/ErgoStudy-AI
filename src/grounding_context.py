"""Build the small allow-listed context sent to the local language model."""

from __future__ import annotations

import copy
from typing import Any, Iterable


FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "evaluation_queries",
        "expected_ids",
        "expected_record_ids",
        "final_test_ids",
        "local_file_path",
        "path",
        "git",
        "commit",
    }
)


def _as_dict(value: Any, label: str) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object or expose to_dict()")
    return copy.deepcopy(value)


def _safe_user_input(values: dict[str, Any]) -> dict[str, Any]:
    scalar_fields = {
        "total_available_minutes",
        "preferred_start_time",
        "preferred_session_length",
    }
    result = {key: copy.deepcopy(values[key]) for key in scalar_fields if key in values}
    subject_fields = {
        "name",
        "topics",
        "difficulty",
        "priority",
        "workload",
        "current_understanding",
    }
    raw_subjects = values.get("subjects", [])
    if isinstance(raw_subjects, list):
        result["subjects"] = [
            {key: copy.deepcopy(subject[key]) for key in subject_fields if key in subject}
            for subject in raw_subjects
            if isinstance(subject, dict)
        ]
    serialized_keys: list[str] = []

    def collect_keys(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                serialized_keys.append(str(key).lower())
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(values)
    if any(key in FORBIDDEN_INPUT_KEYS for key in serialized_keys):
        raise ValueError("original user input contains an evaluation or internal-only field")
    return result


def _record_ids(plan: dict[str, Any], sessions: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for item in plan.get("scheduled_subjects", []):
        ids.update(str(value) for value in item.get("retrieved_record_ids", []))
    for item in sessions:
        ids.update(str(value) for value in item.get("retrieved_record_ids", []))
    return ids


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    record_id = record.get("record_id")
    summary = record.get("summary", record.get("retrieval_text"))
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("retrieved record summary requires record_id")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(f"retrieved record {record_id} requires a summary")
    concise = summary.strip()
    if len(concise) > 220:
        concise = concise[:217].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."
    raw_source_ids = record.get("source_ids", [])
    source_ids = raw_source_ids if isinstance(raw_source_ids, list) else []
    return {
        "record_id": record_id,
        "title": str(record.get("title", "")),
        "document_family": str(record.get("document_family", "")),
        "summary": concise,
        "source_ids": [str(item) for item in source_ids],
        "evidence_level": str(record.get("evidence_level", "")),
        "reviewed": bool(record.get("reviewed", False)),
    }


def build_grounding_context(
    original_user_input: dict[str, Any],
    plan: Any,
    *,
    retrieved_record_summaries: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Return only deterministic results and relevant supplied record summaries."""
    original = _as_dict(original_user_input, "original user input")
    plan_values = _as_dict(plan, "daily study plan")
    sessions = copy.deepcopy(plan_values.get("sessions", []))
    if not isinstance(sessions, list):
        raise ValueError("final sessions must be a list")
    allowed_ids = _record_ids(plan_values, sessions)
    relevant_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for supplied in retrieved_record_summaries:
        summary = _record_summary(copy.deepcopy(supplied))
        if summary["record_id"] in allowed_ids and summary["record_id"] not in seen:
            relevant_records.append(summary)
            seen.add(summary["record_id"])
    relevant_records.sort(key=lambda item: item["record_id"])
    final_plan = {
        "total_available_minutes": plan_values.get("total_available_minutes"),
        "total_study_minutes": plan_values.get("total_study_minutes"),
        "total_break_minutes": plan_values.get("total_break_minutes"),
        "subject_allocations": [
            {
                "subject": item.get("subject"),
                "allocated_minutes": item.get("allocated_study_minutes"),
                "reason": item.get("reason"),
                "retrieved_record_ids": copy.deepcopy(item.get("retrieved_record_ids", [])),
                "used_fallback": bool(item.get("used_fallback", False)),
            }
            for item in plan_values.get("scheduled_subjects", [])
        ],
        "sessions": sessions,
        "unscheduled_subjects": copy.deepcopy(plan_values.get("unscheduled_subjects", [])),
        "warnings": copy.deepcopy(plan_values.get("warnings", [])),
    }
    return {
        "original_user_input": _safe_user_input(original),
        "final_plan": final_plan,
        "retrieved_record_summaries": relevant_records,
    }
