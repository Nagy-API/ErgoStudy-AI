"""Post-generation grounding, structure, numeric, and safety validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.response_models import GroundedResponse


MEDICAL_PATTERN = re.compile(
    r"\b(diagnos(?:e|ed|is|tic)|disease|disorder|injur(?:y|ies)|treatment|therapy|"
    r"medication|medicine|doctor|clinician|symptom|cure|medical condition|chronic pain)\b",
    re.IGNORECASE,
)
UNSUPPORTED_INPUT_TERMS = (
    "exam",
    "deadline",
    "homework",
    "assignment",
    "test date",
    "due date",
    "tomorrow",
)
RECORD_ID_PATTERN = re.compile(
    r"\b(?:subject|topic|strategy|session)-[a-z0-9][a-z0-9-]*-v\d+\b",
    re.IGNORECASE,
)
MINUTE_PATTERN = re.compile(r"\b(\d+)\s*(?:-|\s)?minutes?\b", re.IGNORECASE)
WORD_MINUTE_PATTERN = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s*(?:-|\s)minutes?\b",
    re.IGNORECASE,
)
WORD_NUMBERS = {
    word: value
    for value, word in enumerate(
        (
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        )
    )
}
MARKDOWN_PATTERN = re.compile(r"```|`|\*\*|__|(?:^|\n)\s*#{1,6}\s|(?:^|\n)\s*[-*+]\s")


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    response: GroundedResponse | None = None


def _all_text(response: GroundedResponse) -> list[str]:
    values = [response.summary, *(item.reason for item in response.allocation_explanations)]
    values.extend(item.message for item in response.session_messages)
    values.extend(response.warnings)
    if response.unscheduled_message:
        values.append(response.unscheduled_message)
    return values


def _non_english_text(text: str) -> bool:
    return any(character.isalpha() and ord(character) > 127 for character in text)


def _minute_values(text: str) -> set[int]:
    values = {int(match) for match in MINUTE_PATTERN.findall(text)}
    values.update(WORD_NUMBERS[match.lower()] for match in WORD_MINUTE_PATTERN.findall(text))
    return values


def validate_generated_response(
    raw_response: str | dict[str, Any],
    grounding_context: dict[str, Any],
) -> ValidationResult:
    errors: list[str] = []
    if isinstance(raw_response, str):
        try:
            values = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            return ValidationResult(False, (f"invalid JSON: {exc.msg}",))
    else:
        values = raw_response
    try:
        response = GroundedResponse.from_dict(values)
    except (TypeError, ValueError) as exc:
        return ValidationResult(False, (str(exc),))

    plan = grounding_context["final_plan"]
    expected_allocations = {
        item["subject"]: item["allocated_minutes"] for item in plan["subject_allocations"]
    }
    allowed_plan_minutes = {
        int(value)
        for key in ("total_available_minutes", "total_study_minutes", "total_break_minutes")
        if isinstance((value := plan.get(key)), int) and not isinstance(value, bool)
    }
    allowed_plan_minutes.update(expected_allocations.values())
    allowed_plan_minutes.update(item["duration_minutes"] for item in plan["sessions"])
    if not _minute_values(response.summary).issubset(allowed_plan_minutes):
        errors.append("summary changes or invents a duration")
    actual_allocations = {
        item.subject: item.allocated_minutes for item in response.allocation_explanations
    }
    if len(actual_allocations) != len(response.allocation_explanations):
        errors.append("allocation explanations contain duplicate subjects")
    if set(actual_allocations) != set(expected_allocations):
        errors.append("allocation explanations must contain every exact scheduled subject once")
    for subject, minutes in actual_allocations.items():
        if subject in expected_allocations and minutes != expected_allocations[subject]:
            errors.append(
                f"allocated minutes changed for {subject}: expected {expected_allocations[subject]}, got {minutes}"
            )
    for item in response.allocation_explanations:
        claims = _minute_values(item.reason)
        if claims and claims != {item.allocated_minutes}:
            errors.append(f"allocation reason changes the minutes for {item.subject}")
        expected_reason = next(
            (
                source.get("reason", "")
                for source in plan["subject_allocations"]
                if source.get("subject") == item.subject
            ),
            "",
        ).lower()
        priority_claims = re.findall(
            r"\b(low|medium|high|higher|highest|lower|lowest|top) priority\b",
            item.reason.lower(),
        )
        for level in priority_claims:
            if f"{level} priority" not in expected_reason:
                errors.append(f"unsupported priority claim for {item.subject}")

    expected_sessions = {item["order"]: item for item in plan["sessions"]}
    actual_orders = [item.session_order for item in response.session_messages]
    if len(set(actual_orders)) != len(actual_orders):
        errors.append("session messages contain duplicate session_order values")
    if set(actual_orders) != set(expected_sessions):
        errors.append("session messages must reference every exact final session order once")
    for item in response.session_messages:
        expected = expected_sessions.get(item.session_order)
        if expected is None:
            continue
        if expected.get("session_type") == "study" and expected.get("subject") not in item.message:
            errors.append(f"session {item.session_order} omits its exact subject name")
        claims = _minute_values(item.message)
        if claims and claims != {expected["duration_minutes"]}:
            kind = expected.get("session_type", "session")
            errors.append(f"{kind} duration changed in session {item.session_order}")

    unscheduled = [item["subject"] for item in plan.get("unscheduled_subjects", [])]
    if unscheduled and response.unscheduled_message is None:
        errors.append("unscheduled_message is required when subjects are unscheduled")
    if not unscheduled and response.unscheduled_message is not None:
        errors.append("unscheduled_message must be null when no subject is unscheduled")
    if response.unscheduled_message:
        for subject in unscheduled:
            if subject not in response.unscheduled_message:
                errors.append(f"unscheduled_message omits {subject}")
        warning_minutes = {
            value for warning in plan.get("warnings", []) for value in _minute_values(warning)
        }
        if not _minute_values(response.unscheduled_message).issubset(
            allowed_plan_minutes | warning_minutes
        ):
            errors.append("unscheduled_message changes or invents a duration")

    allowed_ids = {
        item["record_id"] for item in grounding_context.get("retrieved_record_summaries", [])
    }
    for text in _all_text(response):
        if MEDICAL_PATTERN.search(text):
            errors.append("unsupported medical language detected")
        if MARKDOWN_PATTERN.search(text):
            errors.append("Markdown is not allowed in JSON strings")
        if _non_english_text(text):
            errors.append("output must be English-only")
        invented = set(RECORD_ID_PATTERN.findall(text)) - allowed_ids
        if invented:
            errors.append(f"invented retrieved record IDs: {', '.join(sorted(invented))}")

    supplied_text = json.dumps(grounding_context, ensure_ascii=True).lower()
    output_text = " ".join(_all_text(response)).lower()
    for term in UNSUPPORTED_INPUT_TERMS:
        if term in output_text and term not in supplied_text:
            errors.append(f"unsupported invented user input: {term}")
    all_subjects = [
        item.get("name", "")
        for item in grounding_context.get("original_user_input", {}).get("subjects", [])
    ]
    for subject in all_subjects:
        if not subject:
            continue
        fact_pattern = re.compile(
            rf"\b{re.escape(subject)}\b\s+(?:is an?|covers|teaches|develops|improves|causes|"
            rf"involves|studies|explores|examines|deals with|concerns)\b",
            re.IGNORECASE,
        )
        for text in _all_text(response):
            match = fact_pattern.search(text)
            if match and match.group(0).lower() not in supplied_text:
                errors.append(f"unsupported subject-specific fact about {subject}")

    expected_warning_count = len(plan.get("warnings", []))
    if len(response.warnings) != expected_warning_count:
        errors.append(
            f"warnings count changed: expected {expected_warning_count}, got {len(response.warnings)}"
        )
    source_warning_minutes = {
        value for warning in plan.get("warnings", []) for value in _minute_values(warning)
    }
    output_warning_minutes = {
        value for warning in response.warnings for value in _minute_values(warning)
    }
    if not output_warning_minutes.issubset(source_warning_minutes):
        errors.append("warning text changes or invents a duration")
    return ValidationResult(not errors, tuple(dict.fromkeys(errors)), response)
