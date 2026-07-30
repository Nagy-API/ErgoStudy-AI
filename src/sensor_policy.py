"""Load and validate the configurable prototype sensor-adaptation policy."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SensorThresholds:
    long_continuous_sitting_minutes: int
    extended_continuous_sitting_minutes: int
    sustained_poor_posture_minutes: int
    stale_reading_age_seconds: int


@dataclass(frozen=True)
class SensorAdaptationRules:
    standard_movement_break_minutes: int
    extended_movement_break_minutes: int
    next_session_reduction_minutes: int
    minimum_adapted_study_session_minutes: int
    reminder_cooldown_minutes: int


@dataclass(frozen=True)
class SensorPolicy:
    sensor_policy_version: str
    policy_status: str
    thresholds: SensorThresholds
    adaptation: SensorAdaptationRules

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SensorPolicy":
        if not isinstance(values, dict):
            raise ValueError("sensor policy must be an object")
        version = values.get("sensor_policy_version")
        status = values.get("policy_status")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("sensor_policy_version must be a non-empty string")
        if not isinstance(status, str) or "non-medical" not in status.lower():
            raise ValueError("policy_status must clearly label the parameters as non-medical")
        threshold_values = values.get("thresholds")
        adaptation_values = values.get("adaptation")
        if not isinstance(threshold_values, dict) or not isinstance(adaptation_values, dict):
            raise ValueError("thresholds and adaptation must be objects")

        def positive(source: dict[str, Any], name: str) -> int:
            value = source.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
            return value

        thresholds = SensorThresholds(
            long_continuous_sitting_minutes=positive(
                threshold_values, "long_continuous_sitting_minutes"
            ),
            extended_continuous_sitting_minutes=positive(
                threshold_values, "extended_continuous_sitting_minutes"
            ),
            sustained_poor_posture_minutes=positive(
                threshold_values, "sustained_poor_posture_minutes"
            ),
            stale_reading_age_seconds=positive(
                threshold_values, "stale_reading_age_seconds"
            ),
        )
        adaptation = SensorAdaptationRules(
            standard_movement_break_minutes=positive(
                adaptation_values, "standard_movement_break_minutes"
            ),
            extended_movement_break_minutes=positive(
                adaptation_values, "extended_movement_break_minutes"
            ),
            next_session_reduction_minutes=positive(
                adaptation_values, "next_session_reduction_minutes"
            ),
            minimum_adapted_study_session_minutes=positive(
                adaptation_values, "minimum_adapted_study_session_minutes"
            ),
            reminder_cooldown_minutes=positive(
                adaptation_values, "reminder_cooldown_minutes"
            ),
        )
        if thresholds.extended_continuous_sitting_minutes <= thresholds.long_continuous_sitting_minutes:
            raise ValueError("extended sitting threshold must exceed the long sitting threshold")
        if adaptation.extended_movement_break_minutes < adaptation.standard_movement_break_minutes:
            raise ValueError("extended movement break must not be shorter than the standard break")
        return cls(version.strip(), status.strip(), thresholds, adaptation)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_sensor_policy(path: Path) -> SensorPolicy:
    """Load a sensor policy from UTF-8 JSON."""
    return SensorPolicy.from_dict(json.loads(path.read_text(encoding="utf-8")))


def default_sensor_policy(project_root: Path) -> SensorPolicy:
    return load_sensor_policy(project_root / "config" / "sensor_policy.json")
