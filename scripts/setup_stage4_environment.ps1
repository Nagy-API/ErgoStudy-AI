param(
    [string]$PythonPath = "",
    [switch]$CpuOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    if (-not $PythonPath) {
        $PythonPath = (py -3.12 -c "import sys; print(sys.executable)")
    }
    & $PythonPath -m venv --copies (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -m pip install "pip==25.0.1"
$TorchIndex = if ($CpuOnly) { "https://download.pytorch.org/whl/cpu" } else { "https://download.pytorch.org/whl/cu130" }
$TorchVersion = if ($CpuOnly) { "torch==2.12.0" } else { "torch==2.12.0+cu130" }
& $VenvPython -m pip install $TorchVersion --index-url $TorchIndex
& $VenvPython -m pip install --index-url "https://pypi.org/simple" `
    "sentence-transformers==5.5.0" `
    "chromadb==1.5.9" `
    "numpy==2.4.3" `
    "huggingface-hub==1.4.1" `
    "ipykernel==7.2.0" `
    "psutil==7.2.2"

& $VenvPython -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available())"
