import json
import subprocess

from ci.bash_sources import bash_executable
from ci.common import ROOT


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
