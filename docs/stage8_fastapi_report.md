# Stage 8 FastAPI integration report

## Outcome

Stage 8 exposes the validated ErgoStudy planner, optional normalized sensor adaptation, and optional grounded English wording through a local versioned FastAPI service. The three normal planning endpoints do not construct or call an Ollama client. Explanation work is isolated in separate endpoints and returns a validated deterministic response with HTTP 200 when local generation is unavailable, slow, malformed, or invalid after correction.

## Implementation

The API uses strict Pydantic models with forbidden unknown fields, UUID4 request correlation, one consistent safe error envelope, environment-driven local CORS, and FastAPI lifespan initialization. Startup validates dataset artifacts, planner configuration, sensor policy, generation configuration, the cached selected embedding model, and the existing persistent Chroma collection. It initializes reusable retrieval, planner, and sensor services without preloading Ollama or running benchmarks.

The explanation default changed from the Stage 7 benchmark-oriented 180 seconds to a user-facing 30 seconds. Configuration permits safe per-request overrides from 1 through 60 seconds. One deadline covers the initial response and the single existing correction attempt. No Stage 7 output schema or generation-validation rule changed.

## API surface

- `GET /api/v1/health`
- `GET /api/v1/readiness`
- `POST /api/v1/plans`
- `POST /api/v1/plans/adapt`
- `POST /api/v1/plans/full`
- `POST /api/v1/explanations`
- `POST /api/v1/plans/full-with-explanation`

The complete transport contract is in `docs/api_contract.md`. Flutter addresses, examples, model suggestions, timeout guidance, and fallback handling are in `docs/flutter_integration_guide.md`.

## Validation summary

All 35 focused Stage 8 tests and all 171 repository tests pass. OpenAPI 3.1 generation contains all seven required paths and 28 schemas. The notebook parses and executes all seven code cells. The six demo request/response pairs validate as JSON, Python compilation passes, and the production lifespan smoke opens the existing cached embedding model and Chroma collection successfully.

One measured local smoke flow returned `/plans` in 464.772 ms, `/plans/adapt` in 3.377 ms, and `/plans/full` in 210.115 ms after startup. The one permitted real explanation smoke request reached the configured deadline at 30,011.231 ms and returned HTTP 200 with a validated deterministic fallback and `OLLAMA_TIMEOUT`. The persistent Chroma collection was not rebuilt. No embedding benchmark, retrieval retuning, model download, or six-case LLM benchmark ran.

This remains a local prototype measurement and is not evidence of production-scale throughput.
