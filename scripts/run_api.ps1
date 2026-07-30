param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "The repository-local Python environment was not found."
}

Set-Location -LiteralPath $ProjectRoot
& $PythonPath -m uvicorn api.main:app --host $HostAddress --port $Port
