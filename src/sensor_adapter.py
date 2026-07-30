"""Deterministically adapt an existing daily plan from normalized sensor observations."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.planner_models import DailyStudyPlan
from src.sensor_models import AdaptationAction, AdaptedStudyPlan, SensorObservation
from src.sensor_policy import SensorPolicy, default_sensor_policy


LEANING_DIRECTIONS = frozenset(
    {"leaning_left", "leaning_right", "leaning_forward", "leaning_backward"}
)


def _as_plan_dict(plan: DailyStudyPlan | dict[str, Any]) -> dict[str, Any]:
    if isinstance(plan, DailyStudyPlan):
        values = plan.to_dict()
    elif isinstance(plan, dict):
        values = copy.deepcopy(plan)
    else:
        raise ValueError("plan must be a DailyStudyPlan or an object")
    if not isinstance(values.get("plan_id"), str) or not values["plan_id"]:
        raise ValueError("plan must contain a non-empty plan_id")
    total = values.get("total_available_minutes")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        raise ValueError("plan must contain positive total_available_minutes")
    sessions = values.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("plan sessions must be a list")
    seen_orders: set[int] = set()
    for session in sessions:
        if not isinstance(session, dict):
            raise ValueError("every plan session must be an object")
        order = session.get("order")
        duration = session.get("duration_minutes")
        if not isinstance(order, int) or isinstance(order, bool) or order <= 0 or order in seen_orders:
            raise ValueError("session order values must be unique positive integers")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            raise ValueError("session duration_minutes must be a positive integer")
        if session.get("session_type") not in {"study", "break"}:
            raise ValueError("session_type must be study or break")
        seen_orders.add(order)
    return values


def _fallback_reason(observation: SensorObservation, policy: SensorPolicy) -> tuple[str, str]:
    if observation.observation_status == "invalid":
        return "invalid_observation", "The sensor observation could not be used; the timer-based plan remains active."
    if observation.connection_status != "connected":
        return "sensor_connection_unavailable", "Sensor data is unavailable; the timer-based plan remains active."
    if observation.observation_status == "missing":
        return "missing_observation", "No current sensor observation is available; the timer-based plan remains active."
    if observation.observation_status == "stale":
        return "stale_observation", "The sensor observation is not current; the timer-based plan remains active."
    if observation.observation_status != "valid":
        return "unknown_observation_status", "Sensor status is unavailable; the timer-based plan remains active."
    age = observation.reading_age_seconds
    if age is not None and age > policy.thresholds.stale_reading_age_seconds:
        return "stale_observation", "The sensor observation is not current; the timer-based plan remains active."
    return "", ""


def _clock_after(value: str | None, minutes: int) -> str | None:
    if value is None:
        return None
    try:
        return (datetime.strptime(value, "%H:%M") + timedelta(minutes=minutes)).strftime("%H:%M")
    except ValueError:
        return None


def _recalculate_orders_and_times(sessions: list[dict[str, Any]]) -> None:
    start = next((item.get("start_time") for item in sessions if item.get("start_time") is not None), None)
    current = start
    for order, session in enumerate(sessions, start=1):
        session["order"] = order
        session["start_time"] = current
        current = _clock_after(current, session["duration_minutes"])


def _adapted_id(
    original_plan_id: str,
    observation: SensorObservation,
    policy: SensorPolicy,
    sessions: list[dict[str, Any]],
    triggers: list[str],
) -> str:
    payload = {
        "original_plan_id": original_plan_id,
        "observation": observation.to_dict(),
        "policy": policy.to_dict(),
        "sessions": sessions,
        "triggers": triggers,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "adapted-" + hashlib.sha256(encoded).hexdigest()[:16]


def _result(
    plan: dict[str, Any],
    observation: SensorObservation,
    policy: SensorPolicy,
    *,
    mode: str,
    severity: str,
    triggers: list[str],
    actions: list[AdaptationAction],
    sessions: list[dict[str, Any]],
    notice: str,
    warnings: list[str] | None = None,
) -> AdaptedStudyPlan:
    study = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "study")
    breaks = sum(item["duration_minutes"] for item in sessions if item["session_type"] == "break")
    total = study + breaks
    original_study = sum(
        item["duration_minutes"] for item in plan["sessions"] if item["session_type"] == "study"
    )
    applied = sessions != plan["sessions"] or bool(actions)
    original_warnings = plan.get("warnings", [])
    if not isinstance(original_warnings, list) or not all(
        isinstance(item, str) for item in original_warnings
    ):
        raise ValueError("plan warnings must be a list of strings when provided")
    combined_warnings = tuple(dict.fromkeys([*original_warnings, *(warnings or ())]))
    return AdaptedStudyPlan(
        original_plan_id=plan["plan_id"],
        adapted_plan_id=_adapted_id(plan["plan_id"], observation, policy, sessions, triggers),
        adaptation_applied=applied,
        mode=mode,
        severity=severity,
        triggers=tuple(triggers),
        actions=tuple(actions),
        sessions=tuple(copy.deepcopy(sessions)),
        total_available_minutes=plan["total_available_minutes"],
        total_study_minutes=study,
        total_break_minutes=breaks,
        total_planned_minutes=total,
        unallocated_minutes=plan["total_available_minutes"] - total,
        deferred_study_minutes=max(0, original_study - study),
        sensor_notice=notice,
        warnings=combined_warnings,
        sensor_policy_version=policy.sensor_policy_version,
    )


class SensorPlanAdapter:
    """Apply bounded sensor rules without changing academic planning decisions."""

    def __init__(self, project_root: Path, *, policy: SensorPolicy | None = None) -> None:
        self.project_root = project_root.resolve()
        self.policy = policy or default_sensor_policy(self.project_root)

    def adapt(
        self,
        plan: DailyStudyPlan | dict[str, Any],
        observation_values: SensorObservation | dict[str, Any],
    ) -> AdaptedStudyPlan:
        plan_values = _as_plan_dict(plan)
        observation = (
            observation_values
            if isinstance(observation_values, SensorObservation)
            else SensorObservation.from_dict(observation_values)
        )
        original_sessions = copy.deepcopy(plan_values["sessions"])
        if not observation.sensor_enabled:
            return _result(
                plan_values,
                observation,
                self.policy,
                mode="non_sensor",
                severity="normal",
                triggers=[],
                actions=[],
                sessions=original_sessions,
                notice="Sensor support is off; the timer-based plan remains active.",
            )

        fallback_trigger, fallback_notice = _fallback_reason(observation, self.policy)
        if fallback_trigger:
            return _result(
                plan_values,
                observation,
                self.policy,
                mode="non_sensor",
                severity="data_unavailable",
                triggers=[fallback_trigger],
                actions=[],
                sessions=original_sessions,
                notice=fallback_notice,
            )

        triggers: list[str] = []
        sitting = observation.continuous_sitting_minutes or 0
        if sitting >= self.policy.thresholds.extended_continuous_sitting_minutes:
            triggers.append("extended_continuous_sitting")
            severity = "high"
            break_duration = self.policy.adaptation.extended_movement_break_minutes
        elif sitting >= self.policy.thresholds.long_continuous_sitting_minutes:
            triggers.append("long_continuous_sitting")
            severity = "medium"
            break_duration = self.policy.adaptation.standard_movement_break_minutes
        else:
            severity = "normal"
            break_duration = 0

        posture_triggered = (
            observation.posture_direction in LEANING_DIRECTIONS
            and (observation.poor_posture_duration_minutes or 0)
            >= self.policy.thresholds.sustained_poor_posture_minutes
        )
        if posture_triggered:
            triggers.append(observation.posture_direction or "unknown")
            if severity == "normal":
                severity = "medium"
            break_duration = max(
                break_duration, self.policy.adaptation.standard_movement_break_minutes
            )
        if observation.pressure_imbalance_detected:
            triggers.append("pressure_imbalance")
            if severity == "normal":
                severity = "low"
            break_duration = max(
                break_duration, self.policy.adaptation.standard_movement_break_minutes
            )

        if not triggers:
            return _result(
                plan_values,
                observation,
                self.policy,
                mode="sensor",
                severity="normal",
                triggers=[],
                actions=[],
                sessions=original_sessions,
                notice="Sensor observation is available; the original plan remains active.",
            )

        cooldown_active = (
            observation.minutes_since_last_reminder is not None
            and observation.minutes_since_last_reminder
            < self.policy.adaptation.reminder_cooldown_minutes
        )
        sitting_triggered = triggers[0] in {
            "extended_continuous_sitting",
            "long_continuous_sitting",
        }
        if cooldown_active and not sitting_triggered:
            return _result(
                plan_values,
                observation,
                self.policy,
                mode="sensor",
                severity=severity,
                triggers=triggers,
                actions=[],
                sessions=original_sessions,
                notice="A recent posture reminder is still active; the original plan remains in place.",
            )

        sessions = copy.deepcopy(original_sessions)
        protected_index = -1
        if observation.current_session_order is not None:
            matches = [
                index
                for index, item in enumerate(sessions)
                if item["order"] == observation.current_session_order
            ]
            if not matches:
                return _result(
                    plan_values,
                    observation,
                    self.policy,
                    mode="sensor",
                    severity=severity,
                    triggers=triggers,
                    actions=[],
                    sessions=original_sessions,
                    notice="The current session could not be matched; the original plan remains active.",
                    warnings=["No adaptation was applied because current_session_order was not in the plan."],
                )
            protected_index = matches[0]
            elapsed = observation.elapsed_session_minutes
            if elapsed is not None and elapsed > sessions[protected_index]["duration_minutes"]:
                raise ValueError("elapsed_session_minutes cannot exceed the current session duration")
        protected_session_ids = {id(item) for item in sessions[: protected_index + 1]}

        next_study_index = next(
            (
                index
                for index, item in enumerate(sessions)
                if index > protected_index and item["session_type"] == "study"
            ),
            None,
        )
        if next_study_index is None:
            return _result(
                plan_values,
                observation,
                self.policy,
                mode="sensor",
                severity=severity,
                triggers=triggers,
                actions=[],
                sessions=original_sessions,
                notice="No upcoming study block is available to adapt; the current plan remains active.",
                warnings=["No upcoming study session was available for sensor adaptation."],
            )

        actions: list[AdaptationAction] = []
        # Extended sitting always shortens the next sufficiently long upcoming session.
        if "extended_continuous_sitting" in triggers:
            target = sessions[next_study_index]
            reducible = max(
                0,
                target["duration_minutes"]
                - self.policy.adaptation.minimum_adapted_study_session_minutes,
            )
            reduction = min(self.policy.adaptation.next_session_reduction_minutes, reducible)
            if reduction:
                target["duration_minutes"] -= reduction
                actions.append(
                    AdaptationAction(
                        action="shorten_next_session",
                        minutes_reduced=reduction,
                        session_order=target["order"],
                        reason="The next long study block was reduced after extended continuous sitting.",
                    )
                )

        preceding_break = next_study_index - 1
        if (
            preceding_break > protected_index
            and sessions[preceding_break]["session_type"] == "break"
        ):
            existing = sessions[preceding_break]["duration_minutes"]
            if existing < break_duration:
                sessions[preceding_break]["duration_minutes"] = break_duration
                sessions[preceding_break]["reason"] = "Sensor-guided movement and repositioning break."
                actions.append(
                    AdaptationAction(
                        action="extend_movement_break",
                        duration_minutes=break_duration,
                        session_order=sessions[preceding_break]["order"],
                        reason="An upcoming timer-based break was extended for movement.",
                    )
                )
            else:
                actions.append(
                    AdaptationAction(
                        action="use_existing_movement_break",
                        duration_minutes=existing,
                        session_order=sessions[preceding_break]["order"],
                        reason="The upcoming timer-based break already provides enough movement time.",
                    )
                )
        else:
            movement_break = {
                "order": 0,
                "session_type": "break",
                "duration_minutes": break_duration,
                "reason": "Sensor-guided movement and repositioning break.",
                "start_time": None,
                "subject": None,
                "topic": None,
                "cognitive_demand": None,
                "recommended_methods": [],
                "retrieved_record_ids": [],
                "used_fallback": False,
            }
            sessions.insert(next_study_index, movement_break)
            actions.append(
                AdaptationAction(
                    action="insert_movement_break",
                    duration_minutes=break_duration,
                    reason=(
                        "Extended continuous sitting was detected."
                        if "extended_continuous_sitting" in triggers
                        else "A short movement or repositioning break is appropriate."
                    ),
                )
            )

        if posture_triggered or observation.pressure_imbalance_detected:
            actions.append(
                AdaptationAction(
                    action="show_posture_reminder",
                    reason="Adjust your sitting position to a comfortable, balanced posture.",
                )
            )

        # Fit all changes inside the original available window without touching protected sessions.
        overflow = sum(item["duration_minutes"] for item in sessions) - plan_values["total_available_minutes"]
        if overflow > 0:
            for item in sessions[protected_index + 1 :]:
                if overflow <= 0:
                    break
                if item["session_type"] != "study":
                    continue
                reducible = max(
                    0,
                    item["duration_minutes"]
                    - self.policy.adaptation.minimum_adapted_study_session_minutes,
                )
                reduction = min(overflow, reducible)
                if reduction:
                    item["duration_minutes"] -= reduction
                    overflow -= reduction
                    actions.append(
                        AdaptationAction(
                            action="shorten_future_session",
                            minutes_reduced=reduction,
                            session_order=item["order"],
                            reason="A future study block was shortened to keep the plan within its time window.",
                        )
                    )

        if overflow > 0:
            removable = [
                index
                for index, item in enumerate(sessions)
                if index > protected_index and item["session_type"] == "study"
            ]
            for index in reversed(removable):
                if overflow <= 0:
                    break
                removed = sessions.pop(index)
                overflow -= removed["duration_minutes"]
                actions.append(
                    AdaptationAction(
                        action="defer_future_session",
                        minutes_reduced=removed["duration_minutes"],
                        session_order=removed["order"],
                        reason="A future study block was deferred because the adjusted window was full.",
                    )
                )

        # Remove timer breaks that no longer sit between study blocks after a deferral.
        cleaned: list[dict[str, Any]] = []
        for item in sessions:
            if item["session_type"] == "break" and cleaned and cleaned[-1]["session_type"] == "break":
                if id(cleaned[-1]) in protected_session_ids:
                    cleaned.append(item)
                    continue
                if "Sensor-guided" in item["reason"]:
                    cleaned[-1] = item
                elif (
                    "Sensor-guided" not in cleaned[-1]["reason"]
                    and item["duration_minutes"] > cleaned[-1]["duration_minutes"]
                ):
                    cleaned[-1] = item
                continue
            cleaned.append(item)
        while (
            cleaned
            and cleaned[-1]["session_type"] == "break"
            and "Sensor-guided" not in cleaned[-1]["reason"]
            and id(cleaned[-1]) not in protected_session_ids
        ):
            cleaned.pop()
        sessions = cleaned
        _recalculate_orders_and_times(sessions)

        if "extended_continuous_sitting" in triggers:
            notice = "Take an extended movement break before the next study block."
        elif "long_continuous_sitting" in triggers:
            notice = "Take a short movement break before the next study block."
        else:
            notice = "Take a short movement break and adjust your sitting position."
        warnings: list[str] = []
        original_study = sum(
            item["duration_minutes"]
            for item in original_sessions
            if item["session_type"] == "study"
        )
        adapted_study = sum(
            item["duration_minutes"] for item in sessions if item["session_type"] == "study"
        )
        if adapted_study < original_study:
            deferred = original_study - adapted_study
            warnings.append(
                f"{deferred} study minute{'s were' if deferred != 1 else ' was'} deferred to keep the plan within its available time."
            )
        return _result(
            plan_values,
            observation,
            self.policy,
            mode="sensor",
            severity=severity,
            triggers=triggers,
            actions=actions,
            sessions=sessions,
            notice=notice,
            warnings=warnings,
        )


def adapt_study_plan(
    project_root: Path,
    plan: DailyStudyPlan | dict[str, Any],
    observation: SensorObservation | dict[str, Any],
    *,
    policy: SensorPolicy | None = None,
) -> AdaptedStudyPlan:
    """Convenience function for one deterministic adaptation."""
    return SensorPlanAdapter(project_root, policy=policy).adapt(plan, observation)
