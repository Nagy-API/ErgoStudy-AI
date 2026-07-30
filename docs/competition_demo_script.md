# Competition demo script

## Demo setup

Use the `long_sitting_adaptation` request in `data/processed/final_demo_inputs.json`. Before the presentation, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prewarm_ollama.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1 -SkipPrewarm
```

Keep these ready in separate tabs: the README architecture section, `/docs`, the `POST /api/v1/plans/full` endpoint, the saved Stage 9 results, and the final notebook. The normal demonstration uses the deterministic endpoint first. The local explanation is an optional final step.

## 5–7 minute presentation flow

### 0:00–0:40 — Problem and product

**Show:** The project title and one simple diagram from the README.

**Say:** “Students often know what subjects they have, but still need to decide what to study first, how long to spend, and when to take a break. ErgoStudy AI turns those inputs into one clear daily plan. It can work without hardware, and it can make safe timing adjustments when a normalized sensor observation is available.”

**Expected result:** The audience understands that this is a daily planning prototype, not a tutoring chatbot or medical system.

### 0:40–1:15 — Why the AI feature matters

**Show:** The Hybrid RAG flow: retrieval, Python planner, optional language model.

**Say:** “The AI part helps match natural subject names and topics to our validated knowledge collection, then explains the result in clear English. Important numbers are not left to a language model. Python rules calculate the score, time allocation, sessions, and breaks.”

### 1:15–1:55 — User input

**Show:** `long_sitting_adaptation` in `final_demo_inputs.json` or paste it into `/api/v1/plans/full`.

**Say:** “This student has 150 minutes for Mathematics and Biology. They provide difficulty, priority, workload, and current understanding. The optional observation says the student has been sitting continuously for 65 minutes.”

**Expected result:** The request is accepted with HTTP 200.

### 1:55–2:35 — RAG retrieval

**Show:** The returned `retrieved_record_ids` and the project file map or a matching corpus record.

**Say:** “MiniLM converts the request into an embedding. Chroma searches 477 records. The fixed retriever also handles controlled aliases such as CS and Stats. Every returned record ID must exist in the corpus, so the planner can trace its suggested methods back to project data.”

**Expected result:** Mathematics and Biology sessions contain real record IDs and recommended methods.

### 2:35–3:20 — Planner output

**Show:** `original_plan.scheduled_subjects`, totals, then `sessions`.

**Say:** “The score uses priority, workload, difficulty, and knowledge gap. The planner allocates study time in score order, splits it into valid sessions, and includes every break in the same 150-minute limit. Notice that the result is structured JSON that the Flutter application can use directly.”

**Expected result:** Total planned minutes do not exceed 150; study and break durations are positive; sessions are ordered.

### 3:20–4:05 — Sensor adaptation

**Show:** `adapted_plan.triggers`, `actions`, `sessions`, and totals.

**Say:** “The 65-minute reading activates the configured extended-sitting rule. The adapter adds movement time and fits the change inside the original window by changing only future timing. It does not change subject scores, priorities, methods, or retrieval evidence. These are prototype comfort rules, not medical advice.”

**Expected result:** Trigger `extended_continuous_sitting` appears; the adapted total stays within 150 minutes.

### 4:05–4:35 — FastAPI response for Flutter

**Show:** The response model in `/docs` and the request ID.

**Say:** “FastAPI validates both input and output. Flutter receives a stable versioned response with a request ID, original plan, optional adapted plan, and final sessions. Invalid input uses one safe error format and never returns stack traces or local file paths.”

### 4:35–5:15 — Optional local LLM explanation

**Show:** The saved `ollama_available_explanation` output first. If the prewarm succeeded and time allows, call `/api/v1/plans/full-with-explanation` with the 60-minute Mathematics input.

**Say:** “The local Qwen model only phrases the completed plan. Its JSON is checked against exact deterministic values. Our measured prewarmed example needed one correction and completed in about 17.6 seconds. This step is optional; the normal application uses the fast deterministic endpoint.”

**Expected result:** `generation_mode` is `local_llm` or `local_llm_corrected`. A fallback is also a valid response.

### 5:15–5:45 — Safety fallback

**Show:** `ollama_timeout_fallback` and `stale_sensor_fallback` in the saved outputs.

**Say:** “If Ollama is slow, the API returns the same verified plan with deterministic English and an `OLLAMA_TIMEOUT` reason. If the sensor is stale or missing, no sensor adjustment is applied. These are expected safety behaviors, not system crashes.”

### 5:45–6:30 — Key evaluation results

**Show:** `final_evaluation_results.json` and the performance table in the final report.

**Say:** “All 12 final scenarios and all 171 unit tests passed. Final retrieval Recall@5 was 0.8621 and MRR@10 was 0.8728. Warm planning averaged 113 milliseconds, sensor adaptation about 3.9 milliseconds, and five simultaneous deterministic requests all succeeded. These are local prototype results, not production capacity claims.”

## Backup plans

If Ollama is slow, do not wait through the presentation. Show the preserved real output and the timeout-fallback output, explain that wording is optional, and continue with `/plans/full`. A deterministic fallback is expected valid behavior.

If the sensor is unavailable, omit `sensor_observation` or show the `stale_sensor_fallback` scenario. The timer-based plan remains complete and unchanged. Make clear that the product is designed to work without hardware.

If the API is not already running, use the executed notebook output and saved JSON artifacts. They preserve the exact evaluated inputs and responses.
