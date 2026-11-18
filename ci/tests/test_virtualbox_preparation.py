import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_virtualbox_is_separate_and_protected():
    source = (ROOT / "infra/terraform-virtualbox/main.tf").read_text()
    assert "terra-farm/virtualbox" in source
    assert "= 0.2.2-alpha.1" in source
    assert "prevent_destroy = true" in source
    assert "filesha256(var.image_archive)" in source
    assert "filesha256(var.seed_iso)" in source
    assert "private_key" not in source
    assert "libvirt" in (ROOT / "infra/terraform/versions.tf").read_text()


def test_apply_has_capacity_and_plan_guards():
    source = (ROOT / "scripts/invoke-jenkins-virtualbox.ps1").read_text()
    assert source.index("preflight-jenkins-virtualbox.ps1") < source.index(
        '"-chdir=$WorkDirectory" apply'
    )
    assert "'virtualbox_vm.jenkins'" in source
    assert "'anuyen-jenkins'" in source
    assert "if (-not $Apply)" in source
    assert "Host capacity check failed" in source
    assert "$instance.status -eq 'tainted'" in source
    assert source.index("$instance.status -eq 'tainted'") < source.index(
        '"-chdir=$WorkDirectory" plan'
    )


def test_iso_uses_nocloud_label_and_refuses_overwrite():
    source = (ROOT / "scripts/new-nocloud-iso.ps1").read_text()
    assert "VolumeName = 'cidata'" in source
    assert "@('user-data', 'meta-data')" in source
    assert "FileMode.CreateNew" in source


def test_prepared_seed_when_available():
    seed = Path("E:/DevOpsVMs/jenkins/seed/user-data")
    if not seed.exists():
        import pytest

        pytest.skip("Local prepared seed is not available on this host")
    config = json.loads(seed.read_text().split("\n", 1)[1])
    assert config["ssh_pwauth"] is False
    assert config["disable_root"] is True
    user = config["users"][0]
    assert user["name"] == "clinicops"
    assert user["lock_passwd"] is True
    assert user["ssh_authorized_keys"][0].startswith("ssh-ed25519 ")
    assert "virtualbox-guest-utils" in config["packages"]
