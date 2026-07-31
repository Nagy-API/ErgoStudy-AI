# Dataset design

The active corpus supports one-day study planning through five retrievable families: subject profiles, topic profiles, study strategies, session templates, and controlled subject aliases. Evaluation queries are stored separately and never indexed.

Every factual record preserves a stable ID, family, title, retrieval text, evidence level, source IDs, review state, review tier, dataset version, and relevant educational metadata. Synthetic aliases inherit their reviewed parent's sources and introduce no evidence claim.

The physical product's sensors are outside the AI corpus and belong to hardware and Flutter teams. The corpus contains no sensor intervention family, hardware aliases, readings, or hardware-specific metadata. Normal study-session and timer-break records remain valid planner knowledge.
