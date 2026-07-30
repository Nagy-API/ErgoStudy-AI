# ErgoStudy AI project file map

## Start here

| File | Purpose |
| --- | --- |
| `README.md` | Final overview, setup, commands, endpoints, and limitations |
| `PROJECT_STATUS.md` | Completed-stage and release checkpoint |
| `PROJECT_PLAN.md` | Evidence-based stage plan and completion state |
| `AGENTS.md` | Repository working rules |

## Production Python

| Area | Main files | Responsibility |
| --- | --- | --- |
| API | `api/main.py`, `api/schemas.py`, `api/lifecycle.py` | Versioned endpoints, strict transport models, startup services |
| API support | `api/dependencies.py`, `api/error_handlers.py`, `api/settings.py` | Explanation deadline, fallback classification, errors, local settings |
| Retrieval | `src/retriever.py`, `src/query_analyzer.py`, `src/alias_resolver.py` | Frozen hybrid retrieval and controlled subject names |
| Vector store | `src/chroma_store.py`, `src/metadata_projection.py` | Persistent collection, traceable metadata, safe rebuild boundaries |
| Planner | `src/daily_planner.py`, `src/subject_scoring.py`, `src/time_allocator.py`, `src/session_scheduler.py` | Score, allocate, order, and fit study sessions and breaks |
| Planner models | `src/planner_models.py`, `src/planner_config.py`, `src/knowledge_adapter.py` | Validated plan structures, configuration, retrieved guidance mapping |
| Sensor | `src/sensor_adapter.py`, `src/sensor_models.py`, `src/sensor_policy.py` | Normalized observations, bounded timing adaptation, safe fallback |
| Generation | `src/grounded_generator.py`, `src/local_llm_client.py`, `src/generation_validator.py` | Local Ollama request, correction, strict validation |
| Response grounding | `src/grounding_context.py`, `src/deterministic_response.py`, `src/response_models.py` | Allowed context, stable English fallback, output models |
| Dataset | `src/dataset_builder.py`, `src/dataset_validator.py`, `src/dataset_io.py` | Deterministic corpus build and validation |
| Embedding evaluation | `src/embedding_models.py`, `src/embedding_evaluator.py`, `src/retrieval_metrics.py` | Frozen Stage 4/5 evaluation utilities; not rerun in Stage 9 |

## Configuration

| File | Purpose |
| --- | --- |
| `config/planner_config.json` | Planner weights, time rules, retrieval thresholds, fallback methods |
| `config/sensor_policy.json` | Non-medical sensor thresholds and bounded actions |
| `config/generation_config.json` | Ollama model, schema generation, and API timeout bounds |
| `config/embedding_models.json` | Stage 4 candidate and model configuration record |

## Scripts

| File | Use |
| --- | --- |
| `scripts/setup_stage4_environment.ps1` | Create the original pinned local environment |
| `scripts/build_dataset.py` / `scripts/validate_dataset.py` | Rebuild and validate source-backed data |
| `scripts/build_chroma_index.py` / `scripts/verify_chroma_index.py` | Build and check the persistent vector collection |
| `scripts/run_api.ps1` / `scripts/check_api.py` | Start and smoke-check FastAPI |
| `scripts/prewarm_ollama.ps1` | Verify Ollama/model and run a small no-download warm-up |
| `scripts/run_demo.ps1` | Prepare the optional model and start the competition API |
| `scripts/final_validation.py` | Run 12 scenarios, warm benchmarks, fallback checks, and concurrency smoke |
| `scripts/build_handoff_package.py` | Build, scan, hash, and audit the ignored source ZIP |
| `scripts/run_notebook_cells.py` | Execute notebook code cells without adding notebook tooling |
| `scripts/generate_study_plan.py`, `scripts/adapt_study_plan.py`, `scripts/generate_grounded_response.py` | Focused Stage 6/7 demonstrations |
| `scripts/benchmark_embeddings.py`, `scripts/evaluate_retriever.py`, `scripts/inspect_retrieval_failures.py` | Frozen earlier-stage evaluation tools; do not rerun final tuning |

## Data

| Location | Contents |
| --- | --- |
| `data/raw` | Deterministic subject, topic, strategy, session, sensor, and alias seeds |
| `data/sources/source_catalog.csv` | 29-source provenance and reuse catalog |
| `data/interim` | Dataset schema, examples, and retrieval-evaluation seed |
| `data/processed/knowledge_corpus.jsonl` | Complete 477-record retrievable corpus |
| `data/processed/*_profiles.jsonl`, `*_strategies.jsonl`, `subject_aliases.jsonl` | Family-specific rebuild inputs/outputs |
| `data/processed/retrieval_*`, `final_retrieval_metrics.json` | Frozen development/final retrieval evidence |
| `data/processed/planner_demo_*`, `sensor_demo_*`, `generation_demo_*`, `api_demo_*` | Earlier-stage demonstration fixtures |
| `data/processed/final_demo_inputs.json` | Twelve final scenario definitions |
| `data/processed/final_demo_outputs.json` | Preserved API responses |
| `data/processed/final_evaluation_results.json` | Per-scenario checks and outcome |
| `data/processed/final_performance_results.json` | Cold, warm, fallback, Ollama, and concurrent measurements |
| `data/processed/final_validation_report.json` | Machine-readable Stage 9 validation summary |
| `data/processed/package_manifest.json` | Ignored external ZIP manifest generated after final commit |
| `chroma_db` | Ignored local persistent vector data; only `.gitkeep` is versioned |

## Notebooks

Notebooks `00` through `09` preserve each earlier project stage. `notebooks/10_end_to_end_demo.ipynb` starts the real deterministic API pipeline and presents the saved final evaluation without requiring a live Ollama response.

## Tests

The `tests` directory contains 171 unit and integration tests covering dataset building/validation, embeddings, Chroma persistence, retrieval, scoring, allocation, scheduling, sensor models/policy/adaptation, generation grounding/validation/fallback, API schemas/errors/endpoints, and concurrency. `tests/api_fakes.py` and `tests/planner_fakes.py` provide deterministic test-only services.

## Documentation route

Read the stage reports in number order for implementation evidence. Use `docs/final_system_report.md` for the consolidated release, `docs/competition_demo_script.md` for the live presentation, `docs/discussion_guide.md` for likely questions, `docs/final_handoff_guide.md` for transfer instructions, and `docs/api_contract.md` plus `docs/flutter_integration_guide.md` for future client work.
