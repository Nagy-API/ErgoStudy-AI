"""Validated JSON-compatible models for sensor-aware plan adaptation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


POSTURE_DIRECTIONS = frozenset(
    {
        "upright",
        "leaning_left",
        "leaning_right",
        "leaning_forward",
        "leaning_backward",
        "unknown",
    }
)
CONNECTION_STATUSES = frozenset({"connected", "disconnected", "unknown"})
OBSERVATION_STATUSES = frozenset({"valid", "missing", "stale", "invalid", "unknown"})


def _optional_non_negative_number(values: dict[str, Any], name: str) -> int | None:
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer or null")
    return value


def _optional_choice(values: dict[str, Any], name: str, choices: frozenset[str]) -> str | None:
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or value not in choices:
        options = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {options}")
    return value


@dataclass(frozen=True)
class SensorObservation:
    """One normalized application-level observation; no raw hardware units are accepted."""

    sensor_enabled: bool
    connection_status: str | None = None
    observation_status: str | None = None
    continuous_sitting_minutes: int | None = None
    poor_posture_duration_minutes: int | None = None
    posture_direction: str | None = None
    pressure_imbalance_detected: bool | None = None
    reading_age_seconds: int | None = None
    current_session_order: int | None = None
    elapsed_session_minutes: int | None = None
    minutes_since_last_reminder: int | None = None

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SensorObservation":
        if not isinstance(values, dict):
            raise ValueError("sensor observation must be an object")
        enabled = values.get("sensor_enabled")
        if not isinstance(enabled, bool):
            raise ValueError("sensor_enabled must be a boolean")
        pressure = values.get("pressure_imbalance_detected")
        if pressure is not None and not isinstance(pressure, bool):
            raise ValueError("pressure_imbalance_detected must be a boolean or null")
        current_order = _optional_non_negative_number(values, "current_session_order")
        if current_order == 0:
            raise ValueError("current_session_order must be a positive integer or null")
        return cls(
            sensor_enabled=enabled,
            connection_status=_optional_choice(
                values, "connection_status", CONNECTION_STATUSES
            ),
            observation_status=_optional_choice(
                values, "observation_status", OBSERVATION_STATUSES
            ),
            continuous_sitting_minutes=_optional_non_negative_number(
                values, "continuous_sitting_minutes"
            ),
            poor_posture_duration_minutes=_optional_non_negative_number(
                values, "poor_posture_duration_minutes"
            ),
            posture_direction=_optional_choice(
                values, "posture_direction", POSTURE_DIRECTIONS
            ),
            pressure_imbalance_detected=pressure,
            reading_age_seconds=_optional_non_negative_number(values, "reading_age_seconds"),
            current_session_order=current_order,
            elapsed_session_minutes=_optional_non_negative_number(
                values, "elapsed_session_minutes"
            ),
            minutes_since_last_reminder=_optional_non_negative_number(
                values, "minutes_since_last_reminder"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptationAction:
    """One concise explanation of a deterministic timeline change."""

    action: str
    reason: str | None = None
    duration_minutes: int | None = None
    minutes_reduced: int | None = None
    session_order: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class AdaptedStudyPlan:
    """Stable result returned by the sensor adaptation layer."""

    original_plan_id: str
    adapted_plan_id: str
    adaptation_applied: bool
    mode: str
    severity: str
    triggers: tuple[str, ...]
    actions: tuple[AdaptationAction, ...]
    sessions: tuple[dict[str, Any], ...]
    total_available_minutes: int
    total_study_minutes: int
    total_break_minutes: int
    total_planned_minutes: int
    unallocated_minutes: int
    deferred_study_minutes: int
    sensor_notice: str
    warnings: tuple[str, ...] = field(default_factory=tuple)
    sensor_policy_version: str = "1.0.0-prototype"

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_plan_id": self.original_plan_id,
            "adapted_plan_id": self.adapted_plan_id,
            "adaptation_applied": self.adaptation_applied,
            "mode": self.mode,
            "severity": self.severity,
            "triggers": list(self.triggers),
            "actions": [item.to_dict() for item in self.actions],
            "sessions": [dict(item) for item in self.sessions],
            "total_available_minutes": self.total_available_minutes,
            "total_study_minutes": self.total_study_minutes,
            "total_break_minutes": self.total_break_minutes,
            "total_planned_minutes": self.total_planned_minutes,
            "unallocated_minutes": self.unallocated_minutes,
            "deferred_study_minutes": self.deferred_study_minutes,
            "sensor_notice": self.sensor_notice,
            "warnings": list(self.warnings),
            "sensor_policy_version": self.sensor_policy_version,
        }
