# Project plan

The prototype stages are complete. This current-scope plan records the maintained system:

1. Validate structured study input with strict FastAPI/Pydantic schemas.
2. Resolve controlled subject aliases and retrieve source-traceable learning records with the cached MiniLM model and ChromaDB.
3. Score subjects with the fixed formula and allocate available study time deterministically.
4. Build ordered sessions with configured bounds and normal timer-based breaks.
5. Return explicit unknown-subject and unscheduled-subject behavior.
6. Optionally explain the completed plan with local Ollama, strict JSON validation, numeric preservation, and deterministic fallback.
7. Return versioned JSON suitable for Flutter.

Completion evidence includes deterministic dataset validation, a 463-record verified Chroma collection, a fresh non-sensor retrieval split and metrics, planner/generation/API tests, OpenAPI checks, demo artifacts, notebook execution, compilation, file-format scans, and a clean source handoff package.

The physical product's sensors belong to hardware and Flutter teams. No sensor contract, data, endpoint, retrieval content, plan adaptation, or differentiated AI feature is part of this plan. Do not redesign the planner, retune retrieval against historical evaluation results, download models automatically, or add replacement hardware features.
