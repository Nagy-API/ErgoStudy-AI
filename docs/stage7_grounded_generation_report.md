# Stage 7 local grounded-generation report

## Scope

Stage 7 adds a local wording layer after the deterministic planner and optional sensor adapter. The layer explains completed decisions in concise English. It does not plan, retrieve, change times, add or remove sessions, alter sensor policy, provide medical advice, expose evaluation data, or call a cloud service.

## Local model environment

The official Windows Ollama distribution provides the API at `http://127.0.0.1:11434`. The only language model pulled for this stage is `qwen3:4b-instruct`. The client uses `stream=false`, temperature zero, a 4096-token context, and an explicit JSON schema. No LangChain or additional Python dependency is used.

The final environment record is in `data/processed/local_llm_environment.json`:

- Ollama version: 0.32.5
- Model: `qwen3:4b-instruct`
- Digest: `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`
- Size: 2.497 GB (2,497,293,803 bytes)
- Local API: responding
- Execution: GPU (`NVIDIA GeForce RTX 3050 6GB Laptop GPU`)

## Grounding boundary

`build_grounding_context` deep-copies its inputs and uses an allow list. It includes the original planner request, final deterministic timeline, subject allocations, reasons, methods, warnings, unscheduled subjects, optional sensor result, and only summaries of record IDs used by the plan. Relevant summaries are capped at 220 characters and retain source IDs, evidence level, and review status. The full 477-record corpus, evaluation queries, expected evaluation IDs, file paths, and Git details are never sent to the model.

The LLM output schema contains only the plan summary, exact subject allocations, exact session-order messages, an optional sensor message, an optional unscheduled-subject message, and warnings. Generation metadata is kept outside the model response in a wrapper with one of three modes: `local_llm`, `local_llm_corrected`, or `deterministic_fallback`.

## Validation and fallback

The validator parses JSON into strict immutable models and rejects missing or extra fields, incorrect types, duplicate or changed subjects, changed allocated minutes, missing or changed session references, conflicting minute claims, invented record IDs or user inputs, unsupported subject facts, Markdown, non-English text, warning-count changes, and medical diagnostic or treatment language.

An invalid first response receives one correction request containing the validation errors, original structured context, and exact schema. A second invalid response uses a deterministic template. An unavailable Ollama API also uses that fallback without failing the study-plan request. The fallback is stable for identical structured input and passes the same validator.

## Focused demonstrations

The real local pass covers school and university plans without sensors, an unscheduled subject, an unknown-subject planner fallback, a sensor-triggered movement break, and missing sensor data. The committed outputs and validation summary are in `generation_demo_outputs.json` and `generation_validation_results.json`.

- First-attempt valid JSON: 1 of 6
- Corrected responses: 2
- Deterministic fallbacks: 3
- Average latency: 50.9421 seconds
- Median latency: 26.3237 seconds
- Maximum latency: 180.0673 seconds
- Numeric preservation: passed
- Grounding validation: passed
- Sensor safety: passed

## Verification

The Stage 7 suite has 40 passing tests. Controlled model outputs that change a study allocation, study duration, or break duration; invent a subject or record ID; omit a scheduled subject; use an invalid session order; return malformed JSON; add an unsupported subject fact or user input; use non-English text; or introduce diagnostic language are rejected.

The required Stage 6A and 6B baseline has 41 passing planner, persistent-retrieval integration, sensor-model, policy, adapter, and planner-adapter tests. All six notebook code cells execute. Python compilation, notebook JSON parsing, generated JSON parsing, deterministic fallback repetition, and Git whitespace validation pass. No embedding benchmark ran, retrieval was not retuned, Chroma was not rebuilt, and no other model was downloaded.
