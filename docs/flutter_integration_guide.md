# Flutter integration guide

## Local addresses

- Android emulator: `http://10.0.2.2:8000`
- Windows desktop and Flutter web: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Start the local service from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_api.ps1
```

Do not expose this prototype publicly. It has no authentication, TLS termination, rate limiting, or production hardening.

## Endpoint choice

Use `/api/v1/plans` for a normal plan. Use `/api/v1/plans/adapt` when an existing plan receives a new normalized observation. Use `/api/v1/plans/full` when the app has both initial study inputs and an optional observation. These three endpoints are deterministic and never wait for Ollama.

Use `/api/v1/explanations` only when natural-language wording is wanted. `/api/v1/plans/full-with-explanation` is intended for demonstrations and is slower than `/plans/full`.

## Complete non-sensor request

```json
{
  "total_available_minutes": 30,
  "subjects": [
    {
      "name": "Mathematics",
      "topics": [],
      "difficulty": 4,
      "priority": 5,
      "workload": 4,
      "current_understanding": 2
    }
  ]
}
```

## Complete plan response

The IDs and measured latency vary by request and local data. All other fields shown are part of the response contract.

```json
{
  "plan": {
    "plan_id": "plan-0a10c9587c02f9e7",
    "total_available_minutes": 30,
    "total_study_minutes": 30,
    "total_break_minutes": 0,
    "total_planned_minutes": 30,
    "unallocated_minutes": 0,
    "scheduled_subjects": [
      {
        "subject": "Mathematics",
        "canonical_subject": "Mathematics",
        "score": 4.35,
        "allocated_study_minutes": 30,
        "session_count": 1,
        "reason": "Scheduled because of high priority, high workload, high difficulty, and a large knowledge gap.",
        "retrieved_record_ids": ["subject-mathematics-cross-level-v1"],
        "used_fallback": false
      }
    ],
    "unscheduled_subjects": [],
    "sessions": [
      {
        "order": 1,
        "session_type": "study",
        "duration_minutes": 30,
        "reason": "Scheduled because of high priority, high workload, high difficulty, and a large knowledge gap.",
        "start_time": null,
        "subject": "Mathematics",
        "topic": null,
        "cognitive_demand": "high",
        "recommended_methods": ["active recall", "guided practice", "self-check"],
        "retrieved_record_ids": ["subject-mathematics-cross-level-v1"],
        "used_fallback": false
      }
    ],
    "warnings": [],
    "planner_version": "1.0.0-prototype"
  },
  "request_id": "ed6cb330-bc7e-4670-90c1-64f5d7c66f64",
  "processing_time_ms": 8.214,
  "fallback": {
    "used": false,
    "reason_codes": [],
    "subjects": []
  },
  "api_version": "v1"
}
```

## Complete sensor request

Send the exact plan object returned above as `plan`:

```json
{
  "plan": {
    "plan_id": "plan-0a10c9587c02f9e7",
    "total_available_minutes": 30,
    "total_study_minutes": 30,
    "total_break_minutes": 0,
    "total_planned_minutes": 30,
    "unallocated_minutes": 0,
    "scheduled_subjects": [{"subject":"Mathematics","canonical_subject":"Mathematics","score":4.35,"allocated_study_minutes":30,"session_count":1,"reason":"Scheduled because of high priority, high workload, high difficulty, and a large knowledge gap.","retrieved_record_ids":["subject-mathematics-cross-level-v1"],"used_fallback":false}],
    "unscheduled_subjects": [],
    "sessions": [{"order":1,"session_type":"study","duration_minutes":30,"reason":"Scheduled because of high priority, high workload, high difficulty, and a large knowledge gap.","start_time":null,"subject":"Mathematics","topic":null,"cognitive_demand":"high","recommended_methods":["active recall","guided practice","self-check"],"retrieved_record_ids":["subject-mathematics-cross-level-v1"],"used_fallback":false}],
    "warnings": [],
    "planner_version": "1.0.0-prototype"
  },
  "sensor_observation": {
    "sensor_enabled": true,
    "connection_status": "connected",
    "observation_status": "valid",
    "continuous_sitting_minutes": 50,
    "poor_posture_duration_minutes": 12,
    "posture_direction": "leaning_right",
    "pressure_imbalance_detected": true,
    "reading_age_seconds": 5,
    "current_session_order": 1,
    "elapsed_session_minutes": 20
  }
}
```

For a non-sensor adaptation, send `"sensor_observation": {"sensor_enabled": false}`. If the observation is missing, stale, invalid, or disconnected, the API returns the existing timer-based plan with a calm `sensor_notice` and a trigger explaining the fallback.

## Complete explanation fallback response

```json
{
  "grounded_response": {
    "summary": "Today's plan includes 30 minutes of study across 1 subject, with 0 minutes of breaks.",
    "allocation_explanations": [
      {
        "subject": "Mathematics",
        "allocated_minutes": 30,
        "reason": "Scheduled because of high priority, high workload, high difficulty, and a large knowledge gap."
      }
    ],
    "session_messages": [
      {
        "session_order": 1,
        "message": "Session 1: Study Mathematics for 30 minutes using active recall, guided practice, self-check."
      }
    ],
    "sensor_message": null,
    "unscheduled_message": null,
    "warnings": []
  },
  "generation_mode": "deterministic_fallback",
  "model_status": "unavailable",
  "validation_status": "fallback_valid",
  "fallback_reason_code": "OLLAMA_UNAVAILABLE",
  "attempt_count": 0,
  "generation_latency_ms": 1.104,
  "request_id": "d3df7f40-bbee-4e48-aed8-4d38f755e947",
  "api_version": "v1"
}
```

Complete generated requests and responses for health, readiness, planning, sensor adaptation, the full deterministic flow, and explanation fallback are also committed in `data/processed/api_demo_requests.json` and `data/processed/api_demo_responses.json`.

## Suggested Dart models

Keep transport models separate from UI state. A practical structure is:

```dart
class PlanRequest { int totalAvailableMinutes; String? preferredStartTime; int? preferredSessionLength; List<SubjectInput> subjects; }
class SubjectInput { String name; List<String> topics; int difficulty; int priority; int workload; int currentUnderstanding; }
class PlanResponse { DailyStudyPlan plan; String requestId; double processingTimeMs; FallbackInfo fallback; String apiVersion; }
class DailyStudyPlan { String planId; List<ScheduledSubject> scheduledSubjects; List<PlannedSession> sessions; List<String> warnings; }
class SensorObservation { bool sensorEnabled; String? connectionStatus; String? observationStatus; int? readingAgeSeconds; }
class ExplanationResponse { GroundedResponse groundedResponse; String generationMode; String modelStatus; String validationStatus; String? fallbackReasonCode; }
class ApiError { ErrorBody error; String requestId; }
```

Generate the complete field mappings from `/openapi.json` or mirror the examples above. Preserve nullable fields rather than replacing them with empty strings.

## Timeouts and error handling

- Use a short client timeout, such as 5 seconds, for `/plans`, `/plans/adapt`, and `/plans/full` after local startup.
- Use at least 35 seconds for `/explanations` when the server uses its 30-second default.
- Use a similarly long timeout for the demo-only full-with-explanation endpoint.
- Parse non-2xx responses as the documented `ApiError` envelope and show its readable message.
- Log `request_id` for support, but do not show stack traces or internal details.
- Treat `generation_mode == "deterministic_fallback"` as a successful explanation. The plan is still valid; a small optional UI indicator may say local AI wording was unavailable.
- Retry deterministic calls only for connection failures. Do not automatically retry a slow explanation because it may duplicate expensive local work.
