param(
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$configurationPath = Join-Path $projectRoot "config\generation_config.json"
$configuration = Get-Content -Raw -LiteralPath $configurationPath | ConvertFrom-Json
$baseUrl = $configuration.ollama_base_url.TrimEnd("/")
$modelName = $configuration.model_name

try {
    $version = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/version" -TimeoutSec 2
} catch {
    Write-Host "Ollama readiness: unavailable. Deterministic ErgoStudy endpoints remain usable."
    exit 1
}

try {
    $showBody = @{ model = $modelName } | ConvertTo-Json -Compress
    $null = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/show" -ContentType "application/json" -Body $showBody -TimeoutSec 5
} catch {
    Write-Host "Ollama readiness: model '$modelName' is not available locally. No download was attempted."
    exit 1
}

$warmupBody = @{
    model = $modelName
    stream = $false
    keep_alive = "10m"
    messages = @(
        @{ role = "system"; content = "You are a local readiness check. /no_think" }
        @{ role = "user"; content = "Reply with READY only." }
    )
    options = @{
        temperature = 0
        num_ctx = 512
        num_predict = 8
    }
} | ConvertTo-Json -Depth 6 -Compress

$started = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $response = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/chat" -ContentType "application/json" -Body $warmupBody -TimeoutSec $TimeoutSeconds
    $started.Stop()
} catch {
    $started.Stop()
    Write-Host "Ollama readiness: warm-up generation did not finish within the local limit."
    Write-Host "Deterministic endpoints remain ready; use their fallback during the presentation."
    exit 1
}

if (-not $response.message.content) {
    Write-Host "Ollama readiness: warm-up returned no content."
    exit 1
}

Write-Host "Ollama readiness: ready"
Write-Host "Version: $($version.version)"
Write-Host "Model: $modelName"
Write-Host ("Warm-up latency: {0:N0} ms" -f $started.Elapsed.TotalMilliseconds)
Write-Host "No model was downloaded. The model will remain warm for the live explanation demo."
exit 0
