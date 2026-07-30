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

The non-sensor mode supports deterministic daily planning and timer-based study sessions and breaks. Sensor-disabled or unusable observations preserve this plan unchanged.

### With a sensor

The sensor mode accepts normalized application-level observations such as continuous sitting minutes, posture direction, pressure imbalance, and poor-posture duration. A deterministic adapter may adjust only future breaks and session lengths while preserving academic scores, priorities, methods, and retrieved record IDs. Raw hardware communication and device calibration remain outside the repository.

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

Stages 1 through 7 are complete. The repository contains a deterministic, validated 477-record knowledge corpus, the fixed `minilm_plain` embedding configuration, a persistent 477-record ChromaDB collection, a reusable production `RetrievalService`, a deterministic daily planner, a deterministic sensor-adaptation layer, and a local grounded wording layer. Stage 7 uses only `qwen3:4b-instruct` through the local Ollama API with schema-constrained JSON, strict value and safety validation, one correction attempt, and a deterministic fallback.

The frozen `alias_plus_dense` retriever achieved development Recall@5 0.8661 and MRR@10 0.8750, then sealed final-test Recall@5 0.8621 and MRR@10 0.8728. Final document-family and subject-family Hit@5 were both 1.0000. FastAPI integration is the next stage; API implementation and Flutter integration have not started.

See [docs/stage3_dataset_report.md](docs/stage3_dataset_report.md), [docs/stage4_embedding_chroma_report.md](docs/stage4_embedding_chroma_report.md), [docs/stage5_retrieval_report.md](docs/stage5_retrieval_report.md), [docs/stage6a_daily_planner_report.md](docs/stage6a_daily_planner_report.md), [docs/stage6b_sensor_adaptation_report.md](docs/stage6b_sensor_adaptation_report.md), and [docs/stage7_grounded_generation_report.md](docs/stage7_grounded_generation_report.md) for the completed checkpoints.

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

## Stage 6A daily planner workflow

The planner accepts plain JSON-compatible dictionaries and does not require an LLM:

```python
from pathlib import Path
from src.daily_planner import DailyPlanner
from src.retriever import RetrievalService

root = Path.cwd()
with RetrievalService.from_frozen_config(root, device="cpu") as retriever:
    planner = DailyPlanner(root, retrieval_service=retriever)
    plan = planner.plan({
        "total_available_minutes": 90,
        "preferred_start_time": "16:00",
        "subjects": [{
            "name": "Stats",
            "topics": ["Probability"],
            "difficulty": 4,
            "priority": 5,
            "workload": 4,
            "current_understanding": 2,
        }],
    })
    print(plan.to_dict())
```

Regenerate the committed school, university, short-window, and fallback demos with:

```powershell
.venv\Scripts\python.exe scripts\generate_study_plan.py --device cpu
.venv\Scripts\python.exe scripts\run_notebook_cells.py 06_daily_planner.ipynb
```

Planner weights and time bounds are in `config/planner_config.json`. They are versioned prototype product settings rather than universal scientific values.

## Stage 6B sensor adaptation workflow

Apply one normalized observation to an existing `DailyStudyPlan` or its dictionary form:

```python
from pathlib import Path
from src.sensor_adapter import SensorPlanAdapter

adapter = SensorPlanAdapter(Path.cwd())
adapted = adapter.adapt(plan, {
    "sensor_enabled": True,
    "connection_status": "connected",
    "observation_status": "valid",
    "continuous_sitting_minutes": 50,
    "poor_posture_duration_minutes": 12,
    "posture_direction": "leaning_right",
    "pressure_imbalance_detected": True,
    "reading_age_seconds": 5,
    "current_session_order": 1,
    "elapsed_session_minutes": 25,
})
print(adapted.to_dict())
```

Regenerate and inspect the committed sensor scenarios with:

```powershell
.venv\Scripts\python.exe scripts\adapt_study_plan.py
.venv\Scripts\python.exe scripts\run_notebook_cells.py 07_sensor_adaptation.ipynb
```

Sensor thresholds and time bounds are in `config/sensor_policy.json`. They are configurable, non-medical prototype product parameters pending user testing and hardware-team confirmation.

## Stage 7 local grounded-generation workflow

Stage 7 explains an already-complete deterministic plan. It cannot change allocations, session or break durations, priorities, record IDs, or sensor actions. Check the local environment and run the six focused demos with:

```powershell
.venv\Scripts\python.exe scripts\check_ollama.py
.venv\Scripts\python.exe scripts\generate_grounded_response.py
.venv\Scripts\python.exe scripts\run_notebook_cells.py 08_grounded_generation.ipynb
```

The generation settings in `config/generation_config.json` lock the client to the local Ollama API, `qwen3:4b-instruct`, `stream=false`, temperature zero, a 4096-token context, and one correction attempt. If Ollama is unavailable or both model responses fail validation, the request returns a stable template response with `generation_mode` set to `deterministic_fallback`.
