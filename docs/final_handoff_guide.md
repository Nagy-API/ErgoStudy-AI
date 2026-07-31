# Final handoff guide

## Scope

The handoff contains the AI one-day study planner only. Physical sensors belong to hardware and Flutter teams; the backend accepts no sensor data, and all users receive the same planner features.

## Verification

From the repository root, run:

```powershell
.venv\Scripts\python.exe scripts\validate_dataset.py
.venv\Scripts\python.exe scripts\verify_chroma_index.py
.venv\Scripts\python.exe scripts\final_validation.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\run_notebook_cells.py 10_end_to_end_demo.ipynb
.venv\Scripts\python.exe -m compileall -q api src scripts
git diff --check
```

Confirm OpenAPI lists exactly the six documented `/api/v1` paths and contains no hardware-specific schema. Confirm the corpus and Chroma collection each contain 463 matching IDs.

## Package

Run `.venv\Scripts\python.exe scripts\build_handoff_package.py` after the final commit. The ignored ZIP must exclude `.git`, `.venv`, caches, `chroma_db`, model/Ollama files, temporary files, secrets, and machine-local configuration. The external ignored manifest records the included file count, ZIP size, SHA-256, exclusions, and source commit. Do not commit the ZIP.

## Runtime

Start with `scripts/run_api.ps1`. Deterministic plan calls do not need Ollama. If optional Ollama wording is unavailable, the API returns a valid fallback. This prototype must remain local because it has no production authentication, TLS, or rate limiting.
