# Discussion guide

Key points a student should be able to explain:

- The backend is a deterministic one-day study planner with semantic retrieval, not a hardware-aware planner.
- Physical sensors remain in the product, but hardware and Flutter teams own them; the backend receives no readings and offers no extra AI feature to hardware owners.
- MiniLM embeds the query, ChromaDB returns source-traceable records, and Python calculates all scores, allocations, sessions, reasons, and timer-based breaks.
- The fixed score is `0.35 × priority + 0.25 × workload + 0.20 × difficulty + 0.20 × knowledge gap`.
- Aliases resolve controlled names such as `CS`; unknown subjects use a clear fallback; short windows can leave lower-ranked subjects unscheduled.
- Ollama only explains the finished plan. Strict validation prevents number or structure changes, and unavailability or timeout returns deterministic wording.
- The current corpus has 463 records and the compatible 30-query final evaluation scored Recall@5 `0.9038`, MRR@10 `0.9274`, nDCG@10 `0.9198`, and both family Hit@5 metrics `1.0000`.
- The prototype is local and not production-ready. It lacks authentication, deployment, Flutter UI, and broader independent evaluation.

Avoid claiming medical, hardware, universal learning, or production-performance conclusions.
