param([ValidateSet('smoke', 'soft-minimal')][string]$Suite = 'smoke')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
$evidenceFolder = Join-Path $projectRoot ('docs/evidence/ui-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
New-Item -ItemType Directory -Force -Path $evidenceFolder | Out-Null
foreach ($previewPort in @(18000, 15173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $previewPort -ErrorAction SilentlyContinue) {
        throw "Port $previewPort is already in use. Stop this check without affecting existing services."
    }
}
New-Item -ItemType Directory -Force -Path 'tmp' | Out-Null
$previewDb = Join-Path $projectRoot ('tmp/ui-' + [guid]::NewGuid().ToString('N') + '.db')
$env:DATABASE_URL = 'sqlite:///' + ($previewDb -replace '\\', '/')
$env:PYTHONPATH = Join-Path $projectRoot 'services'
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\alembic.exe upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Preview migration failed' }
& .\.venv\Scripts\python.exe -m clinic.seed
if ($LASTEXITCODE -ne 0) { throw 'Preview seed failed' }
$apiProcess = $null
$uiProcess = $null
try {
    $apiProcess = Start-Process -FilePath (Join-Path $projectRoot '.venv/Scripts/python.exe') -ArgumentList @('-m', 'uvicorn', 'clinic.api:app', '--host', '127.0.0.1', '--port', '18000', '--no-access-log', '--log-config', 'services/logging.json') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $evidenceFolder 'api.stdout.log') -RedirectStandardError (Join-Path $evidenceFolder 'api.stderr.log')
    $uiProcess = Start-Process -FilePath (Get-Command node).Source -ArgumentList @('node_modules/vite/bin/vite.js', '--config', 'tests/vite.preview.config.ts', '--host', '127.0.0.1', '--port', '15173', '--strictPort') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $evidenceFolder 'vite.stdout.log') -RedirectStandardError (Join-Path $evidenceFolder 'vite.stderr.log')
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-WebRequest -Uri 'http://127.0.0.1:18000/ready' -TimeoutSec 1 | Out-Null
            Invoke-WebRequest -Uri 'http://127.0.0.1:15173' -TimeoutSec 1 | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Preview servers not ready; inspect evidence logs' }
    Push-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    $suiteFile = if ($Suite -eq 'soft-minimal') { 'tests/soft-minimal-smoke.cjs' } else { 'tests/smoke.cjs' }
    try { & node $suiteFile $evidenceFolder; $smokeExit = $LASTEXITCODE } finally { Pop-Location }
    if ($smokeExit -ne 0) { throw 'UI smoke failed; inspect evidence metadata' }
} finally {
    if ($null -ne $apiProcess -and -not $apiProcess.HasExited) { Stop-Process -InputObject $apiProcess }
    if ($null -ne $uiProcess -and -not $uiProcess.HasExited) { Stop-Process -InputObject $uiProcess }
}
Write-Output "UI evidence: $evidenceFolder"
