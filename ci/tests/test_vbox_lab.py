import importlib.util
import json

import pytest

from ci.common import ROOT

spec = importlib.util.spec_from_file_location("vbox_lab", ROOT / "scripts/infra/vbox-lab.py")
vbox_lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vbox_lab)


def test_checksum_lookup_matches_exact_filename():
    sums = "aaa *ubuntu-24.04-server-cloudimg-amd64.vmdk.manifest\nbbb *ubuntu-24.04-server-cloudimg-amd64.vmdk\n"
    assert vbox_lab.expected_sha256(sums, vbox_lab.IMAGE) == "bbb"
    with pytest.raises(ValueError):
        vbox_lab.expected_sha256("ccc *other.img\n", vbox_lab.IMAGE)


def test_seed_creates_key_only_operator_and_static_hostonly_ip():
    files = vbox_lab.seed_files("ssh-ed25519 AAAA lab\n", "192.168.56.10", "anuyen-lab")
    header, body = files["user-data"].split("\n", 1)
    config = json.loads(body)
    assert header == "#cloud-config" and config["ssh_pwauth"] is False
    user = config["users"][0]
    assert user["name"] == "clinicops" and user["lock_passwd"] is True
    assert user["ssh_authorized_keys"] == ["ssh-ed25519 AAAA lab"]
    netplan = json.loads(config["write_files"][0]["content"])
    assert netplan["network"]["ethernets"]["enp0s8"]["addresses"] == ["192.168.56.10/24"]
    assert "local-hostname: anuyen-lab" in files["meta-data"]
