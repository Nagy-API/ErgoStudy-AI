# ErgoStudy API contract

## Scope and versioning

The local API is rooted at `/api/v1`. The deterministic planner owns subject allocation, session order, durations, breaks, methods, and retrieval record IDs. The sensor adapter may change only the bounded future timeline allowed by its existing policy. Ollama is used only by the two explanation-capable endpoints.

Interactive OpenAPI documentation is available at `/docs`, ReDoc at `/redoc`, and the generated OpenAPI 3.1 document at `/openapi.json`.

## Endpoints

| Method | Path | Purpose | Calls Ollama |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | Basic process health | No |
| GET | `/api/v1/readiness` | Dataset, Chroma, embedding, configuration, service, and separate Ollama status | Version probe only |
| POST | `/api/v1/plans` | Create a deterministic one-day plan | No |
| POST | `/api/v1/plans/adapt` | Adapt an existing plan from a normalized sensor observation | No |
| POST | `/api/v1/plans/full` | Create and optionally adapt a plan | No |
| POST | `/api/v1/explanations` | Explain an existing deterministic plan | Yes, with fallback |
| POST | `/api/v1/plans/full-with-explanation` | Slower demo-only full pipeline | Yes, with fallback |

## Planning input

`total_available_minutes` is an integer from 30 through 720. `preferred_start_time`, when supplied, uses 24-hour `HH:MM`. `preferred_session_length`, when supplied, is an integer from 20 through 60. The `subjects` list contains one through 30 unique subject names. Every rating is a strict integer from 1 through 5. A subject may contain up to 20 unique topic strings, each no longer than 160 characters.

Unknown JSON fields are rejected. Duplicate subject names follow the existing planner behavior and are rejected after case and whitespace normalization.

## Sensor input

The API accepts only the normalized application-level contract already implemented by Stage 6B. It does not accept raw voltages, pressure matrices, calibration values, or device-specific units. Omitting `sensor_observation` from `/plans/adapt` produces the existing safe missing-observation result. Omitting it from `/plans/full` skips adaptation.

## Explanation behavior

The default explanation timeout is 30 seconds. A request may override it only within the configured 1-to-60-second range. The deadline covers the initial model call and the one permitted correction call together. Stage 7 generation and validation rules are unchanged.

Timeout, connection failure, malformed model output, and failed correction all return HTTP 200 with:

```json
{
  "generation_mode": "deterministic_fallback",
  "model_status": "unavailable",
  "validation_status": "fallback_valid",
  "fallback_reason_code": "OLLAMA_UNAVAILABLE"
}
```

The full response also contains the validated grounded response, attempt count, generation latency, request ID, and API version. Non-sensitive reason codes are `OLLAMA_TIMEOUT`, `OLLAMA_UNAVAILABLE`, `MODEL_VALIDATION_FAILED`, and `GENERATION_FAILED`.

## Error envelope

Validation and service errors use one envelope:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is invalid.",
    "details": [
      {
        "field": "subjects.0.priority",
        "message": "Input should be less than or equal to 5"
      }
    ]
  },
  "request_id": "886654c1-e092-4033-a5f8-6a11ac39b57c"
}
```

Responses never include stack traces, local paths, cache locations, secrets, evaluation data, or raw Ollama errors.

## Request IDs

Each request receives a random UUID version 4. It is safe for correlation, does not encode user data, and is returned in the JSON response and `X-Request-ID` header. Plan and adapted-plan IDs remain deterministic hashes owned by the existing pipeline.

## CORS and lifecycle

The defaults allow `http://localhost` and `http://127.0.0.1` without credentials. Configure comma-separated origins with `ERGOSTUDY_CORS_ORIGINS`. Configure credentials with `ERGOSTUDY_CORS_ALLOW_CREDENTIALS`; wildcard origins are rejected when credentials are enabled.

FastAPI lifespan validates local artifacts and configurations, checks the persistent Chroma collection and cached embedding model, and initializes reusable retrieval, planning, and sensor services. It does not preload Ollama or run benchmarks.
