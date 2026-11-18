param(
    [Parameter(Mandatory)][string]$TargetDisk,
    [string]$SourceDisk = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Docker/wsl/disk/docker_data.vhdx')
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sourceDisk=[IO.Path]::GetFullPath($SourceDisk)
$resolvedTarget=[IO.Path]::GetFullPath($TargetDisk)
if ([IO.Path]::GetExtension($resolvedTarget) -ne '.vhdx' -or $resolvedTarget -eq $sourceDisk) { throw 'Target must be a VHDX file distinct from the source disk' }
function Get-DiskLock([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @{path=$Path;exists=$false;sharing_locked=$false} }
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
        $stream.Dispose()
        return @{path=$Path;exists=$true;exclusive_read=$true;sharing_locked=$false}
    } catch {
        $cause=$_.Exception
        while ($null -ne $cause.InnerException) { $cause=$cause.InnerException }
        $code=$cause.HResult -band 0xffff
        return @{path=$Path;exists=$true;exclusive_read=$false;sharing_locked=($code -in @(32,33));error_code=$code}
    }
}
$source=Get-DiskLock $sourceDisk
$target=Get-DiskLock $resolvedTarget
$server=& docker version --format '{{json .Server}}' 2>&1
$engineOk=($LASTEXITCODE -eq 0)
$containers=@()
$volumes=@()
if ($engineOk) {
    $containers=@(& docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}')
    $volumes=@(& docker volume ls --format '{{.Name}}')
}
$sourceInactive=(-not $source.exists) -or ($source.exclusive_read -eq $true)
$activeOnTarget=$engineOk -and $target.sharing_locked -and $sourceInactive
$snapshot=[ordered]@{
    at_utc=(Get-Date).ToUniversalTime().ToString('o')
    status=$(if ($activeOnTarget) {'TARGET_DISK_LOCK_AND_ENGINE_VERIFIED_STACK_PENDING'} else {'BLOCKED_TARGET_NOT_VERIFIED'})
    scope='Read-only paths/locks and engine inventory; no data removed, no stack health/business claim'
    source=$source;target=$target;engine_available=$engineOk
    containers=$containers;volumes=$volumes
    disk_free_bytes=@{source=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($sourceDisk)).AvailableFreeSpace;target=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($resolvedTarget)).AvailableFreeSpace}
}
$destination=Join-Path $projectRoot ('docs/evidence/docker-active-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
New-Item -ItemType Directory -Path $destination | Out-Null
$snapshot | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $destination 'metadata.json') -Encoding utf8
Write-Output "$($snapshot.status): $destination"
if (-not $activeOnTarget) { exit 1 }
