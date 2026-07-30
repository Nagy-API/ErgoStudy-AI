# Stage 5 Production Retrieval and Final Evaluation Report

## Outcome

Stage 5 implements a reusable `RetrievalService` over the fixed Stage 4 Chroma collection and the selected `minilm_plain` embedding configuration. The service accepts plain English, supports `top_k` and scalar metadata filters, returns structured source-preserving results, performs exact normalized subject and alias resolution, and falls back to dense semantic retrieval.

Development work used only the 64-query development split. The configuration was frozen before the 32 final-test queries were retrieved. The sealed test was then executed once; no retrieval behavior was changed afterward.

The selected configuration improved development Recall@5 from 0.7143 to 0.8661 and MRR@10 from 0.6429 to 0.8750. On the sealed final test it achieved Recall@5 0.8621, MRR@10 0.8728, document-family Hit@5 1.0000, and subject-family Hit@5 1.0000.

## Production retrieval boundary

`src/retriever.py` loads the persistent `ergostudy-knowledge-1-0-0` collection and the locally cached `sentence-transformers/all-MiniLM-L6-v2` revision selected in Stage 4. Model loading uses `local_files_only=True`; Stage 5 installed and downloaded nothing.

Each result contains:

- `record_id`
- `title`
- `retrieval_text`
- `document_family`
- `subject_family`
- `score`
- complete remaining record metadata, including source and review fields

Chroma uses cosine distance. The reported semantic score is exactly `1 - cosine_distance`. Exact-name and intent adjustments affect deterministic ordering but never alter the reported similarity. Ties are ordered by adjusted ranking value, then cosine similarity, then stable `record_id`.

Empty or non-string queries return an empty list. Invalid `top_k` values and unsupported or non-scalar metadata filters fail explicitly. Multiple scalar filters are translated to a deterministic Chroma `$and` expression.

## Query analysis and alias handling

`QueryAnalyzer` derives non-oracle signals from normalized query text: subject lookup, topic lookup, strategy request, session-template request, sensor or posture situation, and alias lookup. These signals never read query IDs, difficulty labels, expected families, or relevant record IDs.

`AliasResolver` applies Unicode compatibility normalization, case folding, whitespace collapse, ampersand-to-`and` conversion, punctuation-to-boundary conversion, exact token-phrase subject matching, and exact controlled-alias matching. It does not use fuzzy matching.

Aliases flagged as ambiguous remain unresolved without educational context. General context such as `course`, `study`, `revision`, `assignment`, or `topic` can establish that the token is being used as a subject name; the resolver still returns all controlled candidates and never silently chooses among multiple subject mappings. Dense semantic retrieval remains the fallback.

## Development-only comparison

Record metrics use the 56 development queries with explicit relevant IDs. Family metrics use all 64 applicable development queries.

| Development configuration | R@1 | R@3 | R@5 | R@10 | MRR@10 | nDCG@10 | Doc H@1 / H@5 | Subject H@1 / H@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline dense | 0.4107 | 0.6518 | 0.7143 | 0.7321 | 0.6429 | 0.6349 | 0.8594 / 0.9375 | 0.8448 / 0.8966 |
| Exact alias + dense | 0.6964 | 0.8661 | 0.8661 | 0.8750 | 0.8750 | 0.8652 | 0.8594 / 0.9375 | 0.9655 / 1.0000 |
| Intent-aware blend | 0.6786 | 0.8661 | 0.8661 | 0.8750 | 0.8661 | 0.8581 | 0.8594 / 0.9375 | 0.9655 / 1.0000 |

Exact resolution corrected a genuine defect in dense retrieval: controlled subject names and aliases could be semantically relevant but remain below the useful cutoff. A 0.25 deterministic boost for a safely resolved exact subject or alias raised the canonical and controlled alias records without changing their reported cosine scores.

The light intent-aware blend tied Recall@5 but reduced MRR@10 slightly. More aggressive family boosts improved some family slices but displaced specifically labeled records. Because the selection priorities start with Recall@5 and MRR@10, `alias_plus_dense` was frozen.

## Development failure analysis

A baseline failure means Recall@5 below 1.0, document-family Hit@5 failure, or subject-family Hit@5 failure. All 20 failures were classified using development data only.

| Primary category | Count |
| --- | ---: |
| Ambiguous query | 7 |
| Embedding limitation | 4 |
| Narrow or incorrect evaluation label | 4 |
| Wrong document-family ranking | 4 |
| Alias-resolution failure | 1 |
| Corpus coverage limitation | 0 |
| Metadata mismatch | 0 |

The analysis did not justify corpus edits. Several cross-family strategy requests ranked the immediate subject or topic above a useful strategy or session template. Some labels were narrower than the query: for example, a biology genetics-vocabulary query retrieved the exact genetics topic, Biology profile, and `Bio` alias, while its labels named a different controlled alias plus one strategy. Ambiguous abbreviations accounted for the largest category, and the new resolver improved these only when the query supplied educational context.

## Frozen configuration

`data/processed/retrieval_config.json` records the immutable development decision:

- configuration: `alias_plus_dense`
- embedding: `minilm_plain`
- collection: `ergostudy-knowledge-1-0-0`
- semantic candidate retrieval: Chroma cosine search, top 10 at evaluation time
- exact subject boost: 0.25
- exact alias boost: 0.25
- intent family routing: disabled in the selected configuration
- deterministic final ordering: adjusted value, cosine similarity, stable record ID
- configuration hash: `d3f8675f5ae0f50d7a4a7dc61723db9749ab5f2a9bf14f72f426247252063118`

The file stores development and sealed-ID hashes, the collection manifest hash, all candidate development metrics, and an explicit statement that final-test metrics were unseen during selection.

## Sealed final-test evaluation

Before the final run, the evaluator verified that all 64 development IDs were present, no final-test ID occurred in the development results or failure analysis, both split hashes matched the frozen configuration, and neither final artifact existed. The final command required `--acknowledge-sealed-test`; the presence of either final artifact now blocks another run.

Record metrics use 29 final queries with explicit relevant IDs. Family metrics use all 32 applicable final queries.

| Final metric | Value |
| --- | ---: |
| Recall@1 | 0.7241 |
| Recall@3 | 0.8448 |
| Recall@5 | 0.8621 |
| Recall@10 | 0.8966 |
| MRR@10 | 0.8728 |
| nDCG@10 | 0.8673 |
| Document-family Hit@1 | 0.9688 |
| Document-family Hit@5 | 1.0000 |
| Subject-family Hit@1 | 1.0000 |
| Subject-family Hit@5 | 1.0000 |

There were no zero-result queries. Two of 29 record-labeled queries had no labeled top-10 hit. The measured median latency was 16.86 ms, average latency 32.84 ms, and maximum cold-start-affected latency 530.50 ms on the recorded Stage 4 machine.

## Priority slices

| Slice | n | R@5 | MRR@10 | Doc H@1 | Doc H@5 | Subject H@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alias and abbreviation | 3 | 0.8333 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Session-template expected | 8 | 0.5714 | 0.6159 | 0.8750 | 1.0000 | 1.0000 |
| Study-strategy expected | 11 | 0.7778 | 0.8123 | 0.9091 | 1.0000 | 1.0000 |
| Unseen wording | 4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Ambiguous | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

The final sensor and safety slice has only two queries, so it is reported separately rather than treated as a stable aggregate. Both returned a sensor intervention at ranks 1 and 5. The continuous-sitting query retrieved its labeled intervention at rank 1. The missing-and-stale-reading query ranked the more literal stale, missing, disconnected, and invalid-reading interventions above the narrower labeled pressure-unreliable fallback, producing record Recall@5 0.5 across this two-query slice despite document-family Hit@1 and Hit@5 of 1.0. No post-test change was made.

## Validation

The completed validation covers query normalization, exact subject and alias matching, ambiguous aliases, safe empty-query behavior, deterministic ordering, scalar metadata filters, cosine score conversion, persistent collection reopening, evaluation-label isolation, development/final ID separation, frozen split hashes, and the public result schema.

The final checkpoint runs all repository tests, retrieval integration checks against the existing Chroma collection, all Stage 5 notebook code cells, notebook JSON parsing, Python compilation, and `git diff --check`. The Chroma manifest passed full logical verification, so the collection was not rebuilt.

## Next stage

Stage 6 is the deterministic daily planning engine. It may consume `RetrievalService` results, but planning decisions, time allocation, break placement, and rescheduling remain deterministic and outside Stage 5.
