# Stage 6A deterministic daily planner report

## Scope

Stage 6A adds a deterministic one-day planner for students who do not use a sensor. It accepts available minutes, an optional start time, an optional preferred session length, and per-subject ratings. It does not add sensor adaptation, a local LLM, FastAPI, Flutter integration, multi-day planning, medical guidance, new embeddings, index rebuilding, or retrieval retuning.

## Planner algorithm

The planner validates the request, retrieves knowledge for every subject, calculates scores, selects only subjects that can receive meaningful time, allocates study minutes proportionally, splits them into bounded sessions, orders the sessions, and inserts breaks. Total available time includes both study and breaks.

The subject score is:

```text
0.35 * priority
+ 0.25 * workload
+ 0.20 * difficulty
+ 0.20 * (6 - current_understanding)
```

All inputs share the 1-to-5 scale. These weights are prototype planning choices, not research-proven universal values. They and every time boundary live in `config/planner_config.json`; configuration loading rejects weights that do not sum to 1.0.

Subjects are sorted by score and normalized name. A subject is not forced into the plan when its minimum session plus the conservative break reserve cannot fit. Every selected subject first receives the configured 20-minute minimum. Remaining study minutes are distributed by score with deterministic largest-remainder rounding.

Allocations are split near the preferred or default session length while remaining between 20 and 60 minutes. Sessions from different subjects are interleaved. After a high-demand session, a lower-demand session is selected next when one is available. A 10-minute break follows high-demand work and a 5-minute break follows lower-demand work, except after the last session. These durations are configurable product constraints, not universal scientific facts.

## Retrieval integration

`KnowledgeAdapter` uses the frozen Stage 5 `RetrievalService` and metadata filters for four record families:

- `subject_profile`
- `topic_profile`
- `study_strategy`
- `session_template`

Exact subject names and controlled aliases are resolved before dense results are accepted. Context-sensitive aliases such as `CS` and `Stats` are safe in the explicit subject-input field. An alias resolving to multiple subject profiles is not silently collapsed.

Each study session retains the relevant corpus record IDs. Internal retrieval text and local file paths are not returned. Evaluation labels, held-out query records, and sealed final-test artifacts are not used by planner code.

When retrieval is unavailable, ambiguous, weak, or unknown, the planner uses the configured generic methods `active recall`, `guided practice`, and `self-check`. The subject-specific canonical name remains unset, the session is marked `used_fallback`, and a warning explains why. No subject-specific claim is invented.

## Determinism and response schema

Plan IDs are SHA-256 prefixes calculated from canonical JSON containing normalized request values and the full planner configuration. Identical normalized inputs and configuration produce identical IDs and plans.

The response includes available, study, break, planned, and unallocated minutes; scheduled and unscheduled subjects; ordered study and break sessions; methods; short reasons; retrieved record IDs; warnings; and the planner version. Start times are computed in 24-hour `HH:MM` format when supplied and remain `null` otherwise.

## Demo results

The committed demo artifacts contain four inputs and their generated plans:

| Example | Available | Study | Breaks | Allocation summary |
| --- | ---: | ---: | ---: | --- |
| School evening | 150 | 135 | 15 | Mathematics 60, Biology 41, History 34 |
| University afternoon | 240 | 205 | 35 | Calculus 2 78, CS 67, Stats 60 |
| Short window | 30 | 30 | 0 | Chemistry 30; English Literature unscheduled |
| Unknown subject | 60 | 55 | 5 | Two generic fallback sessions totaling 55 |

The school and university examples use real record IDs from the existing 477-record Chroma collection. The unknown example clearly marks fallback behavior. The short example demonstrates that the planner prefers one meaningful session over forcing two undersized sessions.

## Validation

Stage 6A validation passed 42 focused tests covering planner models, scoring, allocation, scheduling, orchestration, fallback, determinism, traceability, persistent-Chroma integration, and the existing alias, query-analysis, and retrieval behavior required by the planner. A separate boundary sweep passed 2,073 combinations across every available time from 30 through 720 minutes and preferred sessions of 20, 40, and 60 minutes.

The demo generator reproduced byte-identical output with SHA-256 `f6f543c5b297bb6c88e6cf3339e0f5b4b0eded2f50e30918c130c1312b6d3962`. Python compilation, JSON parsing, six notebook code cells, repeated-output assertions, total-time assertions, and Git whitespace checks passed. No embedding benchmark was run and the Chroma collection was not rebuilt.

See `notebooks/06_daily_planner.ipynb` for the score calculation, retrieved record IDs, time allocations, ordered school and university plans, total-time assertion, and repeated-output assertion.
