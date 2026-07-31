# FastAPI report

The local API exposes health, readiness, deterministic planning, convenience planning, explanation, and combined demonstration endpoints under `/api/v1`. Strict Pydantic models reject unknown fields. Planning endpoints do not construct or wait for Ollama.

OpenAPI contains exactly six active paths and no sensor endpoint or schema. Requests containing obsolete sensor fields receive HTTP 422, while the removed adaptation path returns 404. Responses use request IDs, safe error envelopes, and no local paths or stack traces.
