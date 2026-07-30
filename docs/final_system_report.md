# ErgoStudy AI final system report

## Release outcome

ErgoStudy AI `1.0.0-prototype` is a completed local competition prototype. It accepts student ratings and available time, retrieves source-traceable study guidance, calculates a one-day plan with deterministic Python rules, optionally adapts future timing from normalized sensor observations, and returns validated JSON through FastAPI. A local Ollama model may improve the English wording, but it never calculates or changes the plan.

The prototype is not production-ready. It has no Flutter UI, deployment configuration, authentication, public networking, or direct hardware integration.

## Final architecture

The implemented request path is:

1. FastAPI and Pydantic validate the request.
2. The query analyzer and controlled alias resolver interpret the subject and topic.
3. `all-MiniLM-L6-v2` creates a query embedding.
4. the frozen `alias_plus_dense` retriever searches the persistent Chroma collection.
5. Python rules score subjects, allocate study minutes, and schedule sessions and breaks.
6. The sensor adapter optionally changes only future timing and break actions.
7. The optional `qwen3:4b-instruct` wording layer receives the final structured result.
8. Output validation accepts the model response or returns the deterministic English fallback.
9. FastAPI validates the response and returns API version `v1` JSON for Flutter.

The deterministic plan remains authoritative throughout this path.

## Dataset and sources

Dataset version `1.0.0-prototype` contains 477 retrievable records from 29 recorded sources, plus 96 separate retrieval-evaluation queries. The corpus contains 277 canonical records and 200 controlled synthetic alias records:

| Family | Records |
| --- | ---: |
| Subject profiles | 80 |
| Topic profiles | 141 |
| Study strategies | 24 |
| Session templates | 18 |
| Sensor interventions | 14 |
| Subject aliases | 200 |

The final Stage 3 validator reported zero errors and zero warnings. Source IDs, evidence labels, licensing notes, review state, limitations, and synthetic lineage remain attached to the applicable records. Synthetic aliases introduce naming variants, not new evidence claims.

## Embeddings and retrieval

Stage 4 selected the `minilm_plain` configuration: `sentence-transformers/all-MiniLM-L6-v2`, pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. It produces 384-dimensional normalized embeddings and fits the local prototype constraints. The persistent `ergostudy-knowledge-1-0-0` Chroma collection contains exactly 477 records.

The frozen `alias_plus_dense` retriever was selected on the development split and evaluated once on the sealed 32-query final split. Final results were:

| Metric | Result |
| --- | ---: |
| Recall@1 | 0.7241 |
| Recall@3 | 0.8448 |
| Recall@5 | 0.8621 |
| Recall@10 | 0.8966 |
| MRR@10 | 0.8728 |
| NDCG@10 | 0.8673 |
| Document-family Hit@5 | 1.0000 |
| Subject-family Hit@5 | 1.0000 |

There were no zero-result queries. Two queries did not retrieve a labelled relevant record in the measured ranks. These results describe the fixed evaluation set, not universal retrieval quality.

## Planner and sensor behavior

The subject score is `0.35 × priority + 0.25 × workload + 0.20 × difficulty + 0.20 × knowledge gap`, where knowledge gap is derived from current understanding. Scores decide academic priority. The allocator fits only useful study blocks into the requested window. The scheduler then splits allocations into 20-to-60-minute sessions and inserts configured 5- or 10-minute breaks; study and break minutes both count toward the total available time.

Sensor adaptation uses normalized application fields rather than raw hardware data. The prototype thresholds are 45 minutes for long sitting, 60 minutes for extended sitting, 10 minutes for sustained poor posture, and 30 seconds for a stale reading. These are versioned product settings pending hardware confirmation and user testing. They are not medical thresholds. Adaptation may insert or extend a movement break, shorten or defer a future study session, and show calm repositioning wording. It does not change scores, subject priority, retrieved record IDs, or protected completed/current work. Missing, stale, invalid, disconnected, or disabled observations preserve the timer-based plan.

## Grounded generation

The only permitted local model is `qwen3:4b-instruct` through Ollama. It receives structured plan and retrieval context, uses temperature zero and schema-constrained JSON, and has one correction attempt. Validation checks exact subjects, allocations, sessions, sensor content, and safe language.

The earlier six-case Stage 7 evaluation produced six valid final responses: one valid first response, two corrected responses, and three deterministic fallbacks. Numeric preservation, grounding validation, and sensor safety all passed. In Stage 9, a prewarmed real request completed in 17,610.080 ms through `local_llm_corrected`. A simulated timeout returned HTTP 200 with `OLLAMA_TIMEOUT` and a validated deterministic fallback. Explanation is optional and is not part of the primary planning path.

## API surface

The local FastAPI service exposes:

- `GET /api/v1/health`
- `GET /api/v1/readiness`
- `POST /api/v1/plans`
- `POST /api/v1/plans/adapt`
- `POST /api/v1/plans/full`
- `POST /api/v1/explanations`
- `POST /api/v1/plans/full-with-explanation`

The first three planning endpoints do not construct or call an Ollama client. Invalid requests use a consistent safe error envelope. Responses contain UUID4 request IDs and do not expose local paths, caches, stack traces, secrets, or raw Ollama errors.

## Final end-to-end evaluation

All 12 required scenarios passed: school and university plans, custom subjects/topics, `CS` and `Stats` aliases, a short window with an unscheduled subject, unknown-subject fallback, long-sitting adaptation, leaning/pressure adaptation, stale-sensor fallback, a real Ollama explanation, timeout fallback, and an invalid request. Every applicable response passed checks for time limits, positive durations, consistent totals, valid record IDs, preserved subject ordering, unchanged deterministic allocation values, safe language, and transport privacy.

## Performance results

Measurements used FastAPI `TestClient` on the local development/presentation machine. Each warm endpoint received one warm-up followed by 20 measured requests. p95 uses nearest rank.

| Operation | Average ms | Median ms | p95 ms | Min ms | Max ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warm `/plans` | 113.010 | 114.041 | 121.351 | 100.626 | 121.363 |
| Warm `/plans/adapt` | 3.893 | 3.885 | 4.371 | 3.020 | 4.860 |
| Warm `/plans/full` | 114.440 | 113.779 | 129.181 | 102.375 | 132.237 |
| Warm readiness | 5.045 | 4.410 | 5.170 | 3.612 | 18.007 |
| Deterministic explanation fallback | 5.444 | 5.628 | 6.612 | 3.567 | 6.943 |

Cold initialization to ready was 7,807.915 ms, the first plan request was 220.419 ms, and the combined measured lifecycle was 8,036.636 ms. Five simultaneous deterministic plan requests all returned HTTP 200 with the same deterministic plan ID in 784.756 ms total. This is a small correctness smoke, not a production load or capacity claim.

The earlier observation that `/plans` appeared slower than `/plans/full` was not reproduced: repeated averages were 113.010 ms and 114.440 ms respectively. No implementation change was justified.

## Final validation

- Stage 3 validator: 477 records, 29 sources, zero errors, zero warnings.
- Repository unit tests: 171 passed.
- End-to-end scenarios: 12 passed.
- OpenAPI: version 3.1 with all seven required paths.
- Notebook: valid notebook JSON; four code cells executed successfully.
- Python compilation: passed for `api`, `src`, and `scripts`.
- Final JSON, JSONL, and CSV validation: passed.
- Secret, machine-path, whitespace, and package-content audits: passed at handoff creation.

## Safety decisions

- Python owns all scores, allocations, timings, priorities, and sensor actions.
- The LLM can only phrase a validated result.
- Unknown subjects use a visible knowledge fallback rather than invented evidence.
- Missing or unreliable sensor data causes no sensor-based change.
- Sensor wording is non-medical and does not diagnose, treat, or predict injury.
- Optional model failure is a normal HTTP 200 fallback, not plan failure.
- The API is local-only and must not be exposed publicly in its current form.

## Limitations

- The dataset is curriculum-neutral and does not provide course-specific tutoring content.
- Retrieval evaluation uses 32 sealed final queries; it is useful but small.
- Some reuse terms remain paraphrase-only or constrained by their recorded licenses.
- Independent expert review is still recommended before public use.
- Planner and sensor thresholds are prototype product settings requiring user testing.
- No raw sensor transport, calibration, or confirmed production hardware contract is implemented.
- Ollama latency depends strongly on the presentation machine and model warm state.
- The API has no authentication, TLS, rate limiting, telemetry, or production hardening.
- Flutter UI implementation and deployment are outside this release.

## Recommended future work

After the prototype is reviewed, the next sensible work is Flutter integration against the frozen API contract, usability testing, confirmation of the real sensor contract, independent content and safety review, broader retrieval evaluation, and production security design. These are recommendations, not features included in `1.0.0-prototype`.
