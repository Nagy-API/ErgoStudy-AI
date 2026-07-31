"""Stable template response used when local generation is unavailable or invalid."""

from __future__ import annotations

from src.response_models import AllocationExplanation, GroundedResponse, SessionMessage


def deterministic_grounded_response(context: dict) -> GroundedResponse:
    plan = context["final_plan"]
    allocations = plan["subject_allocations"]
    study_minutes = plan["total_study_minutes"]
    break_minutes = plan["total_break_minutes"]
    subject_count = len(allocations)
    subject_word = "subject" if subject_count == 1 else "subjects"
    summary = (
        f"Today's plan includes {study_minutes} minutes of study across "
        f"{subject_count} {subject_word}, with {break_minutes} minutes of breaks."
    )
    allocation_explanations = tuple(
        AllocationExplanation(
            subject=item["subject"],
            allocated_minutes=item["allocated_minutes"],
            reason=item["reason"],
        )
        for item in allocations
    )
    messages: list[SessionMessage] = []
    for session in plan["sessions"]:
        order = session["order"]
        duration = session["duration_minutes"]
        if session["session_type"] == "break":
            message = f"Session {order}: Take the planned {duration}-minute break."
        else:
            methods = session.get("recommended_methods", [])
            method_text = f" using {', '.join(methods)}" if methods else ""
            message = (
                f"Session {order}: Study {session['subject']} for {duration} minutes"
                f"{method_text}."
            )
        messages.append(SessionMessage(order, message))
    unscheduled = plan.get("unscheduled_subjects", [])
    unscheduled_message = None
    if unscheduled:
        parts = [f"{item['subject']}: {item['reason']}" for item in unscheduled]
        unscheduled_message = "Unscheduled subjects: " + " ".join(parts)
    return GroundedResponse(
        summary=summary,
        allocation_explanations=allocation_explanations,
        session_messages=tuple(messages),
        unscheduled_message=unscheduled_message,
        warnings=tuple(plan.get("warnings", [])),
    )
