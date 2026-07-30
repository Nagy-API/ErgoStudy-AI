# Dataset Design

## Status and scope

This document defines the Stage 2 design for the ErgoStudy AI knowledge base. It does not create the final dataset, embeddings, vector database, retrieval pipeline, planner, API, or local-model integration.

The knowledge base will support source-grounded retrieval for personalized one-day study plans. A student's subject difficulty remains a user input. Dataset records describe common learning activities and potentially useful methods; they never assign a universal difficulty to a subject or student.

## Initial user coverage

The first complete prototype is designed for:

- secondary-school students;
- university students;
- English-language subject, topic, and query input;
- curriculum-neutral subject mapping that preserves the user's custom wording.

The initial prototype does not cover:

- primary-school children;
- clinical or therapeutic posture guidance;
- diagnosis or treatment;
- curriculum-specific tutoring content or authoritative answers for a particular national curriculum;
- long-term or multi-day study planning.

Primary-school learners may require substantially different language, interaction design, attention assumptions, safeguarding, parental or guardian consent, privacy controls, and evidence-based learning design. They should not be added by simply lowering the educational-level label on existing records.

## Dataset goals

The dataset must help the future system:

1. Interpret custom English subject and topic names from school and university students.
2. Map those names to curriculum-neutral subject families and learning tasks.
3. Retrieve evidence-backed study methods with clear use cases and limitations.
4. Retrieve task-appropriate session structures without claiming one universal timer pattern.
5. Provide conservative, non-medical posture and movement reminders when sensor data is available.
6. Produce short explanations whose factual claims can be traced to cataloged sources.
7. Support semantic retrieval, exact alias matching, metadata filtering, and later retrieval evaluation.

## Design principles

- Keep source evidence, design proposals, and synthetic expansions visibly separate.
- Preserve the student's wording alongside normalized fields.
- Prefer a smaller diverse corpus over repetitive paraphrases.
- Use metadata for eligibility and safety filters, not as a replacement for meaningful retrieval text.
- Treat subject profiles as typical activity descriptions, not fixed prescriptions.
- Treat sensor mappings and all timing thresholds as proposals until the hardware and Flutter contracts are confirmed.
- Use English-only, concise paraphrases. Do not copy long passages from sources.

## Document families

### `subject_profile`

Describes a school or university subject, common aliases, curriculum-neutral family, educational level, typical activities, and typical task characteristics. It may state that mathematics commonly involves symbolic problem solving or that computer science commonly involves reading, writing, testing, and debugging code. It must not assign a fixed difficulty.

### `topic_profile`

Describes a topic or task type within a subject family, such as integration, vocabulary learning, historical comparison, case analysis, debugging, or laboratory report writing. It links a user's topic wording to learning tasks and cognitive demand.

### `study_strategy`

Describes a named method, supported task types, implementation guidance, limitations, and evidence. Initial coverage includes retrieval practice, spaced practice, suitable interleaving, worked examples, practice problems, self-explanation, flashcards, concept mapping, reading strategies, writing practice, coding practice, and feedback-based revision.

### `session_template`

Describes an adaptable study-session structure for a task type. Durations are ranges used as planning design proposals, not universal scientific optima. A template records suitable and unsuitable use cases, possible phases, and break ranges. The future deterministic planner will select and constrain templates; retrieval will only provide relevant guidance.

### `sensor_intervention`

Describes a conservative response to available, stale, missing, invalid, or unreliable sensor observations. Responses are limited to reminders, optional movement or posture changes, shorter upcoming sessions, or no adjustment. Records cannot diagnose conditions or infer hardware behavior. Hardware-dependent fields and thresholds remain explicitly unconfirmed.

### `subject_alias`

Provides exact and semantic matching hints for alternative names and abbreviations, such as `Mathematics`, `Math`, and `Maths`, or `Computer Science`, `CS`, and `Computing`. Ambiguous aliases must list ambiguity notes and must not silently force a single subject.

### `retrieval_evaluation_query`

Defines a test query, expected document families, subject family when applicable, relevant records or relevance criteria, difficulty type, and notes. Evaluation queries are versioned separately from knowledge records and excluded from the retrieval corpus to prevent leakage.

## Shared record structure

The normative machine-readable rules are in `data/interim/dataset_schema.json`. The schema uses a shared core plus conditional requirements, so irrelevant fields are not forced onto every family.

### Shared knowledge-record fields

| Field | Required | Meaning |
| --- | --- | --- |
| `record_id` | Yes | Stable, human-readable identifier with family prefix and version suffix. |
| `document_family` | Yes | One of the seven controlled document families. |
| `title` | Knowledge records | Short display title. |
| `retrieval_text` | Knowledge records | Standalone text embedded and searched later. |
| `educational_level` | Conditional | One or more of `school`, `university`, or `cross_level`. |
| `subject_family` | Conditional | Curriculum-neutral category used for filtering. |
| `subject_name` | Conditional | Canonical subject label, never a difficulty rating. |
| `aliases` | Conditional | Alternative names and abbreviations. |
| `topic` | Topic records | Canonical topic or task label. |
| `learning_task` | Conditional | Primary task category such as `problem_solving`, `coding`, or `writing`. |
| `cognitive_demand` | Conditional | `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`, or `mixed`. |
| `recommended_methods` | Conditional | Strategy identifiers or plain controlled method names. |
| `session_duration_min` / `session_duration_max` | Session templates | Inclusive proposed focus-duration range in minutes. |
| `break_duration_min` / `break_duration_max` | Session templates | Inclusive proposed break range in minutes. |
| `evidence_level` | Knowledge records | Strength/status label; `design_proposal` is distinct from research evidence. |
| `source_ids` | Knowledge records | One or more foreign keys to `source_catalog.csv`, except curated aliases may use descriptive curriculum sources. |
| `safety_scope` | Knowledge records | `none`, `non_medical_wellbeing`, or `stop_and_seek_help`. |
| `synthetic` | Knowledge records | Whether the record was machine-expanded rather than directly curated. |
| `reviewed` | Knowledge records | Whether a human reviewer accepted this exact record version. |
| `review_tier` | Knowledge records | Proposed review class: `tier_a`, `tier_b`, or `tier_c`. |
| `generation_method` | Expanded records | How an expansion was produced, such as a rule-based alias or controlled template. |
| `dataset_version` | Yes | Semantic dataset version, initially `0.1.0-design`. |

### Family-specific fields

- `subject_profile`: `typical_learning_activities`, `characteristics`, and at least one `educational_level`.
- `topic_profile`: `topic`, `learning_task`, `cognitive_demand`, and `recommended_methods`.
- `study_strategy`: `recommended_methods`, `suitable_learning_tasks`, `implementation_guidance`, `unsuitable_use_cases`, and `limitations`.
- `session_template`: duration and break bounds, `phases`, `suitable_learning_tasks`, `unsuitable_use_cases`, and `duration_status`.
- `sensor_intervention`: `sensor_condition`, `intervention`, `missing_data_behavior`, `hardware_confirmation_required`, and `contraindications`.
- `subject_alias`: canonical `subject_name`, `aliases`, `matching_notes`, and ambiguity information.
- `retrieval_evaluation_query`: `query_id`, `query_text`, expected families, relevance target, difficulty type, and notes. It does not require evidence fields because it is a test artifact, not guidance.

## Controlled metadata

Initial filter fields are:

- `document_family`
- `educational_level`
- `subject_family`
- `learning_task`
- `cognitive_demand`
- `evidence_level`
- `safety_scope`
- `synthetic`
- `reviewed`
- `review_tier`
- `dataset_version`
- `sensor_mode` where relevant: `not_applicable`, `sensor_optional`, or `sensor_required`

Fields used as ChromaDB metadata later must be flattened to scalar strings or deterministic delimited strings during ingestion. The source JSONL remains the richer source of truth. That transformation belongs to Stage 4, not this stage.

## Retrieval-text construction

`retrieval_text` must be independently understandable because a retrieved record may appear without neighboring rows. The construction order is:

1. Canonical title and document-family context.
2. Canonical subject, topic, and aliases when relevant.
3. The learning task and cognitive demand.
4. Concise guidance or typical activities.
5. Suitable and unsuitable cases.
6. Important limitations or safety boundary.

Example pattern:

```text
Topic profile: Debugging in computer science and programming. Common task wording includes fixing bugs, tracing errors, and diagnosing failing tests. This is an applied analysis task suited to reproducing the failure, reading code, forming a hypothesis, testing one change, and explaining the cause. It is not primarily a fact-memorization task.
```

The retrieval text does not include raw URLs, long citations, review workflow fields, or repeated keyword lists. Those stay in metadata or the source catalog.

## Chunking strategy

Most records should remain one semantic unit because they are deliberately concise. Target approximately 80 to 250 words per knowledge record and a hard review trigger above 350 words.

Long evidence summaries may be divided by claim or recommendation, not by arbitrary character count. Each child chunk must:

- keep its own `record_id`;
- retain all supporting `source_ids`;
- retain enough context to stand alone;
- use `parent_record_id` and `chunk_index` when derived from a longer curated record;
- avoid splitting a recommendation from its limitation or safety qualifier.

Alias records and evaluation queries are not chunked.

## Identifier strategy

Knowledge IDs use:

```text
<family-prefix>-<canonical-slug>-<scope-slug>-v<record-revision>
```

Examples are `subject-mathematics-cross-level-v1`, `topic-debugging-computing-v1`, and `sensor-missing-data-safe-fallback-v1`. Prefixes are `subject`, `topic`, `strategy`, `session`, `sensor`, `alias`, and `eval`.

IDs are never regenerated because wording changes. A materially changed meaning creates a new revision suffix and records `supersedes_record_id`. Pure typo fixes may retain the ID but increment the dataset patch version and preserve a change log during Stage 3.

## Relationships

- `subject_alias.canonical_subject_record_id` points to a `subject_profile` when available.
- `topic_profile.related_subject_record_ids` links a topic to one or more subject profiles.
- `topic_profile.recommended_methods` refers to study-strategy identifiers or controlled method names.
- `session_template.recommended_methods` links suitable strategies to a session structure.
- `sensor_intervention.compatible_session_templates` identifies templates that may be shortened or interrupted later, without defining planner behavior now.
- Every evidence-backed knowledge record links through `source_ids` to `data/sources/source_catalog.csv`.
- Evaluation queries may name existing `expected_relevant_record_ids` or use a reusable `relevance_criteria` statement when the final record does not yet exist.

Relationships are validated as foreign keys in Stage 3. They are not embedded as duplicated prose.

## Versioning

- Dataset releases use semantic versions: `MAJOR.MINOR.PATCH`.
- `0.1.0-design` identifies Stage 2 schema examples and is not a production dataset.
- Major: incompatible schema or controlled-vocabulary change.
- Minor: reviewed content expansion or new document family.
- Patch: corrections that do not change meaning or compatibility.
- Each release will record creation date, source-catalog version, schema hash, record counts, reviewer summary, and change notes.
- Evaluation sets receive their own version so retrieval progress can be compared without silently changing the test.

## Proposed corpus structure and size

The first complete prototype should contain **250 to 390 canonical knowledge records** and **200 to 345 controlled alias and coverage expansions**, producing approximately **450 to 735 retrievable records**. It should also contain **80 to 120 held-out evaluation queries**, which are test artifacts and are not counted as retrieval-corpus records.

| Document family | Canonical records | Controlled expansions | Proposed retrievable total | Rationale |
| --- | ---: | ---: | ---: | --- |
| `subject_profile` | 60-90 | 20-40 | 80-130 | Broad secondary-school and university subject coverage while preserving custom names. |
| `topic_profile` | 110-180 | 25-55 | 135-235 | Topic and task diversity is the largest semantic-retrieval need. |
| `study_strategy` | 30-45 | 0 | 30-45 | Every strategy is Tier A and must remain a manually reviewed canonical recommendation. |
| `session_template` | 30-45 | 15-30 | 45-75 | Canonical task structures may support controlled metadata variants without inventing new timing claims. |
| `sensor_intervention` | 20-30 | 0 | 20-30 | Every sensor and safety record is Tier A; unreviewed variants are prohibited. |
| `subject_alias` | 0 | 140-220 | 140-220 | Exact aliases, spelling variants, and ambiguity mappings are controlled coverage expansions. |
| `retrieval_evaluation_query` | Not in corpus | Not in corpus | 80-120 held-out queries | Evaluation data remains separate to prevent leakage. |

The canonical minimum is substantial enough to represent the major learning tasks and source-supported guidance. Controlled expansion improves name and phrasing coverage without duplicating factual claims. A larger row count is not progress when it mainly repeats paraphrases, weakens traceability, or exceeds realistic review capacity.

Coverage review must check diversity across level, family, task, source, and query difficulty rather than only total count. Stage 3 may adjust the distribution after source expansion, duplicate analysis, and measured error rates, while preserving the separation between canonical knowledge, expansions, aliases, and evaluation queries.

## Tiered review and expansion policy

The competition prototype currently has one AI developer, so the review design must concentrate manual effort on risk and novelty. A single documented reviewer is acceptable for the prototype. An independent second reviewer is recommended before production use or public deployment, but is not a Stage 3 completion requirement.

### Tier A: mandatory full manual review

Review every exact record in these categories:

- every `study_strategy` record;
- every `sensor_intervention` record;
- every health, wellbeing, posture, sitting, break, or safety-related claim;
- every new evidence-backed recommendation;
- every record that introduces a new source-supported factual claim;
- all source-catalog entries, license decisions, evidence notes, and contradiction decisions.

Tier A records must pass automated validation, retain direct source traceability, and set `reviewed: true` for the exact record before entering the production corpus. There must be zero unreviewed sensor records in the production corpus.

### Tier B: canonical review plus automated expansion validation

This tier covers `subject_profile`, `topic_profile`, `session_template`, structured curriculum mappings, and controlled synthetic expansions. The exact canonical template or mapping receives full manual review. Every expansion then receives full automated validation and must remain within the canonical record's approved claims, sources, categories, and bounded parameters.

An expanded Tier B record must:

- set `synthetic: true` when machine- or rule-expanded;
- identify one or more reviewed canonical parents in `derived_from_record_ids`;
- record `generation_method` or equivalent derivation metadata;
- inherit source traceability without adding unsupported sources or claims;
- preserve the exact canonical parent's review status separately from its own `reviewed` value.

### Tier C: automated validation plus stratified manual sampling

This tier covers subject-alias expansions, spelling variants, controlled query paraphrases, and low-risk metadata-only expansions. All records receive automated validation. The initial manual sample is 10% of each expansion batch, with at least 10 records when the batch contains 10 or more records, stratified by subject family, educational level, ambiguity status, and generation method.

If a major error is found, increase the affected stratum to at least 20%. If another major error or any blocking error is found, manually review the entire affected batch. Sampling decisions and results belong in the release report.

### Expansion constraints

Synthetic or controlled expansions may add natural-language wording, spelling and punctuation variants, or metadata combinations already allowed by a reviewed canonical record. They may not introduce citations, evidence levels, factual claims, health language, sensor rules, session bounds, or broader recommendations.

## Session and break parameters

Session durations and break ranges are deterministic planner design parameters. They are bounded recommendations, not universal scientific facts. Every range must be:

- stored in versioned configuration or versioned session-template records;
- validated so minimums, maximums, and daily totals remain consistent;
- tested against task type, user availability, and planner constraints;
- explained as an adaptable proposal rather than an ideal timer;
- adjustable in later releases using retrieval evaluation, planner tests, user feedback, and documented product decisions.

Sources may inform the shape and safety boundary of a template, but they do not automatically establish the project's exact numeric range.

### Never generate without evidence or confirmation

- Citations, source metadata, evidence levels, or research findings.
- Health diagnoses, treatment advice, or claims that a posture causes a condition.
- Sensor units, thresholds, sampling rates, calibration rules, or pressure semantics.
- Universal session durations or claims of an ideal break timer.
- Subject difficulty or ability assumptions.
- Curriculum facts presented as universal across countries or institutions.

## Separation from later stages

This design intentionally stops before bulk record generation, validator implementation, embeddings, ChromaDB ingestion, retrieval code, planner logic, FastAPI, or local-LLM integration. The next stage is creation and validation of a small curated dataset from approved sources.
