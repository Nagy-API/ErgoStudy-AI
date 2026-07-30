# Project Plan

Each stage should leave evidence that its completion criteria were met. A stage is not complete merely because code was written.

## 1. Environment and scaffold

**Goal:** Establish a safe, documented, Windows-friendly repository and record the local development capabilities.

**Expected outputs:** Repository structure, project rules, overview documentation, architecture draft, environment notebook, minimal dependency file, and environment report.

**Completion criteria:** The requested files exist; the notebook is valid and runs without future RAG dependencies; Python files compile; Git tracks the intended scaffold; detected tools and missing tools are documented; no model or dataset has been downloaded.

## 2. Dataset design and source strategy

**Goal:** Define the knowledge domains, record schema, metadata, source quality rules, licensing constraints, and validation process before collecting content.

**Expected outputs:** Dataset specification, source-selection rubric, citation and license fields, controlled vocabularies, sample records, and a validation checklist.

**Completion criteria:** Every factual record can retain source traceability; health-related scope and disclaimers are defined; reviewers approve the schema and source policy; synthetic expansion is explicitly separated from validated source content.

## 3. Dataset creation and validation

**Goal:** Build a small, high-quality educational knowledge dataset from approved sources and verify it before expansion.

**Expected outputs:** Raw source records, normalized interim data, validated processed data, provenance logs, validation scripts, and a dataset summary.

**Completion criteria:** Required fields pass automated validation; citations resolve to recorded sources; duplicates and unsupported claims are addressed; manual review samples meet the agreed quality threshold; licenses permit the intended use.

## 4. Embeddings and ChromaDB

**Goal:** Select a suitable local embedding model and persist validated dataset embeddings in ChromaDB.

**Expected outputs:** Model-selection record, embedding pipeline, ChromaDB collection schema, metadata filters, persistence configuration, and reproducible indexing script.

**Completion criteria:** Indexing is repeatable; document IDs and metadata remain traceable to source records; persistence survives a restart; embedding speed and storage use are measured on the target computer.

## 5. Retrieval and retrieval evaluation

**Goal:** Retrieve relevant source-grounded guidance using semantic search and metadata constraints.

**Expected outputs:** Retrieval module, representative query set, relevance labels, evaluation metrics, failure analysis, and tuned retrieval settings.

**Completion criteria:** Retrieval meets agreed relevance targets on the evaluation set; metadata filtering is tested; returned passages include citations; known failure cases and fallback behavior are documented.

## 6. Deterministic daily planning engine

**Goal:** Convert validated study inputs into a predictable one-day schedule with allocations, sessions, and breaks.

**Expected outputs:** Input models, planning rules, allocation algorithm, rescheduling behavior, structured plan schema, unit tests, and decision explanations.

**Completion criteria:** The same input produces the same schedule; time totals and constraints are correct; invalid and edge-case inputs are handled; rescheduling preserves completed work; tests cover the documented rules.

## 7. Sensor-aware adaptation

**Goal:** Adapt sessions and breaks from documented sensor readings without inventing hardware behavior or unsafe health claims.

**Expected outputs:** Sensor data contract, calibration assumptions, posture and pressure mappings, adaptation rules, missing-data behavior, simulated fixtures, and tests.

**Completion criteria:** Rules use confirmed hardware fields and units; sensor-free behavior is unchanged; stale, missing, and invalid readings fail safely; adaptations are deterministic and explainable; simulated scenarios pass tests.

## 8. Local LLM and grounded generation

**Goal:** Use a local language model to explain plans and retrieved guidance while keeping factual claims grounded and schedule decisions deterministic.

**Expected outputs:** Local runtime configuration, model-selection record, prompt templates, context and citation format, structured-output validation, and hallucination tests.

**Completion criteria:** The chosen model runs within measured hardware limits; generated output follows the schema; citations correspond to retrieved records; the model cannot silently change planner decisions; unsupported-answer behavior is tested.

## 9. FastAPI integration

**Goal:** Expose validation, planning, adaptation, retrieval, and grounded explanation through a stable local API for Flutter.

**Expected outputs:** FastAPI application, request and response schemas, error contract, configuration, API tests, OpenAPI documentation, and Flutter-facing examples.

**Completion criteria:** Endpoints return validated structured JSON; sensor and non-sensor flows pass integration tests; errors are consistent; local startup is documented; no secrets or paid services are required.

## 10. Full system evaluation and demo

**Goal:** Measure the complete system and prepare a reproducible demonstration of both operating modes.

**Expected outputs:** End-to-end scenarios, quality and performance results, latency and resource measurements, limitations, demo script, and final documentation.

**Completion criteria:** The full pipeline passes agreed functional tests; retrieval and planner results meet their thresholds; target-hardware latency is recorded; both modes have reproducible demos; limitations and future work are clearly reported.
