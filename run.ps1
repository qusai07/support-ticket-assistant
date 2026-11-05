# One-command local run (Windows PowerShell):
#   .\run.ps1         fast mode: production build of the web app (pages load in ~0.2 s)
#   .\run.ps1 -Dev    development mode: hot reload, but each page compiles on first visit (2-4 s)
# Starts the API (8000), the AI worker and the web app (3000) in three windows.
# Requirements: Ollama running, models pulled, .venv created (see README > Setup).
param([switch]$Dev)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
# 127.0.0.1 instead of "localhost": on Windows, localhost tries IPv6 first (~2 s wasted per call).
$apiUrl = "http://127.0.0.1:8000"; $webUrl = "http://127.0.0.1:3000"

if (-not (Test-Path $py)) {
    Write-Host "No .venv found. Run first:  py -3.11 -m venv .venv ; .venv\Scripts\pip install -e .[dev]" -ForegroundColor Red
    exit 1
}
try { Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null }
catch { Write-Host "Ollama is not running. Start the Ollama app first." -ForegroundColor Red; exit 1 }

foreach ($port in 8000, 3000) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "Port $port is already in use. Close the previous API/Web windows first." -ForegroundColor Red; exit 1
    }
}

if (-not (Test-Path "storage\chroma")) {
    Write-Host "Building the vector index (first run only)..." -ForegroundColor Cyan
    & $py -m scripts.build_index
}

Write-Host "Applying database migrations..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot ".venv\Scripts\alembic.exe") upgrade head
& $py -m scripts.seed_users   # idempotent: creates demo accounts only if missing

Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='API'; & '$py' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='Worker'; & '$py' -m app.worker"

$web = Join-Path $PSScriptRoot "web"
if (-not (Test-Path "web\node_modules")) {
    Write-Host "Installing web dependencies (first run only)..." -ForegroundColor Cyan
    Push-Location web; npm install --no-audit --no-fund; Pop-Location
}
if ($Dev) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='Web (dev)'; Set-Location '$web'; npm run dev"
} else {
    # Production build into its own folder, so it never collides with a dev server's .next
    Write-Host "Building the web app (about 1 minute)..." -ForegroundColor Cyan
    Push-Location web
    $env:NEXT_DIST_DIR = ".next-prod"
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "Web build failed (see above)." -ForegroundColor Red; exit 1 }
    Pop-Location
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='Web'; Set-Location '$web'; `$env:NEXT_DIST_DIR='.next-prod'; npm run start"
}

Write-Host "Waiting for the API..." -ForegroundColor Cyan
foreach ($i in 1..30) {
    try { Invoke-RestMethod "$apiUrl/health" -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep 2 }
}
Write-Host "Waiting for the web app..." -ForegroundColor Cyan
foreach ($i in 1..60) {
    try { Invoke-WebRequest "$webUrl/login" -UseBasicParsing -TimeoutSec 3 | Out-Null; break } catch { Start-Sleep 2 }
}
Start-Process "http://localhost:3000"
Write-Host "Running:  App http://localhost:3000   API docs http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Sign in: admin@lumora.example / Lumora-demo-2026 (or agent.tech@, lead.tech@, analyst@ ...)" -ForegroundColor Green
Write-Host "Stop: close the three PowerShell windows (API, Worker, Web)." -ForegroundColor Green
