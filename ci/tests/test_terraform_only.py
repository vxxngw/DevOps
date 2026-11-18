from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_active_control_does_not_require_ansible():
    for name in ("setup-infra-control.sh", "check-infra-control.sh", "install-infra-tools.py"):
        assert "ansible" not in (ROOT / "scripts" / name).read_text().lower()
    assert not (ROOT / "infra/ansible").exists()
    assert "requirements-ansible" not in (ROOT / "ci/security.py").read_text()


def test_plain_ssh_outputs_and_lifecycle_guards():
    outputs = (ROOT / "infra/terraform/outputs.tf").read_text()
    assert 'output "ssh_targets"' in outputs
    assert "ansible_inventory" not in outputs
    assert "prevent_destroy = true" in (ROOT / "infra/terraform-virtualbox/main.tf").read_text()


def test_host_timer_script_preserves_security_boundary():
    script = (ROOT / "scripts/configure-host.sh").read_text()
    assert "OnUnitActiveSec=5min" in script
    assert "NoNewPrivileges=true" in script
    assert "systemctl enable --now clinic-host-health.timer" in script
    assert "ufw allow" not in script