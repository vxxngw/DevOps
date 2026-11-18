import os
import shutil
import subprocess

import pytest

from ci.bash_sources import bash_executable
from ci.common import ROOT


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "backup project"
    scripts = root / "scripts/infra"
    scripts.mkdir(parents=True)
    for name in ["backup.sh", "restore.sh", "backup-common.sh"]:
        shutil.copyfile(ROOT / "scripts/infra" / name, scripts / name)
    (root / "Jenkinsfile").touch()
    (root / "pyproject.toml").touch()
    return root


def execute(checkout, script, args, environment=None):
    env = os.environ.copy()
    env.update(environment or {})
    return subprocess.run(
        [bash_executable(), (checkout / "scripts/infra" / script).as_posix(), *args],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.mark.parametrize("profile", ["production", "unknown"])
def test_restore_never_accepts_production_or_unknown_profile(checkout, profile):
    result = execute(checkout, "restore.sh", [profile, "unused.dump", "clinic_restore_test"])
    assert result.returncode == 2 and "restricted to dev/staging" in result.stderr


@pytest.mark.parametrize(
    "database", ["clinic", "postgres", "clinic_restore_x;DROP", "clinic_restore_" + "a" * 31]
)
def test_restore_rejects_live_or_unsafe_database_before_transport(checkout, database):
    result = execute(checkout, "restore.sh", ["dev", "unused.dump", database])
    assert result.returncode == 2 and "new clinic_restore_ database" in result.stderr


def test_dev_backup_root_cannot_escape_private_checkout(checkout, tmp_path):
    outside = tmp_path / "outside"
    result = execute(checkout, "backup.sh", ["dev"], {"CLINIC_BACKUP_ROOT": outside.as_posix()})
    assert result.returncode == 2 and "inside .infra-local/db-backups" in result.stderr
    assert not outside.exists()


def test_bad_checksum_is_rejected_before_any_database_creation(checkout):
    directory = checkout / ".infra-local/db-backups/dev"
    directory.mkdir(parents=True)
    artifact = directory / "clinic-dev-20261115T000000Z.dump"
    artifact.write_bytes(b"not-a-valid-backup")
    artifact.with_suffix(".dump.sha256").write_text("0" * 64 + "  " + artifact.name + "\n")
    result = execute(checkout, "restore.sh", ["dev", artifact.as_posix(), "clinic_restore_test"])
    assert result.returncode != 0 and "FAILED" in result.stdout
    assert "restore_database_created" not in result.stdout
