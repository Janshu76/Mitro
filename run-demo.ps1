$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating the local Python environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv. Install Python 3.11 or newer and retry." }
}

Write-Host "Installing or updating Mitro dependencies..."
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

Write-Host "Loading the included regulatory sources..."
& $python -m mitro.cli bootstrap
if ($LASTEXITCODE -ne 0) { throw "Source bootstrap failed." }

Write-Host "Starting Mitro at http://127.0.0.1:8000/"
Write-Host "Keep this window open while presenting. Press Ctrl+C to stop."
& $python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000
