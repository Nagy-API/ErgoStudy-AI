# Sensor Data Contract Draft

## Status

This is a design draft for discussion with the hardware and Flutter teams. It does not confirm units, thresholds, sampling rates, calibration, accuracy, device behavior, or clinical meaning. All fields under **Proposed fields** remain unconfirmed.

The planner works without a sensor. Missing, stale, unreliable, or invalid sensor data safely degrades to the non-sensor plan.

Stage 6B defines an application-level adapter contract below. It does not confirm the hardware transport fields in this draft or perform device-specific conversion.

## Stage 6B normalized application boundary

The deterministic adapter consumes values that an upstream application has already normalized. It accepts minutes, seconds, booleans, and categorical status values only:

| Field | Type | Meaning |
| --- | --- | --- |
| `sensor_enabled` | boolean | Required switch between sensor and non-sensor behavior. |
| `connection_status` | `connected`, `disconnected`, or `unknown` | Application-level connection state. |
| `observation_status` | `valid`, `missing`, `stale`, `invalid`, or `unknown` | Application validation result. |
| `continuous_sitting_minutes` | non-negative integer or null | Normalized continuous sitting duration. |
| `poor_posture_duration_minutes` | non-negative integer or null | Normalized duration for the supplied direction. |
| `posture_direction` | supported direction or null | `upright`, four leaning directions, or `unknown`. |
| `pressure_imbalance_detected` | boolean or null | Upstream normalized flag; no raw pressure values. |
| `reading_age_seconds` | non-negative integer or null | Reading freshness when available. |
| `current_session_order` | positive integer or null | Current timeline position used to protect past work. |
| `elapsed_session_minutes` | non-negative integer or null | Progress in the current protected session. |
| `minutes_since_last_reminder` | non-negative integer or null | Optional cooldown input. |

The adapter does not accept electrical readings, physical pressure units, calibration values, pressure arrays, or device-specific states. `config/sensor_policy.json` contains non-medical prototype product parameters pending user testing and hardware-team confirmation; they are not hardware facts or scientifically universal thresholds.

## Confirmed product-level concepts

The product scope confirms only that sensor-related input may eventually describe:

- continuous sitting duration;
- posture direction;
- pressure distribution or pressure imbalance;
- poor-posture duration;
- whether a smart sensor is available.

These are conceptual inputs, not a confirmed transport contract. No unit or numeric boundary is confirmed.

## Proposed envelope

The following top-level envelope is proposed:

| Field | Type | Status | Purpose |
| --- | --- | --- | --- |
| `sensor_available` | boolean | Confirmed concept; field name proposed | Whether the user reports a sensor is available. |
| `sensor_data` | object or null | Proposed | Latest normalized reading bundle. |
| `captured_at` | ISO 8601 string | Proposed | Reading timestamp for freshness checks. |
| `device_session_id` | string | Proposed | Correlates readings without exposing a device serial number. |
| `data_quality` | object | Proposed | Reliability and validation information. |
| `schema_version` | string | Proposed | Version negotiation between Flutter and backend. |

## Proposed observation fields

| Field | Proposed type | Confirmation required |
| --- | --- | --- |
| `continuous_sitting_duration` | number | Unit, reset event, clock source, precision, and maximum value. |
| `continuous_sitting_duration_unit` | enum | Candidate values might include `seconds` or `milliseconds`; no choice is confirmed. |
| `posture_direction` | enum or null | Exact directions, reference frame, and whether a neutral state exists. |
| `poor_posture_duration` | number or null | Unit, definition of poor posture, accumulation and reset rules. |
| `poor_posture_duration_unit` | enum or null | Must match confirmed hardware output. |
| `pressure_distribution` | array or object | Sensor count, ordering, units, normalization, calibration, and interpretation. |
| `pressure_imbalance` | number, enum, or object | Whether hardware computes it, its range, direction, unit, and confidence. |
| `confidence` | number or null | Meaning, range, and how it is calculated. |
| `status_flags` | array of strings | Hardware-defined quality or fault states. |

Field names are descriptive proposals. They must not be implemented as final API requirements until both teams approve them.

## Draft JSON: sensor unavailable

```json
{
  "schema_version": "sensor-draft-0.1",
  "sensor_available": false,
  "sensor_data": null
}
```

Expected behavior: create the normal non-sensor plan. Do not warn, reduce plan quality, or invent readings.

## Draft JSON: observation present

Values below demonstrate shape only. They are not real units or thresholds.

```json
{
  "schema_version": "sensor-draft-0.1",
  "sensor_available": true,
  "sensor_data": {
    "captured_at": "2026-07-30T14:30:00+03:00",
    "device_session_id": "example-session-not-a-device-id",
    "continuous_sitting_duration": 123,
    "continuous_sitting_duration_unit": "UNCONFIRMED_UNIT",
    "posture_direction": "UNCONFIRMED_DIRECTION",
    "poor_posture_duration": null,
    "poor_posture_duration_unit": null,
    "pressure_distribution": null,
    "pressure_imbalance": null,
    "confidence": null,
    "status_flags": [],
    "data_quality": {
      "state": "unknown",
      "reasons": ["Example only; hardware quality flags are not confirmed"]
    }
  }
}
```

Expected behavior in the current design: validate the envelope, then treat every unconfirmed unit or enum as unusable. Fall back to the non-sensor plan.

## Draft JSON: missing and unreliable data

```json
{
  "schema_version": "sensor-draft-0.1",
  "sensor_available": true,
  "sensor_data": {
    "captured_at": null,
    "device_session_id": "example-session-not-a-device-id",
    "continuous_sitting_duration": null,
    "continuous_sitting_duration_unit": null,
    "posture_direction": null,
    "poor_posture_duration": null,
    "poor_posture_duration_unit": null,
    "pressure_distribution": null,
    "pressure_imbalance": null,
    "confidence": null,
    "status_flags": ["UNCONFIRMED_EXAMPLE_FLAG"],
    "data_quality": {
      "state": "unreliable",
      "reasons": ["No usable reading"]
    }
  }
}
```

Expected behavior: record that no sensor adjustment was applied, use the non-sensor plan, and provide a neutral data-quality message only if useful to the user.

## Validation behavior

The future adapter should distinguish:

- **Absent:** sensor mode is off or `sensor_data` is null. Use the non-sensor plan.
- **Incomplete:** optional observations are null. Use only independently valid fields.
- **Unknown enum or unit:** reject that field; do not guess conversion or meaning.
- **Negative duration:** mark invalid and ignore it.
- **Non-finite number:** mark invalid and ignore it.
- **Timestamp missing:** data freshness cannot be established; ignore time-sensitive adjustment.
- **Stale:** use a team-confirmed freshness rule later; until then, no adjustment.
- **Unreliable:** ignore affected fields and preserve the normal plan.
- **Contradictory:** use a confirmed precedence rule later; until then, no adjustment.
- **Schema version unsupported:** return a clear validation error or negotiated fallback, as agreed with Flutter.

Invalid sensor data must not invalidate otherwise valid study inputs unless the final API contract explicitly requires sensor mode.

## Proposed intervention boundaries

Permitted non-medical outputs may include:

- an optional reminder to change position;
- an optional reminder to stand, stretch, or move briefly if appropriate;
- a proposal to take the next planned break sooner;
- a proposal to shorten a future session within planner constraints;
- a statement that no sensor adjustment was applied because data was unavailable or unreliable.

Stage 6B implements these responses with deterministic configurable rules. The values are adapter-level prototypes and do not confirm any hardware threshold.

The system must not:

- diagnose posture, pain, injury, disease, or musculoskeletal conditions;
- claim that pressure imbalance proves harm;
- prescribe treatment, therapy, medication, or exercises for a condition;
- instruct a user to continue through pain;
- use sensor data to make academic ability or difficulty judgments;
- present proposed fields or limits as hardware facts.

If a user reports severe, persistent, or concerning symptoms, the system should stop sensor-based optimization and use a short general message encouraging appropriate qualified help. The exact safety copy requires review and is not medical advice.

## Data minimization and privacy proposals

- Do not require a hardware serial number for planning.
- Prefer a short-lived session identifier.
- Send only fields required for a deterministic adaptation.
- Define retention separately; do not retain raw pressure arrays by default.
- Do not infer identity, body characteristics, diagnosis, or disability.
- Log validation outcomes without logging sensitive raw readings unless explicitly required and approved.

These are design proposals requiring product and privacy review.

## Questions for the hardware team

1. What exact fields does the device produce?
2. What are the units, numeric ranges, precision, and update frequency?
3. How is continuous sitting started, paused, and reset?
4. What directions or posture classes exist, and relative to which reference frame?
5. Does the device output raw pressure values, normalized values, or a derived imbalance signal?
6. How are pressure sensors ordered spatially?
7. What calibration is required per device or user?
8. What quality, fault, disconnected, warming-up, or out-of-range states exist?
9. Is confidence available, and what does it mean?
10. How should timestamps and clock drift be handled?
11. What data can be safely simulated for testing without implying real hardware behavior?
12. Which thresholds, if any, are implemented in firmware rather than the backend?

## Questions for the Flutter team

1. Will Flutter send individual readings, periodic summaries, or event notifications?
2. Who owns schema-version negotiation?
3. How is sensor availability distinguished from sensor permission, connection, and data validity?
4. Are timestamps generated by the device or phone?
5. How should partial data and validation warnings be displayed?
6. Can the app preserve a non-sensor plan when the sensor disconnects mid-session?
7. Which fields need localization later while API values remain English enums?
8. What is the retry and offline behavior?
9. Should raw sensor data ever be persisted on the phone or backend?
10. What user consent and privacy controls are required?

## Questions for joint confirmation

- Confirm the final JSON field names, units, enum values, nullability, and versioning policy.
- Confirm data freshness and reliability semantics.
- Confirm whether any threshold is a hardware fact, a product configuration, or an evidence-informed proposal.
- Confirm the exact fallback behavior and user-facing copy.
- Confirm test fixtures based on real device behavior before Stage 7.
