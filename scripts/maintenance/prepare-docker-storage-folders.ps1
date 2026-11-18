param(
    [Parameter(Mandatory)][string]$DataRoot,
    [Parameter(Mandatory)][string]$BackupRoot
)
$ErrorActionPreference='Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'This preparation step needs Windows administrator approval' }
$approved=@([IO.Path]::GetFullPath($DataRoot).TrimEnd([IO.Path]::DirectorySeparatorChar),[IO.Path]::GetFullPath($BackupRoot).TrimEnd([IO.Path]::DirectorySeparatorChar))
if ($approved[0] -eq $approved[1] -or
    $approved[0].StartsWith($approved[1]+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
    $approved[1].StartsWith($approved[0]+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Data and backup directories must be distinct and non-overlapping' }
foreach ($directory in $approved) {
    $resolved=[IO.Path]::GetFullPath($directory)
    if ($resolved -notin $approved -or $resolved.TrimEnd([IO.Path]::DirectorySeparatorChar) -eq [IO.Path]::GetPathRoot($resolved).TrimEnd([IO.Path]::DirectorySeparatorChar)) { throw 'Path must match an explicit destination and cannot be a drive root' }
    New-Item -ItemType Directory -Path $resolved -Force | Out-Null
    & icacls.exe $resolved /inheritance:r /grant:r "$($identity.Name):(OI)(CI)F" 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not grant access to approved destination: $resolved" }
}
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Path (Join-Path $projectRoot '.ci-local') -Force | Out-Null
@{at_utc=(Get-Date).ToUniversalTime().ToString('o');prepared=$approved;account=$identity.Name;operation='Create approved folders and grant current user, SYSTEM and Administrators access; no data moved'} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $projectRoot '.ci-local/storage-folders-ready.json') -Encoding utf8
