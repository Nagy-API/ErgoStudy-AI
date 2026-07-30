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

## Current stage

Stage 3 is complete at its final validation checkpoint. No embedding, vector-database, retrieval, planner, sensor-adapter, local-model, or API implementation has started.

## Next planned stage

Stage 4: embeddings and ChromaDB. The next stage should compare suitable free local embedding models on the target hardware, define metadata filters, index only the validated knowledge corpus, preserve stable IDs and provenance, and verify deterministic persistent indexing. The held-out evaluation queries must remain outside the vector collection.

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
