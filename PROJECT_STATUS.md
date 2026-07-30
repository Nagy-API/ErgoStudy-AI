# Project status

## Release

- Project: ErgoStudy AI — Posture-Aware Daily Study Planner
- Version: `1.0.0-prototype`
- Status: competition prototype complete
- API: local FastAPI `v1`
- Production readiness: not production-ready

## Completed stages

All planned prototype stages are complete:

1. Environment and repository scaffold.
2. Dataset design and source strategy.
3. Deterministic 477-record dataset creation and validation.
4. Local embedding selection and persistent Chroma index.
5. Frozen hybrid retrieval and sealed final evaluation.
6. Deterministic subject scoring, time allocation, sessions, and breaks.
7. Deterministic normalized sensor adaptation with safe fallback.
8. Grounded local-LLM wording with strict validation and deterministic fallback.
9. Versioned FastAPI integration for a future Flutter client.
10. Final end-to-end evaluation, demo, packaging, and handoff.

Flutter UI implementation and deployment have not started and are outside this release.

## Final implementation checkpoint

The completed pipeline validates user input, resolves controlled aliases, retrieves source-traceable records with the frozen `alias_plus_dense` configuration, calculates academic priority and time with deterministic Python, builds ordered sessions and breaks, optionally adapts future timing from normalized sensor observations, optionally asks local `qwen3:4b-instruct` for English wording, validates or replaces that wording, and returns strict FastAPI JSON.

The three primary planning endpoints never construct or call Ollama. Missing or unreliable sensor input leaves the timer-based plan unchanged. Unknown knowledge uses an explicit fallback. LLM failure returns a validated deterministic response with HTTP 200.

## Frozen data and retrieval facts

- Dataset version: `1.0.0-prototype`.
- Corpus: 477 retrievable records, including 277 canonical records and 200 controlled aliases.
- Sources: 29 recorded and used.
- Evaluation queries: 96, separated from the corpus.
- Selected embedding: `sentence-transformers/all-MiniLM-L6-v2`, pinned revision, 384 dimensions.
- Chroma collection: `ergostudy-knowledge-1-0-0`, 477 records.
- Final retrieval: Recall@5 `0.8621`, MRR@10 `0.8728`, NDCG@10 `0.8673`, document-family Hit@5 `1.0000`, subject-family Hit@5 `1.0000`.

No embedding benchmark, dataset rebuild, retrieval retuning, dataset expansion, new model, planner redesign, or sensor-policy redesign occurred in the final stage.

## Final Stage 9 checkpoint

- Stage 3 validator: zero errors and zero warnings.
- End-to-end scenarios: 12 passed, 0 failed.
- Repository tests: 171 passed.
- OpenAPI: 3.1 document with all seven required versioned paths.
- Notebook: valid JSON; four code cells executed successfully.
- Python compilation: passed.
- Warm `/plans`: average `113.010 ms`, median `114.041 ms`, p95 `121.351 ms` over 20 requests.
- Warm `/plans/adapt`: average `3.893 ms`, median `3.885 ms`, p95 `4.371 ms` over 20 requests.
- Warm `/plans/full`: average `114.440 ms`, median `113.779 ms`, p95 `129.181 ms` over 20 requests.
- Warm readiness: average `5.045 ms`, median `4.410 ms`, p95 `5.170 ms` over 20 requests.
- Deterministic explanation fallback: average `5.444 ms`, p95 `6.612 ms` over 20 requests.
- Cold lifecycle: `7,807.915 ms` to ready, `220.419 ms` first plan request, `8,036.636 ms` combined.
- Concurrent correctness smoke: 5 of 5 deterministic requests succeeded with one plan ID in `784.756 ms` total.
- Prewarmed real Ollama explanation: `local_llm_corrected` in `17,610.080 ms`.
- Simulated timeout: validated `OLLAMA_TIMEOUT` deterministic fallback.

The repeated measurement did not reproduce the earlier single-request result in which `/plans` appeared slower than `/plans/full`; no implementation defect or planner change was justified.

## Final artifacts

Stage 9 adds the final scenario inputs/outputs, evaluation/performance/validation results, end-to-end notebook, no-download Ollama prewarm, demo runner, package builder, consolidated report, competition script, discussion guide, handoff guide, and project file map. The source ZIP and its external manifest are generated after the final commit and remain ignored by Git.

## Remaining limitations

- Curriculum-neutral knowledge rather than course-specific tutoring lessons.
- Small sealed final retrieval set.
- Prototype planner and sensor parameters still need user testing.
- No confirmed raw sensor hardware transport/calibration contract.
- Optional local generation may be slow despite prewarming.
- No independent production security, accessibility, content, or clinical review.
- No authentication, TLS, rate limiting, deployment, Flutter UI, or cloud service.

Future work is documented but is not part of the completed `1.0.0-prototype` handoff.
