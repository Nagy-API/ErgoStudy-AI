# Project Status

## Project name

ErgoStudy AI - Posture-Aware Daily Study Planner

## Completed stage

Environment and scaffold.

The repository structure, project rules, initial documentation, architecture draft, environment inspection notebook, and Git repository have been created. No dataset, retrieval system, planner, sensor logic, local model integration, or API implementation has started.

## Current stage

The environment and scaffold stage is at its final repository checkpoint. Work is paused after setup validation.

## Next planned stage

Dataset design and source strategy. This stage will define knowledge scope, record structure, metadata, source-quality rules, licensing requirements, citation handling, and validation criteria before any dataset content is created.

## Confirmed product requirements

- All system content, code, documentation, API fields, notebooks, and generated responses must be in English.
- The system is intended for school and university students.
- Users will enter custom subject names rather than choosing only from a fixed subject list.
- The system will create one-day study plans.
- Plans will include study sessions and breaks.
- The project will use local and free models only.
- Development will target a Windows environment.
- The product will support both sensor and non-sensor modes.
- Sensor data may include continuous sitting duration, posture direction, pressure distribution or imbalance, and poor-posture duration.
- The system will use a substantial validated dataset.
- The target architecture includes a persistent vector database, deterministic planner, sensor adapter, local LLM, and FastAPI.
- Dataset quality and evaluation are more important than inflating the row count.

## Confirmed technical decisions

- Flutter will communicate with the local Python backend through FastAPI and structured JSON.
- Python 3.12 is the recommended initial project interpreter for library compatibility.
- Jupyter notebooks will be used for learning, development, demonstrations, and discussion.
- Reusable production logic will live in Python modules.
- Filesystem code will use `pathlib` where appropriate and remain Windows-friendly.
- ChromaDB is the planned persistent vector database, with semantic retrieval and metadata filtering.
- Planning, time allocation, break placement, rescheduling, and sensor adaptations will be deterministic and testable.
- The local LLM will explain grounded results but will not override planner or sensor-adaptation decisions.
- Factual educational and health-related records will preserve source, citation, and license metadata.
- Source-backed records will be validated before any synthetic expansion.
- Paid APIs will not be used.
- LangChain will not be used unless a later stage demonstrates a concrete need.
- No model or embedding choice is final until candidates are evaluated on the target hardware and project evaluation set.

## Open questions

- Which school age ranges, university levels, and subject types should the first dataset cover?
- Should the knowledge scope contain only study and scheduling guidance, or also ergonomics and posture guidance?
- Which authoritative source categories and licenses are acceptable?
- What health-safety boundary and disclaimer policy should the project enforce?
- Which citation format should processed records and generated responses use?
- Who will manually review records, and what quality threshold will define acceptance?
- What initial dataset size is substantial but still realistic to validate carefully?
- What representative questions and expected answers should form the retrieval evaluation set?
- What are the confirmed sensor fields, units, sampling rate, calibration method, and missing-data behavior?
- Should the initial knowledge remain curriculum-neutral, or target a specific country or education system?

## Last validation results

The setup validation completed successfully on July 30, 2026:

- The environment notebook contains valid notebook JSON.
- All notebook code cells executed successfully without future RAG dependencies.
- Python files compiled successfully.
- All requested scaffold files were present.
- The English-content audit found no non-ASCII project text.
- Git contained no commits and showed only the intended setup-stage files before this checkpoint commit.
- No datasets, models, large files, or heavy packages were downloaded or installed.
