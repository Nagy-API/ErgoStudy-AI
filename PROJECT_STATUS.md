# Project status

ErgoStudy AI `1.0.0-prototype` is a completed local one-day study-planning prototype. The current AI scope is study input validation, MiniLM/ChromaDB retrieval, deterministic scheduling with timer-based breaks, optional local explanation, and validated FastAPI JSON.

The physical product still includes sensors, but hardware and Flutter teams own them. The AI backend receives and processes no sensor data, and all users receive the same AI planner features.

## Current checkpoint

- Active API: six endpoints; no adaptation endpoint or sensor schema.
- Corpus: 463 records from 23 sources; no sensor records.
- Evaluation corpus: 91 queries; fresh deterministic split of 61 development and 30 final queries.
- Final retrieval: Recall@5 `0.9038`, MRR@10 `0.9274`, nDCG@10 `0.9198`, document-family Hit@5 `1.0000`, subject-family Hit@5 `1.0000`.
- Chroma: 463 records with complete ID, document, metadata, manifest, and persistence verification.
- Planner scoring, configurable bounds, allocation, scheduling, normal breaks, fallbacks, and deterministic IDs remain unchanged.
- Optional `qwen3:4b-instruct` only explains the plan. Strict validation, numeric preservation, medical-diagnosis protection, timeout handling, and deterministic fallback remain active.

## Limits

The project is not production-ready. Flutter implementation, hardware behavior, deployment, authentication, TLS, rate limiting, accessibility review, and production security remain outside this repository.
