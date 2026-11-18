<#
.SYNOPSIS
Read-only Windows capacity check for the Jenkins VirtualBox VM. Does not provision.
#>
[CmdletBinding()]
param(
    [string]$StoragePath = 'E:\DevOpsVMs',
    [string]$VirtualBoxPath = 'E:\VirtualBox\VBoxManage.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$checks = [System.Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Passed, $Detail) {
    $checks.Add([pscustomobject]@{ name = $Name; passed = $Passed; detail = $Detail })
}

$os = Get-CimInstance Win32_OperatingSystem
$freeMiB = [math]::Floor($os.FreePhysicalMemory / 1024)
# VM 6 GiB plus 2 GiB available headroom; not a global Windows minimum.
Add-Check 'available_memory' ($freeMiB -ge 8192) @{
    availableMiB = $freeMiB; vmMiB = 6144; additionalHeadroomMiB = 2048
}
$cpu = Get-CimInstance Win32_Processor
$logical = ($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum
Add-Check 'cpu' ($logical -ge 2) @{ logicalProcessors = $logical; vmVcpus = 2 }
$fullStorage = [IO.Path]::GetFullPath($StoragePath)
$driveRoot = [IO.Path]::GetPathRoot($fullStorage)
if ($driveRoot -notmatch '^[A-Za-z]:\\$') {
    throw 'Choose a local drive for VirtualBox storage, not a network path.'
}
$disk = Get-PSDrive -Name $driveRoot.Substring(0, 1) -PSProvider FileSystem
$freeGiB = [math]::Round($disk.Free / 1GB, 2)
Add-Check 'storage' ($disk.Free -ge 44GB) @{
    path = $fullStorage; freeGiB = $freeGiB; vmDiskGiB = 32; requiredFreeGiB = 44
}
$vboxExists = Test-Path -LiteralPath $VirtualBoxPath -PathType Leaf
Add-Check 'virtualbox_executable' $vboxExists $VirtualBoxPath
if ($vboxExists) {
    $version = & $VirtualBoxPath --version 2>&1
    $versionExit = $LASTEXITCODE
    Add-Check 'virtualbox_cli' ($versionExit -eq 0) ($version -join "`n")
    $running = & $VirtualBoxPath list runningvms 2>&1
    $runningExit = $LASTEXITCODE
    Add-Check 'running_vm_query' ($runningExit -eq 0) ($running -join "`n")
}

$passed = @($checks | Where-Object { -not $_.passed }).Count -eq 0
$report = [ordered]@{
    checkedAt = (Get-Date).ToString('o')
    scope = 'Host capacity only; no VM, download, process stop, network change or provisioning'
    status = $(if ($passed) { 'CAPACITY_READY' } else { 'BLOCKED' })
    checks = @($checks.ToArray())
    limitation = 'Capacity readiness does not verify Ubuntu image, bridged networking, BIOS settings or Terraform VirtualBox provider compatibility.'
}
$folder = Join-Path $root '.infra-local'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$json = $report | ConvertTo-Json -Depth 6
$json | Set-Content -LiteralPath (Join-Path $folder 'jenkins-virtualbox-host.json') -Encoding utf8
Write-Output $json
if (-not $passed) { exit 2 }