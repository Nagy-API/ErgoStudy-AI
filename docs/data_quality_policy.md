# Data quality policy

Active records must be English, source-traceable, schema-valid, review-labelled, and free of unsupported effectiveness claims. Synthetic aliases must retain parent lineage and cannot introduce factual claims. Evaluation queries remain separate from retrievable records.

The validator checks IDs, required fields, enums, sources, lineage, duplicates, language, family slices, session/break proposal bounds, evaluation references, and deterministic rebuild hashes. Sensor or hardware records are out of scope and fail the active family/schema boundary.

Normal timer-based breaks are planner design parameters requiring user testing; they must not be presented as universal scientific or medical facts.
