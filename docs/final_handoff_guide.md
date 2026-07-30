# Final handoff guide

## Release identity

- Project: ErgoStudy AI
- Version: `1.0.0-prototype`
- API version: `v1`
- Intended use: local competition demonstration and code review
- Production status: not production-ready

The Git tag `v1.0.0-prototype` identifies the finalized source. The handoff ZIP is generated locally and is not committed.

## What the recipient receives

The source package contains Python source, FastAPI code, configuration, notebooks, tests, documentation, raw seed data, processed JSON/JSONL/CSV data required to rebuild the Chroma collection, `requirements.txt`, environment setup, index build, API startup, validation, prewarm, and demo scripts.

It excludes Git history, virtual environments, caches, Chroma contents, model files, temporary files, secrets, and machine-specific paths. `data/processed/package_manifest.json` is an external generated manifest because embedding a ZIP's own SHA-256 inside that ZIP would be self-referential.

## Setup on Windows

1. Install 64-bit CPython 3.12, Git, and PowerShell.
2. Create a repository-local virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   ```

3. Install a PyTorch build suitable for the target machine, then install the pinned requirements:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Build the local Chroma index from the included processed corpus:

   ```powershell
   .venv\Scripts\python.exe scripts\build_chroma_index.py
   .venv\Scripts\python.exe scripts\verify_chroma_index.py
   ```

5. Run the tests:

   ```powershell
   .venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

The selected MiniLM revision must be available locally. The setup script documents the original Stage 4 environment. Ask before downloading a model on a managed or bandwidth-limited machine.

## Optional Ollama setup

Ollama is not required for planning. If the local `qwen3:4b-instruct` model already exists, check and warm it without downloading anything:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prewarm_ollama.ps1
```

A nonzero result means the live explanation should use its deterministic backup. Do not increase the normal API timeout to hide a slow machine.

## Run the application and demo

Start the API:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_api.ps1
```

Open `http://127.0.0.1:8000/docs`. Use `/api/v1/plans/full` for the primary demonstration and `/api/v1/plans/full-with-explanation` only for the optional local-model step.

The convenience command prewarms Ollama when possible and starts the API:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1
```

Use `-RefreshOutputs` only when intentionally re-running the final scenarios. Performance values are machine-specific and should not be silently replaced in presentation material.

## Reproduce final validation

```powershell
.venv\Scripts\python.exe scripts\validate_dataset.py
.venv\Scripts\python.exe scripts\final_validation.py
.venv\Scripts\python.exe scripts\run_notebook_cells.py 10_end_to_end_demo.ipynb
.venv\Scripts\python.exe -m compileall -q api src scripts
.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

The final validator writes the scenario, performance, and validation JSON artifacts. It performs one real optional Ollama request unless `--skip-real-ollama` is supplied.

## Build and verify the handoff package

Run after checking out the final tagged commit:

```powershell
.venv\Scripts\python.exe scripts\build_handoff_package.py
```

The script audits text for machine-specific paths and common secret patterns, creates a deterministic source ZIP under the ignored `handoff` directory, reopens it for a content/corruption audit, calculates SHA-256, and writes `data/processed/package_manifest.json`. Compare the manifest's `git_commit` with `git rev-parse HEAD`, then verify the ZIP independently with:

```powershell
Get-FileHash -Algorithm SHA256 handoff\ErgoStudy-AI-1.0.0-prototype.zip
```

## Operational boundaries

- Keep the API on localhost.
- Do not place tokens or machine-specific `.env` files in the repository.
- Do not commit the Chroma directory, model cache, Ollama model files, virtual environment, ZIP, or generated external package manifest.
- Treat a deterministic explanation fallback as successful behavior.
- Treat stale or missing sensor observations as unavailable data.
- Do not describe sensor output as diagnosis or treatment.
- Do not change frozen retrieval, planner, or sensor settings only to improve demo numbers.

## Support starting points

Read `README.md` for setup, `docs/api_contract.md` for transport details, `docs/flutter_integration_guide.md` for client mapping, `docs/competition_demo_script.md` for presentation flow, and `docs/discussion_guide.md` for design questions.
