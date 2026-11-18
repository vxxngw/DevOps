import subprocess
from types import SimpleNamespace

import pytest

from ci.ansible_sources import check_local_sources
from ci.bash_sources import check_bash_sources
from ci.common import ROOT


def role(tmp_path, tasks):
    import yaml

    target = tmp_path / "infra/ansible/roles/backup/tasks/main.yml"
    target.parent.mkdir(parents=True)
    target.write_text(yaml.safe_dump(tasks), encoding="utf-8")


def test_actual_backup_and_template_sources_exist():
    checked = check_local_sources(ROOT)["checked"]
    paths = {item["path"] for item in checked}
    assert {
        "scripts/infra/backup.sh",
        "scripts/infra/restore.sh",
        "scripts/infra/host-health.sh",
        "scripts/infra/backup-common.sh",
    } <= paths


def test_missing_later_loop_source_is_rejected(tmp_path):
    role(
        tmp_path,
        [
            {
                "block": [
                    {
                        "ansible.builtin.copy": {
                            "src": "{{ playbook_dir }}/../../scripts/infra/{{ item }}"
                        },
                        "loop": ["first.sh", "missing.sh"],
                    }
                ]
            }
        ],
    )
    script = tmp_path / "scripts/infra/first.sh"
    script.parent.mkdir(parents=True)
    script.touch()
    with pytest.raises(ValueError, match="Missing Ansible local source"):
        check_local_sources(tmp_path)


def test_remote_source_does_not_require_controller_file(tmp_path):
    role(tmp_path, [{"ansible.builtin.copy": {"src": "/opt/generated/binary", "remote_src": True}}])
    report = check_local_sources(tmp_path)
    assert report["checked"] == [] and len(report["remote_sources"]) == 1


def test_controller_source_cannot_escape_repo(tmp_path):
    role(tmp_path, [{"ansible.builtin.copy": {"src": str(tmp_path.parent / "outside")}}])
    with pytest.raises(ValueError, match="escapes"):
        check_local_sources(tmp_path)


def test_unknown_source_template_cannot_silently_pass(tmp_path):
    role(tmp_path, [{"ansible.builtin.copy": {"src": "{{ unknown }}/file"}}])
    with pytest.raises(ValueError, match="Unsupported"):
        check_local_sources(tmp_path)


def test_bash_checks_nested_files_as_separate_commands(tmp_path):
    for relative in ["scripts/first.sh", "scripts/nested/second.sh"]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("true\n")
    commands = []

    def record(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0)

    results = check_bash_sources(tmp_path, runner=record)
    assert len(results) == len(commands) == 2
    assert all(len(command) == 3 and command[1] == "-n" for command in commands)


def test_bash_detects_invalid_later_file(tmp_path):
    folder = tmp_path / "scripts/nested"
    folder.mkdir(parents=True)
    (folder / "first.sh").write_text("true\n")
    (folder / "second.sh").write_text("if then\n")
    with pytest.raises(subprocess.CalledProcessError):
        check_bash_sources(tmp_path)


def test_empty_bash_check_is_not_success(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        check_bash_sources(tmp_path)
