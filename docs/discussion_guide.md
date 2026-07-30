# ErgoStudy AI discussion guide

## Core ideas in simple language

### Why this is Hybrid RAG

RAG means retrieval-augmented generation: the system retrieves relevant records before producing its final wording. ErgoStudy is hybrid because dense embedding search is combined with exact alias handling and deterministic Python rules. Retrieval supplies traceable guidance; the planner supplies the actual decision; the local LLM is only an optional wording layer.

### Why the LLM does not calculate the plan

Language models can vary, make arithmetic mistakes, or invent details. A study schedule needs stable totals and rules. Python therefore owns scoring, allocation, sessions, breaks, sensor actions, and fallbacks. The same normalized input and configuration produce the same plan.

### How embeddings and ChromaDB work

MiniLM converts text into a 384-number vector called an embedding. Texts with related meaning tend to have vectors near each other. ChromaDB stores the 477 corpus vectors and metadata. At request time, it compares the query vector with stored vectors, applies the frozen retrieval logic, and returns record IDs, text, and source metadata.

### Why MiniLM was selected

Three local embedding candidates and multiple preprocessing configurations were compared on the development set. `minilm_plain` met the quality band and offered the best final balance of retrieval quality, speed, memory, and a permissive Apache-2.0 license. The exact model revision is pinned for repeatability.

### How retrieval was evaluated

The 96 queries were split before tuning: 64 development queries and 32 sealed final queries. The frozen retriever was evaluated on the final set only once. Recall measures how much labelled relevant evidence was found, MRR rewards finding a relevant item early, NDCG considers ranked relevance, and family Hit@5 checks whether the correct kind of record appears in the first five results.

### How planning scores are calculated

Each subject score is `0.35 × priority + 0.25 × workload + 0.20 × difficulty + 0.20 × knowledge gap`. Knowledge gap comes from the inverse of current understanding. The weights are transparent prototype settings, not scientific facts. Higher scores receive scheduling priority when time is limited.

### How breaks fit inside total time

The planner does not add breaks after using all available time. It schedules study sessions and breaks together, then verifies `study minutes + break minutes <= available minutes`. Unused time is reported explicitly. Sensor-added movement time must also fit within the original window.

### How sensor adaptation works

The adapter accepts normalized fields such as continuous sitting minutes, posture direction, pressure imbalance, reading age, and current session progress. It applies configured rules to future sessions only. It can add or extend a movement break, shorten a future session, defer future study, or show a calm reminder. Completed work and the current protected portion are preserved.

### Why sensor rules are non-medical

The sensor does not diagnose posture, pain, injury, or disease. The thresholds are prototype product parameters awaiting hardware confirmation and user testing. Wording suggests a short movement or comfortable repositioning action and never claims treatment or health outcomes.

### How FastAPI connects to Flutter

Flutter sends JSON to the local `/api/v1` endpoints. Pydantic validates it. FastAPI returns versioned JSON models that Flutter can map into Dart classes. The response includes a request ID for troubleshooting. The Flutter guide lists emulator and desktop addresses and recommends different timeouts for fast planning and optional explanations.

### Why deterministic fallback matters

The plan must remain usable if the subject is unknown, the sensor is missing, or Ollama is unavailable. An unknown subject receives general safe study methods and a visible fallback flag. Bad sensor data makes no sensor-based change. LLM failure returns verified template wording with HTTP 200. These fallbacks keep optional components from breaking the core application.

### Current limitations and future work

This is a local prototype with a small curriculum-neutral corpus and a 32-query sealed final retrieval set. The sensor contract is normalized rather than connected to real hardware. The planner settings need user testing. There is no Flutter implementation, authentication, TLS, deployment, or production monitoring. Future work should begin with interface integration and user/hardware validation before considering broader data, retrieval changes, or deployment.

## Likely questions and short answers

1. **What problem does ErgoStudy solve?** It turns student priorities, workload, difficulty, understanding, and available time into one practical daily schedule.
2. **Is it a chatbot?** No. Its main product is a structured deterministic plan; natural-language explanation is optional.
3. **Why call it AI?** It uses semantic embeddings and retrieval to match natural language to relevant knowledge, plus an optional local model for wording.
4. **What makes the RAG hybrid?** Dense Chroma search is combined with exact alias resolution and rule-based planning.
5. **Does Qwen choose the study time?** No. Python calculates every score, allocation, session, break, and sensor change before Qwen receives the result.
6. **Can the LLM change a number?** Its proposed JSON is rejected if subjects, minutes, sessions, or sensor facts differ from the deterministic context.
7. **What happens after rejected model output?** The system allows one correction attempt, then uses a deterministic validated response.
8. **Why use a local model?** It keeps the prototype offline, avoids paid APIs, and allows a fallback when the local service is unavailable.
9. **Why `qwen3:4b-instruct`?** It is the single frozen Stage 7 model that was evaluated on the available machine; Stage 9 did not add or compare models.
10. **Why MiniLM?** It provided the chosen balance of development-set retrieval quality, 384-dimensional efficiency, local speed, memory use, and licensing.
11. **How large is the dataset?** It has 477 retrievable records from 29 recorded sources and 96 separate evaluation queries.
12. **Are all 477 records manually written evidence?** No. There are 277 canonical records and 200 controlled synthetic aliases. Aliases add names, not new factual claims.
13. **How do you prevent evaluation leakage?** Evaluation queries are stored outside the corpus, development and final IDs are separated, and final-test IDs are checked against development artifacts.
14. **What was final Recall@5?** 0.8621 on the sealed 32-query final set.
15. **What was final MRR@10?** 0.8728, meaning relevant records usually appeared early, while not claiming every query was perfect.
16. **What if a subject is unknown?** The plan uses explicit general fallback methods and returns `KNOWLEDGE_FALLBACK` instead of inventing a source.
17. **What does the score mean?** It is a transparent prototype priority score based on four student inputs, not a grade or prediction.
18. **Can a low-score subject be omitted?** Yes, when the available window cannot fit another minimum useful session; it appears in `unscheduled_subjects` with a reason.
19. **Are breaks outside the entered time?** No. Breaks are included in the same total and the response reports study, break, planned, and unallocated minutes.
20. **Can the sensor reorder subjects?** No. It may adjust future timing but cannot change academic scoring or priority.
21. **What happens with stale sensor data?** It is treated as unavailable and the normal timer-based plan is preserved.
22. **Does the sensor diagnose bad posture?** No. It applies non-medical product rules to normalized observations and uses calm comfort wording.
23. **Is the sensor required?** No. The main planner works completely without it.
24. **How fast is the planner?** In the final local test, warm `/plans` averaged 113.010 ms over 20 measured requests.
25. **Why was `/plans/full` once faster than `/plans`?** That was a single-request result. Repeated measurements gave 113.010 ms versus 114.440 ms, so the anomaly was not reproduced.
26. **Can five students call it together?** Five simultaneous local smoke requests all passed, but that test is not evidence of production-scale capacity.
27. **What if Ollama takes too long?** The explanation endpoint returns deterministic wording and an `OLLAMA_TIMEOUT` reason; the plan stays valid.
28. **How does Flutter use it?** Flutter sends JSON requests and maps the versioned response schema into Dart transport models.
29. **Is the API ready for the public internet?** No. It lacks authentication, TLS termination, rate limiting, and production hardening.
30. **What would you build next?** First validate the frozen contract with a Flutter interface, confirm real sensor fields, and run user testing and independent content review.
