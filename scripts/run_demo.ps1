param(
    [switch]$SkipPrewarm,
    [switch]$RefreshOutputs,
    [switch]$SkipApi
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$apiExitCode = 0
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "The repository-local .venv is missing. Follow the README setup steps first."
}

Push-Location $projectRoot
try {
    if (-not $SkipPrewarm) {
        & powershell -ExecutionPolicy Bypass -File "scripts\prewarm_ollama.ps1"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Continuing with deterministic planning and the expected explanation fallback."
            $global:LASTEXITCODE = 0
        }
    }

    if ($RefreshOutputs) {
        & $pythonPath "scripts\final_validation.py" --skip-performance
        if ($LASTEXITCODE -ne 0) {
            throw "The demo scenarios did not all pass."
        }
    }

    Write-Host "Demo input: data\processed\final_demo_inputs.json"
    Write-Host "Saved outputs: data\processed\final_demo_outputs.json"
    Write-Host "Interactive API: http://127.0.0.1:8000/docs"
    Write-Host "Use /api/v1/plans/full for the deterministic live path."
    Write-Host "Use /api/v1/plans/full-with-explanation only for the optional local-LLM step."

    if (-not $SkipApi) {
        & $pythonPath -m uvicorn api.main:app --host 127.0.0.1 --port 8000
        $apiExitCode = $LASTEXITCODE
    }
} finally {
    Pop-Location
}

exit $apiExitCode
