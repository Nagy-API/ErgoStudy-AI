# ErgoStudy AI

ErgoStudy AI is the working title for a local, posture-aware daily study planner. The planned system will combine deterministic scheduling, source-grounded knowledge retrieval, optional sensor data, and a local language model. A Flutter application will communicate with the Python backend through FastAPI.

## Problem statement

Students often need to decide what to study, for how long, when to pause, and how to recover when a plan changes. Generic schedules do not account for subject priority, difficulty, workload, current understanding, or physical strain from prolonged sitting. This project aims to produce a practical one-day plan from those inputs while keeping important planning decisions predictable and explainable.

## Main users

- Students who want a structured daily study plan.
- Students using only the Flutter application, without additional hardware.
- Students who also use the planned smart back-support sensor.
- Project reviewers who need to inspect and explain the system's data, decisions, and evaluation.

## Operating modes

### Without a sensor

The planned non-sensor mode will support daily planning, timed study sessions, scheduled breaks, completion feedback, and plan rescheduling.

### With a sensor

The planned sensor mode will additionally accept readings such as continuous sitting duration, posture direction, pressure imbalance, and poor-posture duration. These readings will be used by a deterministic adapter to adjust breaks and session timing. Hardware fields and thresholds will not be finalized until the real sensor contract is documented.

## High-level architecture

The intended flow is:

1. A Flutter app submits study and optional sensor inputs.
2. FastAPI validates the request.
3. A retrieval component obtains relevant, source-traceable guidance from a persistent ChromaDB store.
4. A deterministic planning engine creates the schedule.
5. A sensor adapter applies documented timing and break rules when sensor data is available.
6. A local language model explains the grounded result without changing the schedule rules.
7. FastAPI returns structured JSON to Flutter.

See [docs/system_architecture.md](docs/system_architecture.md) for the planned component boundaries.

## Current status

Stages 1 through 5 are complete. The repository contains a deterministic, validated 477-record knowledge corpus, the fixed `minilm_plain` embedding configuration, a persistent 477-record ChromaDB collection, and a reusable production `RetrievalService`. Stage 5 added exact ambiguity-preserving alias resolution, deterministic query analysis, scalar metadata filters, structured source-preserving results, development failure analysis, a frozen retrieval configuration, and a one-time evaluation of the 32-query sealed test set.

The frozen `alias_plus_dense` retriever achieved development Recall@5 0.8661 and MRR@10 0.8750, then sealed final-test Recall@5 0.8621 and MRR@10 0.8728. Final document-family and subject-family Hit@5 were both 1.0000. The deterministic planning engine is the next stage; sensor adaptation, local-model integration, API implementation, and Flutter integration have not started.

See [docs/stage3_dataset_report.md](docs/stage3_dataset_report.md), [docs/stage4_embedding_chroma_report.md](docs/stage4_embedding_chroma_report.md), and [docs/stage5_retrieval_report.md](docs/stage5_retrieval_report.md) for the completed checkpoints.

## Project tracking

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for confirmed requirements, technical decisions, open questions, and the latest validation checkpoint.

## Planned stages

- Environment and scaffold
- Dataset design and source strategy
- Dataset creation and validation
- Embeddings and ChromaDB
- Retrieval and retrieval evaluation
- Deterministic daily planning engine
- Sensor-aware adaptation
- Local LLM and grounded generation
- FastAPI integration
- Full system evaluation and demo

Detailed goals and completion criteria are in [PROJECT_PLAN.md](PROJECT_PLAN.md).

## Dataset build and validation

Stage 3 uses only the Python standard library. From the repository root:

```powershell
python scripts/build_dataset.py
python scripts/validate_dataset.py
python -m unittest discover -s tests -v
```

The notebooks can be opened when Jupyter is installed:

```powershell
jupyter notebook notebooks/01_dataset_creation.ipynb
jupyter notebook notebooks/02_dataset_validation.ipynb
```

No model, embedding package, or vector database is required for Stage 3.

## Stage 4 embedding and index workflow

Stage 4 uses the repository-local `.venv`. On Windows, create or verify it with the existing CPython 3.12 interpreter, then install the pinned packages:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_stage4_environment.ps1 -PythonPath "C:\path\to\python.exe"
```

The benchmark downloads only the three configured embedding models. The build and verification scripts use the resolved cached revision offline:

```powershell
.venv\Scripts\python.exe scripts\benchmark_embeddings.py
.venv\Scripts\python.exe scripts\build_chroma_index.py
.venv\Scripts\python.exe scripts\verify_chroma_index.py
```

Use `--rebuild` only when intentionally replacing the exact ErgoStudy collection:

```powershell
.venv\Scripts\python.exe scripts\build_chroma_index.py --rebuild
```

The `.venv`, Hugging Face model cache, raw embedding arrays, and `chroma_db` contents are local artifacts and are ignored by Git.

## Stage 5 retrieval workflow

The production service loads only the selected cached model and existing Chroma collection:

```python
from pathlib import Path
from src.retriever import RetrievalService

with RetrievalService.from_frozen_config(Path.cwd()) as retriever:
    results = retriever.retrieve(
        "How should I study Mathematics equations?",
        top_k=5,
        metadata_filters={"reviewed": True},
    )
```

Development comparison, failure analysis, and the sealed final-test artifacts are already complete. The evaluator refuses another final run while the final artifacts exist:

```powershell
.venv\Scripts\python.exe scripts\inspect_retrieval_failures.py
.venv\Scripts\python.exe scripts\run_notebook_cells.py 05_retrieval_pipeline.ipynb
```
