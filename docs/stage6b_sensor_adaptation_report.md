# Stage 6B Sensor Adaptation Report

## Scope

Stage 6B adds a deterministic adapter after the Stage 6A daily planner. The planner still owns academic scores, priorities, allocations, methods, record IDs, and initial ordering. The adapter receives normalized application-level observations and may change only future break placement, future break length, and future study duration. It does not communicate with hardware, use raw electrical or pressure units, plan across days, call an LLM, or provide diagnosis or treatment.

## Configurable prototype policy

`config/sensor_policy.json` contains versioned product parameters: 45 minutes for long continuous sitting, 60 minutes for extended sitting, 10 minutes for sustained directional posture, and 30 seconds for reading freshness. Movement breaks are 5 or 10 minutes, the extended-sitting reduction is 10 minutes, adapted study blocks remain at least 20 minutes, and posture reminders have a 15-minute cooldown.

These values are non-medical prototype planner parameters. They are not scientifically universal and remain pending user testing and hardware-team confirmation.

## Deterministic rules

The adapter applies this precedence:

1. Disabled or unusable sensor data keeps the original timer-based plan.
2. Extended continuous sitting requests a 10-minute movement break and reduces the next eligible study block by up to 10 minutes.
3. Long continuous sitting requests a 5-minute movement break.
4. Sustained left, right, forward, or backward leaning adds a calm repositioning reminder and a short break.
5. Pressure imbalance adds the same non-medical reminder and short break.
6. Simultaneous triggers share one break; the highest required break duration wins.

An existing upcoming timer break is reused or extended instead of duplicating it. A recent posture reminder suppresses another posture-only adjustment during the configured cooldown. No posture decision is made from disconnected, missing, stale, invalid, or unknown status data.

## Time and academic preservation

Sessions before and including the reported current session are protected. Additional break time first uses unallocated plan capacity. If the time window is full, upcoming study sessions are shortened without crossing the configured 20-minute minimum. If that is still insufficient, a future study block is deferred and its full duration is reported.

The adapted timeline never exceeds `total_available_minutes`. `deferred_study_minutes` is the difference between original and adapted study time. Academic reasons, subjects, topics, cognitive demand, recommended methods, fallback flags, and retrieved record IDs are copied unchanged. The input plan is deep-copied and is never mutated in place.

## Fallback and language safety

Sensor-disabled mode is labelled `non_sensor`. Disconnected, missing, stale, invalid, or unknown observations also use `non_sensor` and retain normal timer breaks. Notices are short and neutral, such as "The sensor observation is not current; the timer-based plan remains active."

Sensor notices recommend only movement or a comfortable position adjustment. They do not mention injury, diagnosis, disease, treatment, or clinical conclusions. Pressure imbalance is never described as proof of harm.

## Demo scenarios

The committed demo set covers sensor disabled, a normal observation, long sitting, extended sitting, combined right-lean and pressure imbalance, and missing-data fallback. It references the committed Stage 6A plans rather than regenerating retrieval output. `scripts/adapt_study_plan.py` produces stable JSON in `data/processed/sensor_demo_outputs.json` without model or network access.

## Reproducibility

The adapted plan ID hashes the original plan ID, normalized observation, complete sensor policy, resulting sessions, and ordered triggers. Repeated inputs therefore produce identical results and IDs. `notebooks/07_sensor_adaptation.ipynb` demonstrates the original plan, normal and triggered observations, fallback behavior, before-and-after timelines, time bounds, minimum session length, and determinism.

## Validation

The focused Stage 6B suite covers all 25 required cases, including every supported leaning direction, simultaneous triggers, bad-data fallbacks, current and partial sessions, break fit and shortening paths, whole-session deferral, minimum length, time preservation, academic-field integrity, determinism, and input immutability. Existing Stage 6A planner tests are retained as the integration baseline. No embedding benchmark, Chroma rebuild, model download, API work, or multi-day planning is part of this stage.
