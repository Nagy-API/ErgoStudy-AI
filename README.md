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

Stages 1 through 4 are complete. The repository contains a deterministic, validated 477-record knowledge corpus, a 64-query development split and sealed 32-query final-test split, a development-based comparison of four embedding configurations, and a persistent 477-record ChromaDB collection. `minilm_plain` using `sentence-transformers/all-MiniLM-L6-v2` is the selected Stage 4 embedding configuration. The collection is verified for persistence, metadata filtering, logical rebuild reproducibility, and corpus/evaluation separation. The Stage 5 retrieval pipeline, planning, sensor adaptation, local-model integration, API, and Flutter integration have not started.

See [docs/stage3_dataset_report.md](docs/stage3_dataset_report.md) for the dataset checkpoint and [docs/stage4_embedding_chroma_report.md](docs/stage4_embedding_chroma_report.md) for environment, model, metric, performance, index, and persistence results.

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
