# Stage 4 Embedding and ChromaDB Report

## Outcome

Stage 4 selected `minilm_plain`, using `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The persistent `ergostudy-knowledge-1-0-0` collection contains all 477 validated corpus records and no evaluation-query records. A fresh client verified every ID, document, metadata projection, and manifest marker.

The model decision used only 64 development queries. The 32 final-test query IDs remain sealed, and no final-test retrieval metric or failure analysis was computed.

## Environment

- CPython 3.12.13, 64-bit, on Windows 11.
- PyTorch 2.12.0+cu130 with its bundled CUDA 13.0 runtime and cuDNN 9.2.
- NVIDIA GeForce RTX 3050 6GB Laptop GPU, compute capability 8.6.
- CUDA was available. PyTorch reported 6,441,926,656 total GPU-memory bytes and 5,376,049,152 available bytes at the environment check.
- A GPU dot-product check returned the expected value of 32.0.
- `sentence-transformers==5.5.0`, `chromadb==1.5.9`, `numpy==2.4.3`, `huggingface-hub==1.4.1`, `ipykernel==7.2.0`, and `psutil==7.2.2`.

The local `.venv` uses the existing CPython 3.12 installation. PyTorch came from the official CUDA 13.0 wheel index; the other packages came from official PyPI. No CUDA Toolkit, source build, system-wide package, paid service, local LLM, or unrelated framework was installed.

## Development and sealed-test split

The deterministic split uses seed `20260730` and preserves the original 96-query JSONL unchanged. It contains 64 development IDs and 32 final-test IDs with no overlap. Integrity hashes cover the source file, all IDs, each split's IDs, and the canonical query records.

The development split contains 56 queries with expected record IDs and eight criteria-only queries. It retains three school-related cases, six university-related cases, and three sensor or safety cases. Counts by difficulty, subject family, and expected document family are stored in `data/processed/retrieval_eval_split.json`.

## Candidate configurations

| Configuration | Model and revision | License | Query formatting | Document formatting |
| --- | --- | --- | --- | --- |
| `minilm_plain` | `sentence-transformers/all-MiniLM-L6-v2` @ `1110a243...` | Apache-2.0 | unchanged | unchanged |
| `bge_small_plain` | `BAAI/bge-small-en-v1.5` @ `5c38ec7c...` | MIT | unchanged | unchanged |
| `bge_small_instruction` | same BGE revision | MIT | `Represent this sentence for searching relevant passages: ` | unchanged |
| `e5_small_prefix` | `intfloat/e5-small-v2` @ `ffb93f3b...` | MIT | `query: ` | `passage: ` |

All candidates produced 384-dimensional float32 vectors. SentenceTransformer normalization was enabled and direct ranking used normalized cosine similarity. Model-specific rules were not shared across models.

## Direct development metrics

Record-level metrics use the 56 development queries with expected record IDs. Family-hit metrics use every applicable development query.

| Configuration | R@1 | R@3 | R@5 | R@10 | MRR@10 | nDCG@10 | Doc family H@1 / H@5 | Subject family H@1 / H@5 | Zero relevant top-10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `minilm_plain` | 0.4107 | 0.6518 | 0.7143 | 0.7321 | 0.6429 | 0.6349 | 0.8594 / 0.9375 | 0.8448 / 0.8966 | 13 |
| `bge_small_plain` | 0.3214 | 0.6250 | 0.6964 | 0.7500 | 0.5817 | 0.5868 | 0.7969 / 0.9531 | 0.8448 / 0.8793 | 10 |
| `bge_small_instruction` | 0.4196 | 0.6696 | 0.7143 | 0.7589 | 0.6363 | 0.6427 | 0.8438 / 0.9688 | 0.8621 / 0.8966 | 11 |
| `e5_small_prefix` | 0.3750 | 0.5893 | 0.6339 | 0.7321 | 0.5945 | 0.5883 | 0.7656 / 0.9375 | 0.8103 / 0.8966 | 12 |

Every configuration returned ten results for every query, so the zero-result count was zero. The full overall, difficulty, subject-family, document-family, school, university, sensor/safety, alias, ambiguous, and unseen-wording metrics are in `embedding_benchmark_summary.json`.

## Performance and token lengths

| Configuration | Corpus time (s) | Query average / median / p95 (ms) | Peak GPU bytes | Measured cache bytes | Max corpus tokens / limit | Truncated records |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `minilm_plain` | 2.0860 | 39.13 / 40.70 / 44.70 | 181,239,296 | 91,578,415 | 147 / 256 | 0 |
| `bge_small_plain` | 1.6255 | 79.21 / 81.87 / 99.81 | 314,687,488 | 134,505,940 | 147 / 512 | 0 |
| `bge_small_instruction` | 1.5778 | 66.17 / 65.43 / 96.33 | 448,135,680 | 134,505,940 | 147 / 512 | 0 |
| `e5_small_prefix` | 1.6804 | 73.68 / 76.39 / 89.93 | 581,899,264 | 134,478,697 | 149 / 512 | 0 |

Token lengths were checked before encoding. No corpus record or development query required truncation, so retrieval text was not edited.

## Qualitative development audit

Each candidate was inspected on three exact-name, alias or abbreviation, ambiguous, unseen-wording, topic, study-strategy, and sensor or safety queries. The stored audit includes the query, expected IDs or criteria, top five IDs, titles, document and subject families, cosine scores, and a short assessment for all 84 examples.

The first three examples in each category produced the same labeled top-five hit counts across candidates: exact names 3/3, aliases 2/3, ambiguous queries 3/3, topics 2/2 labeled examples, study strategies 1/2 labeled examples, sensor/safety 1/1 labeled example, and unseen wording 0/1 labeled example. Criteria-only examples were reviewed manually rather than scored through text matching.

The audit separates four limitation types:

- **Embedding-model limitation:** the strategy record for recalling French words did not reach the top five even though the vocabulary topic did. This shows dense search may favor the immediate topic over a useful cross-family strategy.
- **Corpus limitation:** several criteria-only cases have no single gold record, so one dense result cannot cover every desired behavior. This is most visible when a query asks for both subject mapping and study guidance.
- **Evaluation-label limitation:** the query containing `Bio` labeled a `Life Science` alias, while all candidates retrieved the more literal `Bio` alias and relevant biology topics. The retrieved result is sensible but is not one of the narrow expected IDs.
- **Ambiguous-query limitation:** short labels such as `AI` and `CS` retrieved the intended profiles in the audited cases, but dense retrieval alone cannot guarantee correct disambiguation without user or topic context.

The sensor and safety audit found no serious candidate failure. All candidates had sensor/safety Recall@5 of 1.0 on the one ID-labeled case. MiniLM and both BGE configurations had document-family Hit@5 of 1.0 across all three cases; E5 had 0.6667. Diagnostic or symptom wording still requires deterministic safety handling in a later retrieval pipeline; an embedding score must not be treated as a diagnosis rule.

## Model selection

`minilm_plain` and `bge_small_instruction` tied for highest Recall@5 at 0.7143. MiniLM had the higher MRR@10, 0.6429 versus 0.6363, though the difference remained within 0.02. The required critical-slice comparison then favored MiniLM overall: it retained perfect sensor results and combined stronger unseen-wording reciprocal-rank performance with competitive ambiguous-query behavior. MiniLM also had the lowest query latency, peak GPU allocation, and cache size. No candidate was rejected by the documented sensor/safety failure threshold.

The selection therefore follows the required order and is based on ErgoStudy development queries, not public benchmark claims.

## Persistent Chroma design

The project-relative `chroma_db/` path contains one collection, `ergostudy-knowledge-1-0-0`. The caller supplies selected-model embeddings; Chroma's default embedding function is disabled. Each Chroma ID is the source `record_id`, each document is the exact validated `retrieval_text`, and cosine distance is used across all document families.

The HNSW configuration is `space=cosine`, `ef_construction=400`, `ef_search=1000`, and `max_neighbors=32`. The high search setting is appropriate for only 477 records and makes the logical top ten match direct cosine exactly. An initial default-HNSW build differed on one rank-10 candidate for two development queries; this was investigated, attributed to approximate graph search, and resolved by the explicit configuration.

## Metadata projection

The source JSONL remains the rich source of truth. Chroma receives a complete scalar projection with consistent types: document and subject family, evidence and review fields, safety scope, dataset version, school/university support booleans, sensor mode, learning task, cognitive demand, canonical and derivation IDs, primary source ID, source count, and `source_ids_json`. Missing optional strings use an empty string, missing subject family uses `not_applicable`, and source IDs are sorted before deterministic JSON encoding. No internal metadata is concatenated into document text.

## Integrity, persistence, and reproducibility

- Corpus SHA-256: `7b2156a6e49c742041edc53eb721033e042cb3329c0e50ee0cc19e4aa5b024df`.
- All 477 IDs are present, unique, and equal to the corpus ID set.
- All 477 documents and metadata projections match the source records.
- Zero evaluation-query record IDs are in the collection.
- A new `PersistentClient` verified the collection after the building client was closed.
- Normal execution verifies a compatible existing collection instead of adding duplicates.
- `--rebuild` deletes only the exact ErgoStudy collection and leaves unrelated collections untouched in tests.
- Two independent tuned rebuilds produced the identical `baseline_retrieval_results.jsonl` SHA-256: `beefea4344d5c435c4a83bd33d1a2dec8e81ebd28724af00baafe83212e6d492`.
- Chroma and direct cosine top-10 ID sets match on all 64 development queries: average and minimum overlap are both 1.0.

The deterministic manifest records corpus, ID-set, retrieval-text, metadata-projection, model, preprocessing, index, normalization, and package details. Chroma database bytes are intentionally not treated as reproducible artifacts.

## Metadata-filter validation

All requested filters returned records and every returned metadata object satisfied its predicate: subject profiles, topic profiles, computing, mathematics, school support, university support, reviewed records, sensor interventions, and non-medical wellbeing. These filters were demonstrated separately and were not applied to the unfiltered baseline metrics.

## Known limitations

- The 56 ID-labeled development queries are useful but small; some subject slices contain only one labeled query and must not be overinterpreted.
- Thirteen ID-labeled development queries have no expected record in the selected model's top ten. Session-template and cross-family study-strategy retrieval are the clearest weak areas.
- Some expected-ID labels are narrower than reasonable semantic results. Stage 5 should review labels without using or changing the sealed test split.
- Latency and peak memory are target-machine observations, not universal hardware guarantees.
- Hugging Face cache size is safely measured logical cache use and can differ on Windows when symlink support is unavailable.
- The final-test set is deliberately unevaluated, so Stage 4 results are development baselines rather than a final retrieval claim.

## Recommendations for Stage 5

Stage 5 should implement the retrieval interface around this fixed collection, run the sealed final-test evaluation once the pipeline is frozen, preserve citations in returned records, and analyze the session-template and cross-family strategy failures. It should not change the selected embedding configuration based on final-test results. Reranking, hybrid lexical search, answer generation, planning, sensor adaptation, local LLM integration, FastAPI, and Flutter integration remain outside Stage 4.
