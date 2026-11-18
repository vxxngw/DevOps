<# Re-plan and optionally apply the prepared Jenkins VM. Never uses a stale plan. #>
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$WorkDirectory = 'E:\DevOpsVMs\jenkins\terraform',
    [string]$TerraformPath = '',
    [string]$VirtualBoxDirectory = 'E:\VirtualBox',
    [string]$GitToolsDirectory = 'C:\Program Files\Git\usr\bin'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $TerraformPath) {
    $TerraformPath = Join-Path $root '.infra-local\bin\windows\terraform.exe'
}
foreach ($file in @($TerraformPath, (Join-Path $WorkDirectory 'terraform.tfvars.json'),
        (Join-Path $VirtualBoxDirectory 'VBoxManage.exe'), (Join-Path $GitToolsDirectory 'cp.exe'))) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required file missing: $file" }
}
$env:PATH = "$VirtualBoxDirectory;C:\Windows\System32;$GitToolsDirectory;" + $env:PATH
$env:VBOX_INSTALL_PATH = $VirtualBoxDirectory
$env:TF_IN_AUTOMATION = '1'
$source = Join-Path $root 'infra\terraform-virtualbox\main.tf'
$active = Join-Path $WorkDirectory 'main.tf'
if ((Get-FileHash $source).Hash -ne (Get-FileHash $active).Hash) {
    throw 'Prepared Terraform source differs from repository. Review and sync before planning.'
}
$link = Get-Item -LiteralPath (Join-Path $HOME '.terraform\virtualbox')
if ($link.LinkType -ne 'Junction' -or [string]$link.Target -ne 'E:\DevOpsVMs\terraform-virtualbox') {
    throw 'Expected E-drive provider storage junction is missing or differs.'
}
$statePath = Join-Path $WorkDirectory 'terraform.tfstate'
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    foreach ($resource in $state.resources) {
        foreach ($instance in $resource.instances) {
            if ($instance.status -eq 'tainted') {
                throw 'Partial/tainted Terraform resource exists. Diagnose the existing VM before planning; do not recreate or untaint blindly.'
            }
        }
    }
}
& $TerraformPath "-chdir=$WorkDirectory" validate -no-color
if ($LASTEXITCODE) { throw 'Terraform validation failed.' }
& $TerraformPath "-chdir=$WorkDirectory" plan -input=false -no-color '-out=jenkins.tfplan'
if ($LASTEXITCODE) { throw 'Terraform plan failed.' }
$json = & $TerraformPath "-chdir=$WorkDirectory" show -json 'jenkins.tfplan'
if ($LASTEXITCODE) { throw 'Cannot read saved plan.' }
$plan = $json | ConvertFrom-Json
$changes = @($plan.resource_changes | Where-Object { ($_.change.actions -join ',') -ne 'no-op' })
foreach ($change in $changes) {
    if ($change.address -ne 'virtualbox_vm.jenkins' -or
        ($change.change.actions -join ',') -ne 'create' -or
        $change.change.after.name -ne 'anuyen-jenkins' -or
        $change.change.after.cpus -ne 2 -or $change.change.after.memory -ne '6.0 gib') {
        throw 'Refusing unexpected resource change, replacement or deletion.'
    }
}
if (-not $Apply) { Write-Output 'Plan checked. No VM was created. Use -Apply to provision.'; return }
& (Join-Path $PSHOME 'pwsh.exe') -NoProfile -NonInteractive -File (
    Join-Path $PSScriptRoot 'preflight-jenkins-virtualbox.ps1')
if ($LASTEXITCODE) { throw 'Host capacity check failed. Nothing was applied.' }
& $TerraformPath "-chdir=$WorkDirectory" apply -input=false -no-color 'jenkins.tfplan'
if ($LASTEXITCODE) {
    throw 'Apply failed. Inspect Terraform state and VBoxManage list vms before retrying; do not delete manually.'
}