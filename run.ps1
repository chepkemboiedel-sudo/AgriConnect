# AgriConnect AI - one-command launcher (Windows PowerShell)
# Usage:  right-click > Run with PowerShell, or:  ./run.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "Installing dependencies (fastapi, uvicorn)..." -ForegroundColor Green
python -m pip install -q -r requirements.txt

Write-Host "Starting AgriConnect AI at http://127.0.0.1:8000 ..." -ForegroundColor Green
python -m agriconnect
