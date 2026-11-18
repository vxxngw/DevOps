import json
import subprocess

from ci.bash_sources import bash_executable
from ci.common import ROOT


def test_entry_scripts_are_executable_in_git():
    # systemd runs scripts straight from a Linux checkout (203/EXEC if the bit is missing);
    # Windows commits default to 100644. *-common.sh files are sourced, not executed.
    listing = subprocess.run(
        ["git", "-c", "safe.directory=*", "ls-files", "-s", "scripts/*.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    modes = {line.split("\t")[1]: line.split()[0] for line in listing}
    assert modes, "no shell scripts found"
    not_executable = [
        path for path, mode in modes.items() if mode != "100755" and not path.endswith("-common.sh")
    ]
    assert not_executable == []


def test_host_health_reports_json_and_exit_code_agrees():
    result = subprocess.run(
        [bash_executable(), (ROOT / "scripts/infra/host-health.sh").as_posix()],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["memory_available_bytes"] > 0 and report["root_disk_free_bytes"] > 0
    assert report["cpus"] >= 1 and report["load1"] >= 0
    assert result.returncode == (0 if report["healthy"] else 1)
