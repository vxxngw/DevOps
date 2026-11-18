$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
foreach ($requiredService in @('postgres', 'rabbitmq', 'mailpit')) {
    $serviceId = & docker compose ps -a -q $requiredService
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($serviceId)) { throw "Missing dev service $requiredService. Start the dev stack before integration tests." }
    $readiness = & docker inspect --format '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' $serviceId
    if ($LASTEXITCODE -ne 0 -or $readiness.Trim() -ne 'true healthy') { throw "Dev service $requiredService is not running and healthy. Restore it before integration tests; no DB or queue was changed by this preflight." }
}
$evidenceRelative = 'docs/evidence/integration-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$evidenceAbsolute = Join-Path $projectRoot $evidenceRelative
New-Item -ItemType Directory -Force -Path $evidenceAbsolute | Out-Null
$env:EVIDENCE_DIR = './' + $evidenceRelative
$started = (Get-Date).ToUniversalTime().ToString('o')
& docker compose -f compose.yaml -f compose.test.yaml run --rm --no-deps integration-tests *> (Join-Path $evidenceAbsolute 'pytest.log')
$testExit = $LASTEXITCODE
$sourceHashes = @{}
Get-ChildItem -LiteralPath 'services','tests','contracts' -Recurse -File | Where-Object { $_.Extension -in @('.py','.json') } | ForEach-Object { $sourceHashes[$_.FullName.Substring($projectRoot.Length + 1)] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
$metadata = @{ started_at_utc = $started; ended_at_utc = (Get-Date).ToUniversalTime().ToString('o'); commit = 'UNCOMMITTED'; scope = 'Linux dev image dependencies with current services/contracts/tests bound read-only -> isolated PostgreSQL test DB + RabbitMQ queues + SMTP Mailpit; not a scanned SHA image claim'; exit_code = $testExit; command = 'docker compose -f compose.yaml -f compose.test.yaml run --rm --no-deps integration-tests'; source_files = @($sourceHashes.Keys | Sort-Object | ForEach-Object { @{path=$_;sha256=$sourceHashes[$_]} }) }
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceAbsolute 'metadata.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $evidenceAbsolute 'pytest.log') -Tail 80
Write-Output "Integration evidence: $evidenceRelative; exit=$testExit"
exit $testExit
