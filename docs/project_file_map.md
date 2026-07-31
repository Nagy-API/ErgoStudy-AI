# Project file map

- `api/`: FastAPI application, strict schemas, lifecycle, dependencies, settings, and safe errors.
- `src/`: dataset, embedding, retrieval, deterministic planner, grounding, generation, and validation modules.
- `config/`: planner, embedding, and generation configuration.
- `data/raw/`: reviewed source seeds for subjects, topics, strategies, sessions, and aliases.
- `data/interim/`: schema, examples, and non-sensor retrieval query seeds.
- `data/processed/`: deterministic corpus, split, retrieval results, Chroma manifest, demos, and validation reports.
- `data/sources/source_catalog.csv`: 23 source mappings used by active records.
- `tests/`: dataset, retrieval, planner, generation, API, OpenAPI, and scope-regression coverage.
- `notebooks/`: focused environment, dataset, retrieval, planner, generation, API, and end-to-end demonstrations.
- `scripts/`: build, validate, index, evaluate, verify, demo, API, notebook, and handoff commands.
- `docs/`: current architecture, contract, integration, demo, report, discussion, and handoff material.

No AI sensor adapter, policy, model, endpoint, corpus family, demo, or test exists. Physical hardware remains outside this repository under hardware and Flutter ownership.
