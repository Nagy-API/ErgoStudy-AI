# API contract

Base URL: `http://127.0.0.1:8000/api/v1`. Content type is JSON. Request models are strict: unknown fields are rejected with HTTP 422.

## Active endpoints

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | Process health |
| GET | `/readiness` | Deterministic component status plus separate Ollama status |
| POST | `/plans` | `{plan, request_id, processing_time_ms, fallback, api_version}` |
| POST | `/plans/full` | `{original_plan, final_sessions, request_id, processing_time_ms, fallback, api_version}` |
| POST | `/explanations` | Validated wording or deterministic fallback for an existing plan |
| POST | `/plans/full-with-explanation` | Combined demonstration response |

## Plan request

```json
{
  "total_available_minutes": 90,
  "preferred_start_time": "16:00",
  "preferred_session_length": 40,
  "subjects": [
    {
      "name": "Mathematics",
      "topics": ["Equations"],
      "difficulty": 4,
      "priority": 5,
      "workload": 4,
      "current_understanding": 2
    }
  ]
}
```

`preferred_start_time`, `preferred_session_length`, and `topics` are optional. Ratings are integers from 1 to 5. Available time is 30 to 720 minutes. Obsolete sensor fields are unknown fields and fail validation.

## Plan semantics

The plan reports subject allocations, ordered study/break sessions, methods, retrieved record IDs, deterministic reasons, warnings, fallback status, and unscheduled subjects. Session minutes and totals are internally consistent and never exceed available time. Repeating the same active request and configuration returns the same plan and plan ID.

## Explanation semantics

`POST /explanations` accepts `plan` and optional `timeout_seconds`. Its `grounded_response` contains `summary`, `allocation_explanations`, `session_messages`, `unscheduled_message`, and `warnings`. It contains no hardware-specific fields. `generation_mode` is `local_llm`, `local_llm_corrected`, or `deterministic_fallback`.

Ollama timeout or unavailability is a successful fallback response, not plan failure. Error responses use `{error: {code, message, details}, request_id}` and do not expose local paths or stack traces.
