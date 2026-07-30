# Stage 3 Dataset Report

## Release summary

Dataset version `1.0.0-prototype` contains 477 retrievable English records and 96 held-out retrieval-evaluation queries. The evaluation queries are stored separately and are not present in the knowledge corpus.

The corpus has 277 canonical records and 200 controlled synthetic alias records. All canonical records are reviewed at their required tier. All 14 sensor interventions and all 24 study strategies are Tier A and reviewed. Tier C aliases receive full automatic validation plus a stratified sample review.

## Record counts

| Document family | Canonical | Synthetic | Total |
| --- | ---: | ---: | ---: |
| `subject_profile` | 80 | 0 | 80 |
| `topic_profile` | 141 | 0 | 141 |
| `study_strategy` | 24 | 0 | 24 |
| `session_template` | 18 | 0 | 18 |
| `sensor_intervention` | 14 | 0 | 14 |
| `subject_alias` | 0 | 200 | 200 |
| **Total** | **277** | **200** | **477** |

The distribution stays within the confirmed overall target and covers every required knowledge family. The extra topic record preserves the Stage 2 debugging evaluation target.

## Subject and level coverage

| Subject family | Records |
| --- | ---: |
| Arts and design | 38 |
| Business and economics | 41 |
| Computing | 45 |
| Engineering | 41 |
| General | 41 |
| Health sciences | 32 |
| Language and literature | 49 |
| Law | 24 |
| Mathematics | 49 |
| Natural sciences | 54 |
| Social sciences | 49 |
| Not applicable to sensor records | 14 |

Education-level metadata appears on 350 school-compatible records, 454 university-compatible records, and 9 explicitly cross-level records. These counts overlap because one record may support both school and university use.

The dataset supports custom subject names through 80 canonical subject mappings and 200 exact, abbreviation, spelling, and course-name variants. Ambiguous aliases retain an explicit ambiguity flag and context note.

## Sources and provenance

The source catalog grew from 19 to 29 records, and all 29 sources are used by the corpus. Ten authoritative descriptive sources were added:

- QAA Subject Benchmark Statement for Business and Management.
- QAA Subject Benchmark Statement for Economics.
- QAA Subject Benchmark Statement for Accounting.
- American Bar Association 2025-2026 law-school standards.
- General Medical Council Outcomes for Graduates.
- ABET 2025-2026 engineering accreditation criteria.
- QAA Subject Benchmark Statement for Art and Design.
- QAA Subject Benchmark Statement for Architecture.
- QAA Subject Benchmark Statement for Music.
- QAA Subject Benchmark Statement for Communication, Media, Film and Cultural Studies.

These additions support curriculum-neutral subject and task descriptions. They are not treated as causal evidence for study-strategy effectiveness. Unknown reuse terms remain marked `unknown` or paraphrase-only in the source catalog. Records use concise paraphrases and preserve source IDs, evidence labels, limitations, and review metadata.

Every source now has an explicit role. The catalog contains 11 `learning_evidence`, 12 `subject_framework`, 5 `ergonomics_guidance`, and 1 `public_health_guidance` sources. Planner timer values are not attributed to an external source; they remain versioned `design_proposal` values requiring evaluation.

## Review result

There are 321 reviewed records and 156 unreviewed Tier C aliases. Unreviewed aliases remain eligible because they add no factual or safety claim, inherit a reviewed parent, and pass automatic traceability checks.

The deterministic Tier C reviewed set contains 44 of 200 aliases (22%). It includes at least one record from every controlled subject family, all explicitly ambiguous short forms, all five controlled misspellings, abbreviations, ordinary aliases, and generated course-name variants. A structured manual sample of 25 aliases covered all 11 controlled subject families, school and university metadata, four initially flagged ambiguous mappings, five misspellings, and all five generation methods. The audit identified under-labelled ambiguous abbreviations; those records were corrected and promoted into the reviewed set. No remaining material alias error was found. A second independent reviewer remains recommended before public deployment.

## Final structured quality audit

The final checkpoint inspected 11 `subject_profile` records, 15 `topic_profile` records, all 24 `study_strategy` records, all 18 `session_template` records, all 14 `sensor_intervention` records, 25 `subject_alias` records, and 24 held-out evaluation queries. The subject and topic samples covered all 11 controlled subject families, both educational levels, and every learning-task category relevant to the sample.

The audit checked factual grounding, source suitability, retrieval-text naturalness, unsupported difficulty or timer claims, medical language, parent relationships, ambiguity, and future semantic-retrieval usefulness. It found and corrected these issues:

- Six Stage 3 catalog rows contained an unquoted comma in `license_or_reuse_note`, which shifted later CSV columns. The fields are now correctly quoted and parsed.
- Source roles were implicit. `source_role` metadata and an automatic role-compatibility validator were added.
- Art, Architecture, Music, and Film Studies inherited ABET engineering support. Four appropriate QAA subject frameworks were added and the records were remapped.
- Generic visual-analysis wording referred to reading claims. Art and film topics now use observation- and evidence-based descriptions.
- Controlled misspellings and additional school-level queries were missing from the expanded held-out set. Five misspelling, four additional school-level, and explicit ambiguity cases were added while retaining exactly 96 queries.
- Several short aliases such as `AI`, `CS`, `DS`, `IT`, and engineering abbreviations lacked ambiguity notes. They now require subject context and are reviewed Tier C records.
- Sensor fallback retrieval text could contain a doubled period. Punctuation is now normalized by the builder.

After correction, all sampled records were natural, traceable, safe, and suitable for future retrieval. No keyword stuffing, universal timer claim, fixed subject-difficulty claim, diagnostic advice, unsupported synthetic claim, or invalid parent relationship remains.

## Source-role audit

All 278 records that reference at least one `subject_framework` source were checked automatically and by family during the manual audit. Their uses are limited to 50 subject profiles, 87 topic profiles, 6 source-descriptive strategies, 9 design-proposal session templates, and 126 inherited aliases. No sensor record references a subject framework.

Framework-backed subject, topic, strategy, and alias records use `evidence_level: source_descriptive`. Framework-backed sessions use `evidence_level: design_proposal`, state that durations are versioned planner parameters, and say they are not universal scientific facts. QAA, ABA, GMC, ABET, ACM, and NGSS sources are therefore not treated as direct evidence for learning effectiveness, timing, breaks, memory claims, or posture interventions.

## Distribution audit

All 16 intended scope areas are represented: mathematics, physics, chemistry, biology, general science, computing, engineering, languages, literature, writing, history, geography and social sciences, business and economics, law, health sciences, and creative design work. These areas map to the schema's 11 controlled `subject_family` values.

Natural sciences is the largest corpus family with 54 records; law is the smallest applicable family with 24. Within the 141-topic corpus, natural sciences is largest with 18 topics, while law and general are smallest with 8 each. No family exceeds 13% of topic records. Canonical education metadata covers 61 school-compatible and 80 university-compatible subject profiles, plus 109 school-compatible and 141 university-compatible topic profiles; values overlap when a record supports both levels.

Aliases comprise 160 reviewed subject-name variants, 31 deterministic course-name variants, 5 controlled misspellings, 2 reviewed abbreviation additions, and 2 reviewed course-name additions. Eighteen context-sensitive aliases carry ambiguity notes. The remaining unreviewed variants are naming-only expansions with reviewed parents and no new claim.

## Retrieval-text examples

`subject_profile`:

> Subject profile: Computer Science belongs to the curriculum-neutral computing family. Common names include CS, Computing. A useful study plan should match the learner's current topic and required task, because the subject name alone does not determine personal difficulty. Typical learning activities are to trace and explain code; write small working programs; test and debug; justify algorithms or designs. Methods should be chosen from the topic's real learning task and checked against course expectations. This profile describes common educational work without fixing a particular curriculum, course sequence, assessment, or study duration.

`topic_profile`:

> Topic profile: Debugging programs is studied within Programming and is classified here as a debugging task. The practical goal is to reproduce a fault, trace state, test a cause hypothesis, and explain the correction. Suitable methods include reproduce trace hypothesize, single change tests, explain the fix. The learner should finish by checking an answer, explanation, product, or decision against available feedback. Course notes, assignments, or teacher guidance remain the authority for required content and conventions. This curriculum-neutral mapping selects a learning task; it does not teach course-specific content or assign personal difficulty.

`study_strategy`:

> Study strategy: Retrieval practice with feedback. Attempt to recall or produce the target information before checking the answer. This supports durable learning for suitable recall and explanation tasks when questions and feedback are well matched. Practical use: answer before opening notes; check accuracy promptly; correct errors in complete form. Limits: effects depend on the task, delay, feedback, and question quality; it is not universally superior to every learning activity. Select this method only when it practises the target learning task, and use feedback where it is available.

`session_template`:

> Session template proposal: Worked example to independent problem solving. Use these phases: identify the target problem type; study and explain one example; solve related problems independently; check errors and selection cues. The proposed focus range is 30 to 50 minutes, followed by a 5 to 10 minute break. These bounded values are versioned planner design parameters for later user testing, not universal scientific facts. The learner may pause early when needed. A future planner may fit the phases to the time available without dropping the final check.

`sensor_intervention`:

> Non-medical sensor response: Stale sensor readings fallback. Condition: A confirmed timestamp rule marks the latest sensor observation as stale. Safe response: ignore the stale observation; continue the normal timer-based schedule; show a non-alarming data-status explanation. If data is unavailable or unreliable: Treat stale data as unavailable and make no sensor-based adjustment. This record does not diagnose posture, injury, or health. No hardware unit, sampling rate, calibration rule, or scientifically confirmed threshold is assumed; the hardware contract and deterministic trigger configuration must be confirmed before use.

`subject_alias`:

> Subject alias mapping: Stats can refer to Statistics in the mathematics subject family. Use this controlled name variant for exact or semantic matching, then retrieve the canonical subject profile and topic-specific guidance. The alias is context-sensitive: Stats may also mean a set of numerical results; use course or topic context. This synthetic mapping inherits its reviewed parent's sources and introduces no new learning or safety claim.

The evaluation family is intentionally not retrievable and has `query_text` rather than `retrieval_text`. One example is: “Help me practise finding why a program crashes.” Its relevance target maps unseen wording to debugging, active code tracing, hypothesis testing, and feedback.

## Validation results

The full validator passed with zero errors and zero warnings. It checks:

- JSON and JSONL syntax and schema-field compatibility.
- Shared and family-conditional required fields.
- Enumerations, ID format, range bounds, and unique IDs.
- Exact and near-duplicate retrieval text.
- Source, parent, relationship, and synthetic-lineage references.
- Evidence inheritance and review-tier compliance.
- Sensor safety wording and unsupported medical language.
- Session and break design-parameter labels and bounds.
- English-only corpus content.
- Evaluation leakage and evaluation record references.
- Subject-family, education-level, and source-type coverage.
- Source-role correctness, including framework, learning-evidence, ergonomics, and public-health boundaries.
- Family-file consistency and byte-identical repeated builds.

No exact or near-duplicate candidates remain. No source reference or parent link is broken. No evaluation query appears in the retrievable corpus. Two independent temporary builds produced identical hashes for every generated dataset file.

All 13 unit tests pass. They cover stable IDs, deterministic builds, required and conditional fields, invalid enumerations, sources, source-role misuse, parents, duplicates, near duplicates, sensor safety, evaluation separation, invalid fixtures, and valid fixtures.

Both notebooks parse as valid notebook JSON. A standard-library cell runner executed all four code cells in `01_dataset_creation.ipynb` and all five code cells in `02_dataset_validation.ipynb`. Jupyter is not installed on the current machine, so execution used the same Python interpreter directly without adding a dependency.

## Known limitations and risks

- The corpus maps subjects, tasks, strategies, and session structures; it does not contain curriculum-specific tutoring lessons.
- General learning-science evidence is stronger than domain-specific study-method evidence for several professional subjects.
- QAA, ABA, GMC, ABET, ACM, and several publisher sources remain paraphrase-only until exact reuse terms receive final approval.
- WHO material is licensed for non-commercial use under its recorded terms; intended distribution must remain compatible or the dependent records must be revised.
- Review metadata represents the competition-prototype review. Independent human review is still recommended, especially for Tier A content and before public use.
- Session and break ranges are planner design parameters requiring user testing. They are not claims of universal optimal timing.
- The standard-library validator enforces the project's schema rules directly; it is not a complete third-party JSON Schema implementation.
- The held-out query set is designed for future retrieval evaluation but has not been run against embeddings or a vector database.

## Remaining source gaps

Future releases would benefit from stronger domain-specific learning research for programming and debugging, university engineering problem solving, independent language learning, accounting practice, and case-based law and health-science study. Any expansion must keep descriptive curriculum sources separate from causal learning evidence.

## Unresolved hardware-contract questions

- Confirmed sensor field names and data types.
- Units, sampling behavior, timestamps, and freshness rules.
- Direction semantics and pressure-channel layout.
- Device and application calibration responsibilities.
- Valid ranges, status flags, and disconnected-state behavior.
- Which thresholds are firmware facts and which are versioned product configuration.

Until those questions are resolved, sensor records use placeholders, require hardware confirmation, and fall back to the normal timer-based plan.

## Stage 4 recommendations

Stage 4 can now evaluate local embedding candidates and define ChromaDB metadata using the stable IDs and processed corpus. It should preserve source and derivation metadata, index only `knowledge_corpus.jsonl`, keep the 96 evaluation queries outside the collection, test persistence and deterministic re-indexing, and record speed and storage on the target Windows machine.
