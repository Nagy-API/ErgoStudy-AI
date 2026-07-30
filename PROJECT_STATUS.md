# Project Status

## Project name

ErgoStudy AI - Posture-Aware Daily Study Planner

## Completed stages

### Environment and scaffold

The repository structure, project rules, initial documentation, architecture draft, environment inspection notebook, and Git repository have been created and validated.

### Dataset design and source strategy

The knowledge domains, seven document families, conditional record schema, retrieval-text and chunking rules, source strategy, data-quality gates, sensor contract draft, source catalog, example records, and retrieval-evaluation seed have been designed and validated. These files are design artifacts, not the final knowledge dataset. No embeddings, vector-database ingestion, retrieval implementation, planner, sensor-adaptation logic, local-model integration, or API implementation has started.

### Dataset creation and validation

The `1.0.0-prototype` English corpus contains 477 retrievable records: 80 subject profiles, 141 topic profiles, 24 study strategies, 18 session templates, 14 sensor interventions, and 200 controlled subject aliases. It also contains 96 held-out evaluation queries outside the corpus. The deterministic builder, standard-library validator, notebooks, unit tests, processed family files, statistics, source expansion, source-role audit, structured manual sample, and Stage 3 report are complete. All blocking validations and 13 unit tests pass.

### Embedding model evaluation and persistent ChromaDB

Stage 4 created a CPython 3.12 `.venv`, verified CUDA execution on the RTX 3050 6GB Laptop GPU, and compared MiniLM, plain BGE, instruction BGE, and prefixed E5 on 64 development queries using direct normalized cosine similarity. The 32 final-test query IDs remain sealed and were not evaluated. `minilm_plain` using `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` was selected by the documented development-only rule.

The persistent `ergostudy-knowledge-1-0-0` Chroma collection contains all 477 corpus records with caller-provided embeddings and a scalar metadata projection. Persistence, full logical content, corpus/evaluation separation, nine metadata filters, direct-versus-Chroma top-10 identity, and reproducible tuned rebuild behavior pass. All 28 repository unit tests, both Stage 4 notebook executions, Stage 3 validation, package compatibility, Python compilation, notebook JSON parsing, and Git whitespace checks pass. Chroma contents, model caches, raw embeddings, and `.venv` remain untracked.

### Production retrieval pipeline and final retrieval evaluation

Stage 5 created a reusable `RetrievalService` with local-only `minilm_plain` loading, persistent Chroma access, `top_k`, scalar metadata filters, source-preserving structured results, documented cosine similarity conversion, deterministic ordering, safe invalid-query behavior, deterministic non-oracle intent analysis, and exact normalized subject and alias resolution with ambiguity preservation.

The 64-query development split compared baseline dense retrieval, exact alias resolution plus dense retrieval, and an intent-aware blend. Twenty baseline failures were classified without changing the corpus: seven ambiguous queries, four embedding limitations, four narrow or incorrect labels, four wrong document-family rankings, and one alias-resolution failure. The frozen `alias_plus_dense` configuration improved development Recall@5 from 0.7143 to 0.8661 and MRR@10 from 0.6429 to 0.8750.

After split hashes and zero final-ID use were verified, the guarded 32-query final test ran exactly once. It achieved Recall@1 0.7241, Recall@3 0.8448, Recall@5 0.8621, Recall@10 0.8966, MRR@10 0.8728, nDCG@10 0.8673, document-family Hit@1/Hit@5 0.9688/1.0000, and subject-family Hit@1/Hit@5 1.0000/1.0000. No retriever change was made after these results.

### Deterministic non-sensor daily study planner

Stage 6A created a deterministic, JSON-compatible one-day planner. It validates available time, optional start time and session preference, subject ratings, topics, and duplicate names. It scores subjects using configurable prototype weights for priority, workload, user-provided difficulty, and knowledge gap; selects only subjects that can receive meaningful time; allocates minutes proportionally; creates 20-to-60-minute sessions; inserts configured breaks; and avoids adjacent high-demand sessions when lower-demand work is available.

The planner retrieves subject profiles, topic profiles, study strategies, and session templates through the frozen Stage 5 service. Exact and alias resolution precede dense acceptance, every study session retains corpus record IDs, and ambiguous, weak, unknown, or unavailable retrieval uses a clearly marked generic fallback. Plan IDs hash normalized input plus the complete configuration. Four committed demos, a reusable CLI, a notebook, unit tests, and persistent-Chroma integration coverage are complete.

## Current stage

Stage 6A is complete at its final validation checkpoint. The deterministic non-sensor daily planner, retrieval-backed knowledge adapter, demo generator, notebook, tests, and documentation are implemented. Sensor adaptation, local-model integration, API, and Flutter integration have not started.

## Next planned stage

Stage 6B: sensor-aware adaptation. It should consume a confirmed sensor contract and apply deterministic, non-medical timing and break adjustments without changing the Stage 6A input scoring rules.

## Confirmed product requirements

- All system content, code, documentation, API fields, notebooks, and generated responses must be in English.
- The system is intended for school and university students.
- Users will enter custom subject names rather than choosing only from a fixed subject list.
- The system will create one-day study plans.
- Plans will include study sessions and breaks.
- The project will use local and free models only.
- Development will target a Windows environment.
- The product will support both sensor and non-sensor modes.
- Sensor data may include continuous sitting duration, posture direction, pressure distribution or imbalance, and poor-posture duration.
- The system will use a substantial validated dataset.
- The target architecture includes a persistent vector database, deterministic planner, sensor adapter, local LLM, and FastAPI.
- Dataset quality and evaluation are more important than inflating the row count.

## Initial user coverage

- The first dataset release targets secondary-school and university students.
- Content is English-only and curriculum-neutral.
- Primary-school coverage, clinical or therapeutic advice, medical diagnosis, curriculum-specific tutoring, and multi-day planning are outside the initial scope.
- Extending the product to younger children would require age-appropriate UX, stronger safety and consent design, and different learning-design assumptions; it is not a simple content expansion.

## Confirmed technical decisions

- Flutter will communicate with the local Python backend through FastAPI and structured JSON.
- Python 3.12 is the recommended initial project interpreter for library compatibility.
- Jupyter notebooks will be used for learning, development, demonstrations, and discussion.
- Reusable production logic will live in Python modules.
- Filesystem code will use `pathlib` where appropriate and remain Windows-friendly.
- ChromaDB is the planned persistent vector database, with semantic retrieval and metadata filtering.
- Planning, time allocation, break placement, rescheduling, and sensor adaptations will be deterministic and testable.
- The local LLM will explain grounded results but will not override planner or sensor-adaptation decisions.
- Factual educational and health-related records will preserve source, citation, and license metadata.
- Source-backed records will be validated before any synthetic expansion.
- Paid APIs will not be used.
- LangChain will not be used unless a later stage demonstrates a concrete need.
- No model or embedding choice is final until candidates are evaluated on the target hardware and project evaluation set.
- Stage 4 selected normalized `sentence-transformers/all-MiniLM-L6-v2` embeddings with plain query and document text, based only on ErgoStudy development queries.
- Retrieval evaluation uses a deterministic 64-query development split and a sealed 32-query final-test split. Stage 4 computed no final-test retrieval metrics.
- Stage 5 freezes exact normalized alias resolution plus dense retrieval. Ambiguous aliases require educational context and never silently collapse multiple controlled subjects.
- The sealed 32-query final test was executed exactly once after configuration freeze; final results are reporting artifacts, not tuning input.
- Chroma uses one persistent collection named `ergostudy-knowledge-1-0-0`, cosine distance, caller-provided embeddings, stable corpus IDs, and scalar metadata filters.
- The knowledge base uses seven document families: subject profiles, topic profiles, study strategies, session templates, sensor interventions, subject aliases, and retrieval evaluation queries.
- Family-specific conditional requirements are used instead of forcing irrelevant fields onto every record.
- Retrieval evaluation queries remain outside the retrieval corpus to reduce evaluation leakage.
- Source-backed records use stable `source_id` foreign keys and concise paraphrases rather than copied passages.
- Evidence strength, design proposals, synthetic status, and manual review status remain separate fields.
- Review is risk-tiered: Tier A receives full manual review, Tier B receives automated checks plus manual review of canonical templates, and Tier C receives automated checks plus stratified sampling with escalation.
- All study-strategy, sensor-intervention, health, wellbeing, posture, prolonged-sitting, break-safety, evidence-backed recommendation, and new factual-claim records are Tier A.
- Synthetic records must preserve the exact reviewed canonical parent, inherited sources, derivation links, and generation-method metadata. Synthetic records are never described as source-verified evidence.
- A second independent reviewer is recommended before production or public release, especially for Tier A records, but is not required for the competition prototype.
- Production eligibility permits zero unreviewed sensor-intervention records.
- Sensor interventions are limited to non-medical reminders and safe fallbacks. Hardware-dependent units, thresholds, calibration, and behavior remain unconfirmed.
- Subject names do not imply fixed difficulty. Difficulty remains personalized user input.
- Session and break ranges are bounded, versioned planner design parameters. They are testable and adjustable by task and user; they are not universal scientific facts.

## Stage 3 corpus targets

- Curate 250 to 390 canonical records across 60 to 90 subject profiles, 110 to 180 topic profiles, 30 to 45 study strategies, 30 to 45 session templates, and 20 to 30 sensor interventions.
- Add 200 to 345 controlled expansions: 20 to 40 subject variants, 25 to 55 topic variants, 15 to 30 session variants, and 140 to 220 aliases or query paraphrases. Study-strategy and sensor-intervention expansions remain zero unless separately promoted to Tier A canonical records.
- Target 450 to 735 retrievable records after canonical and controlled expansion counts are combined.
- Maintain 80 to 120 held-out retrieval-evaluation queries outside the retrieval corpus.
- Keep ordinary retrieval records near 80 to 250 words and review any record above 350 words.
- Use adaptable session and break ranges as planning proposals, never as universal scientific optima.

## Stage 3 source priorities

The 29-source catalog now includes descriptive coverage for business, economics, accounting, law, health and medical education, engineering, art and design, architecture, music, and film/media in addition to the Stage 2 learning-science, literacy, computing, school-science, and ergonomics sources. All sources are used and carry an explicit source role. Domain-specific causal learning evidence remains thinner than general learning-science evidence for several professional subjects, so later releases should expand it carefully.

## Open questions

- Which secondary-school age bands, university levels, and first-release subjects should receive priority within the curriculum-neutral design?
- Who will perform the primary manual review, and is an independent second reviewer available before production or public release?
- Is the intended dataset distribution strictly non-commercial, and is WHO's CC BY-NC-SA 3.0 IGO material compatible with that plan?
- Which source licenses marked unknown or paraphrase-only will receive final approval before public distribution?
- Should final generated responses use a compact source-ID citation, author-year display, or both?
- Which proposed session-duration ranges should be retained after task-level review and later planner testing?
- What are the confirmed sensor fields, units, sampling rate, timestamps, status flags, calibration method, pressure layout, and missing-data behavior?
- Which sensor thresholds, if any, are firmware facts versus product configuration proposals?
- What user-facing safety text will be approved for concerning symptoms without entering medical-advice scope?
- Which independent reviewer can verify Tier A records and the Tier C sample before public deployment?

## Last validation results

The Stage 6A validation completed successfully on July 30, 2026:

- All 42 focused planner and required retrieval tests pass, including real integration with the existing persistent Chroma collection.
- A separate sweep passed 2,073 boundary combinations covering every total from 30 to 720 minutes and preferred session values of 20, 40, and 60 minutes.
- Every generated study session stays between 20 and 60 minutes, every duration is positive, and no plan exceeds its available time.
- The school demo allocates 135 study and 15 break minutes; the university demo allocates 205 study and 35 break minutes.
- The 30-minute demo schedules one meaningful subject and reports the other as unscheduled. The unknown-subject demo uses a clearly marked generic fallback with no invented record IDs.
- All returned retrieval record IDs in the integration plan exist in the 477-record corpus, and planner source inspection confirms that sealed evaluation fields and files are not used.
- Demo regeneration is byte-identical with SHA-256 `f6f543c5b297bb6c88e6cf3339e0f5b4b0eded2f50e30918c130c1312b6d3962`.
- All six Stage 6A notebook code cells execute, including score, retrieval, allocation, time-constraint, and repeated-output assertions.
- Planner and test compilation, notebook and JSON parsing, and Git whitespace checks pass.
- No embedding benchmark ran, the frozen retrieval configuration did not change, and the Chroma collection was not rebuilt.

### Previous Stage 5 validation

The Stage 5 validation completed successfully on July 30, 2026:

- The existing 477-record Chroma collection passed full count, ID, document, metadata, and manifest verification and was not rebuilt.
- The service returns the required structured schema and retains source, review, lineage, evidence, and safety metadata.
- Development Recall@5 improved from 0.7143 to 0.8661 and MRR@10 from 0.6429 to 0.8750.
- All 20 development baseline failures were classified; no corpus modification was justified.
- The frozen configuration and split hashes prove that no final-test ID entered development artifacts.
- The sealed final test ran once and produced Recall@5 0.8621, MRR@10 0.8728, and document/subject family Hit@5 1.0000.
- The final checkpoint includes the complete repository test suite, persistent-index integration tests, notebook execution and JSON parsing, Python compilation, and Git whitespace validation.

### Previous Stage 3 validation

The Stage 3 validation completed successfully on July 30, 2026:

- The deterministic build produced 477 retrievable records: 277 canonical and 200 synthetic.
- All six required retrievable document-family files match the combined corpus.
- The separate held-out set contains 96 queries and has zero corpus leakage.
- The source catalog contains 29 unique records, every source is used, and source roles pass compatibility checks.
- Required fields, conditional fields, controlled values, ranges, unique IDs, sources, parents, lineage, evidence inheritance, and review tiers pass.
- Exact and near-duplicate checks report zero candidates.
- All 14 sensor records are Tier A, reviewed, hardware-confirmation-dependent, non-medical, and safe under missing or invalid data.
- The Tier C reviewed set contains 44 of 200 aliases (22%), including every explicitly ambiguous alias and controlled misspelling; the structured 25-record audit sample covers every controlled subject family and all generation methods.
- Two temporary builds produced byte-identical outputs.
- All 13 unit tests pass.
- Both notebooks parse as JSON and all nine code cells execute successfully with the standard-library runner.
- Python compilation and Git whitespace checks pass.
- No models, heavy packages, embeddings, ChromaDB data, retrieval code, planner code, FastAPI code, or local-LLM integration were added.
