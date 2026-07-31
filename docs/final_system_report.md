# Final system report

## Outcome

ErgoStudy AI `1.0.0-prototype` is a completed local personalized one-day study planner. It validates student study input, retrieves source-traceable learning guidance, creates a deterministic schedule with normal timer-based breaks, optionally explains that schedule with local Ollama, and returns validated FastAPI JSON.

The physical product still contains sensors, but hardware and Flutter teams own them. The AI backend does not receive, validate, store, retrieve, interpret, or act on sensor data. Hardware owners and non-owners receive the same AI planner features.

## Data and retrieval

The cleaned corpus has 463 records from 23 used sources: 80 subject profiles, 141 topic profiles, 24 study strategies, 18 session templates, and 200 controlled aliases. There are 263 canonical and 200 synthetic alias records. Dataset validation reports zero errors and warnings.

The already-selected cached `sentence-transformers/all-MiniLM-L6-v2` revision remains unchanged. No model was downloaded, benchmarked, or retuned. Removal of five obsolete queries required a fresh deterministic 91-query split: 61 development and 30 final queries.

| Current-scope final metric | Result |
| --- | ---: |
| Query count | 30 |
| Recall@5 | 0.9038 |
| MRR@10 | 0.9274 |
| nDCG@10 | 0.9198 |
| Document-family Hit@5 | 1.0000 |
| Subject-family Hit@5 | 1.0000 |

These results are for the new compatible split and must not be presented as a direct comparison with the old 32-query result.

The Chroma collection contains exactly 463 records. Reopen verification confirmed every ID, document, metadata projection, and manifest; missing and duplicate counts are zero. Direct cosine and Chroma top-10 ID sets matched for every development query.

## Planner and generation

The score remains `0.35 × priority + 0.25 × workload + 0.20 × difficulty + 0.20 × knowledge gap`. Allocation, session bounds, breaks, aliases, unknown-subject fallback, unscheduled subjects, and deterministic IDs are unchanged.

The optional `qwen3:4b-instruct` layer only phrases the finished plan. Exact schema validation, numeric preservation, one correction attempt, deterministic fallback, Ollama timeout handling, and general medical-diagnosis protection remain active.

## API

The active surface is `GET /health`, `GET /readiness`, `POST /plans`, `POST /plans/full`, `POST /explanations`, and `POST /plans/full-with-explanation`, all under `/api/v1`. OpenAPI contains no hardware-specific endpoint or schema. Deterministic planning never waits for Ollama.

## Limits

This remains a competition prototype: local-only, curriculum-neutral, without Flutter implementation, deployment, authentication, TLS, rate limiting, course-specific tutoring, or production hardening.
