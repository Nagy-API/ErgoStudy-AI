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

Stages 1 through 3 are complete. The repository now contains a deterministic, validated Stage 3 knowledge corpus with 477 retrievable records, 96 separate evaluation queries, source metadata, reusable build and validation modules, unit tests, and two focused notebooks. Embeddings, ChromaDB, retrieval, planning, sensor adaptation, local-model integration, the API, and Flutter integration have not started.

See [docs/stage3_dataset_report.md](docs/stage3_dataset_report.md) for the complete counts, validation results, source additions, limitations, and hardware questions.

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
