# Data Quality Policy

## Purpose

This policy defines measurable acceptance criteria for Stage 3 dataset creation. Stage 2 example files demonstrate the design; they are not production data. One example record is deliberately invalid for future validator testing and must never enter processed data.

## Quality gates

A release passes only when all automated blocking checks pass, required manual reviews are complete, safety-sensitive records receive full review, and the release summary documents any non-blocking warnings. Counts alone never establish quality.

## Review tiers and production eligibility

The competition prototype currently has one AI developer. It therefore uses risk-based review rather than requiring two reviewers for every record. A second independent reviewer is recommended before production or public deployment, but is not required for the competition prototype.

### Tier A: mandatory full manual review

Tier A includes every `study_strategy`, every `sensor_intervention`, every health, wellbeing, posture, sitting, break, or safety-related claim, every new evidence-backed recommendation, and every record introducing a new source-supported factual claim.

**Acceptance:** 100% automated validation, 100% documented manual review of the exact record, complete source traceability, and `reviewed: true`. The production corpus must contain zero unreviewed sensor records.

### Tier B: reviewed canonical template plus validated expansions

Tier B includes subject profiles, topic profiles, session templates, structured curriculum mappings, and controlled synthetic expansions. Each exact canonical template or mapping receives full manual review. Expansions receive full automated validation against that canonical record.

**Acceptance:** the canonical parent has `reviewed: true`; every expansion identifies the parent in `derived_from_record_ids`, records `generation_method` or equivalent derivation metadata, sets `synthetic: true` when applicable, preserves source traceability, and introduces no new factual claim, evidence level, source, safety language, or numeric session bound.

### Tier C: automated validation plus stratified sampling

Tier C includes subject-alias expansions, spelling variants, controlled query paraphrases, and low-risk metadata-only expansions.

**Acceptance:** 100% automated validation plus a 10% manual sample of each batch, with at least 10 records when the batch contains 10 or more. The sample is stratified by subject family, educational level, ambiguity status, and generation method. One major error increases the affected stratum to at least 20%; a second major error or any blocking error triggers 100% review of the affected batch.

Review samples, errors, escalation decisions, and reviewer identity must be recorded in the release report.

## Automatic checks

### Structure and required values

- CSV parses with a single header and consistent column count.
- JSON parses as UTF-8 JSON; JSONL parses as exactly one object per non-empty line.
- Every record satisfies its family-specific required fields.
- No required string is blank after trimming.
- Arrays required to contain values have at least one non-empty unique item.
- Unknown fields produce a warning during development and a failure in processed releases unless explicitly allowed by the schema version.

**Acceptance:** 100% of processed records pass. The deliberately invalid fixture must fail for the expected reasons.

### Identifiers and versions

- `record_id`, `query_id`, and `source_id` match their documented patterns.
- IDs are unique within and across release files where applicable.
- `dataset_version` is consistent with the release manifest.
- `supersedes_record_id` and relationship IDs resolve when present.

**Acceptance:** zero duplicates, zero unresolved required relationships, and zero version mismatches.

### Numeric ranges

- Session and break values are integers greater than zero.
- Minimum values are less than or equal to maximum values.
- Session proposal ranges remain within the policy envelope configured for the release; proposed initial envelope is 10 to 120 focus minutes and 2 to 30 break minutes.
- No sensor threshold is accepted until a confirmed contract and named configuration source exist.

**Acceptance:** zero invalid bounds. Envelope exceptions require a recorded reviewer decision and cannot be synthetic.

### Controlled vocabularies

- Category values match the schema exactly.
- Family-inappropriate fields are absent or null according to the schema.
- `evidence_level: design_proposal` cannot be described as established evidence.
- `reviewed: true` requires a review-log entry in Stage 3.

**Acceptance:** 100% valid categories and review-log coverage.

### Source integrity

- Every `source_id` resolves to one catalog row.
- Catalog URLs use HTTPS except for a documented legacy reason.
- Access dates use ISO `YYYY-MM-DD`.
- Sources marked rejected cannot support processed records.
- `synthetic: false` does not by itself imply source verification; review status is checked separately.

**Acceptance:** zero broken foreign keys, zero rejected-source references, and 100% valid date formats.

### Exact and near duplicates

- Normalize case, whitespace, punctuation, and list ordering to detect exact duplicates.
- Compare normalized retrieval text using token shingles or a standard-library similarity method.
- Flag pairs with token-set Jaccard similarity at or above 0.85 or `difflib.SequenceMatcher` ratio at or above 0.92 within the same family.
- Alias records with the same normalized alias and canonical subject are merged; aliases mapped to different subjects are flagged as ambiguous rather than deleted.

**Acceptance:** zero unreviewed exact duplicates. Every near-duplicate warning has a `merge`, `retain_with_reason`, or `revise` decision.

### Retrieval-text quality

- Retrieval text is 40 to 350 words for ordinary knowledge records, with warnings below 60 or above 250.
- It contains a family-relevant title or concept, a task or use-case statement, and limitations when required.
- It does not consist primarily of keyword lists, citations, URLs, duplicated metadata, or boilerplate.
- No two records use identical retrieval text.
- Evaluation query text is excluded from corpus retrieval text.

**Acceptance:** 100% inside hard bounds; at least 95% inside preferred bounds; zero identical retrieval text.

### Synthetic traceability

- Synthetic records set `synthetic: true`.
- They contain `derived_from_record_ids`, `generation_method` or equivalent derivation metadata, and a generation-batch identifier in the Stage 3 provenance log.
- Each canonical parent referenced by an expansion has `reviewed: true` for that exact canonical record.
- Expanded records inherit source IDs from their reviewed canonical parent and cannot add a source without Tier A review of the new claim.
- They cannot introduce new `source_ids`, evidence levels, session bounds, sensor rules, or safety claims.
- Their own `reviewed` value describes review of the exact expanded record and must not be confused with the canonical parent's review status.

**Acceptance:** 100% lineage and generation-method coverage, 100% reviewed canonical parents, and zero synthetic safety-sensitive records in processed data unless the exact record completed Tier A review.

### Evaluation leakage

- Evaluation query text and expected answers are stored outside the retrieval corpus.
- Synthetic expansion prompts cannot include held-out query text.
- Exact normalized overlap between evaluation queries and generated training or retrieval text is flagged.
- Query authorship and knowledge-record review should be separated where practical.

**Acceptance:** zero exact leakage; every high-similarity warning at or above 0.90 has a documented decision. At least 20% of final queries remain sealed until the retrieval pipeline is frozen for an evaluation run.

### Unsafe language

Block records that use diagnosis or treatment language such as `diagnose`, `cure`, `treat`, `therapy`, or claims that a sensor proves injury, unless the wording is explicitly a safety boundary telling the system not to provide that advice. Also flag absolute language such as `always`, `never`, `guarantees`, `perfect posture`, and `ideal for everyone`.

**Acceptance:** zero unreviewed health-language flags and 100% manual review of `sensor_intervention` records.

## Manual checks

### Claim-to-source alignment

Reviewers confirm that each factual clause is supported by the cited source, matches the studied population and task, and retains important limitations.

**Acceptance:** 100% documented review for all Tier A records; 100% review of Tier B canonical templates; and the Tier C stratified sample and escalation rules defined above.

### Contradictory recommendations

Reviewers compare records sharing a method, task, or sensor condition. Apparent contradictions must be resolved by narrowing the context, recording evidence disagreement, or rejecting one record. Software should flag contradictory pairs when one recommends and another marks the same method unsuitable for the same metadata combination.

**Acceptance:** zero unexplained high-severity contradictions. Low-severity context differences must have explicit suitable and unsuitable cases.

### Unsupported claims

Reviewers inspect titles, retrieval text, duration ranges, and explanations for claims not present in sources. Design proposals must be labeled and justified separately from evidence.

**Acceptance:** zero unsupported factual claims in accepted records. A record with an unsupported core claim is rejected, not merely downgraded.

### Safety and tone

Sensor guidance must remain optional, non-alarming, non-medical, and clear about missing or unreliable data. It must not shame users or encourage working through pain.

**Acceptance:** every sensor record receives documented Tier A review of its exact wording and sources. No unreviewed sensor record is eligible for the production corpus.

### Subject and alias validity

Reviewers confirm that subject mappings do not assume curriculum, level, or difficulty from a name alone. Ambiguous terms such as `English`, `AI`, or `analysis` require disambiguation notes.

**Acceptance:** 100% of ambiguous aliases flagged; no alias with two plausible meanings is silently normalized to one.

### Coverage

Review a matrix of document family by educational level, subject family, and learning task. No single subject family should dominate merely because it was easier to generate.

**Acceptance for the first release:** every planned learning task has at least five reviewed records across at least two subject families where applicable; both school and university levels appear in every appropriate family; no subject family exceeds 20% of subject and topic profiles without a documented reason.

### Session and break parameters

Session durations and break ranges are planner design parameters and bounded recommendations. They are not universal scientific facts. Reviewers verify that the record labels them as proposals and does not attribute the project's exact numeric range to a source unless the source directly supports that claim.

**Acceptance:** all ranges are versioned, pass minimum and maximum checks, have planner tests for total-time consistency, and can be changed later through a documented dataset or configuration version using evaluation results and user feedback.

## Severity levels

- **Blocking:** parse errors, broken source links, unsupported health claims, fabricated citations, invalid ranges, unresolved IDs, leakage, or unreviewed sensor guidance.
- **Major:** incorrect category, misleading evidence level, unhandled contradiction, ambiguous alias without a flag, or material retrieval-text duplication.
- **Minor:** style, wording, or metadata consistency issue that does not change meaning.

A release requires zero blocking and zero unresolved major issues. Minor issues may remain only with owners and target dates.

## Validation report

Every release report records:

- files and schema version;
- record counts by family and metadata category;
- source counts and review status;
- automatic check totals and failures;
- manual sample sizes and error rates;
- contradiction and duplicate decisions;
- safety-review sign-off;
- leakage results;
- known limitations and deferred issues.

## Stage 2 validation expectations

For the current design artifacts:

- schema JSON must parse;
- every non-deliberately-invalid example must pass the custom conditional checks;
- the deliberately invalid record must fail minimum/maximum ordering and source resolution;
- evaluation seed must contain at least 30 unique queries and all required fields;
- source CSV must parse, have unique IDs, and use checked HTTPS URLs;
- all new project content must remain English-only and free of invalid control characters.
