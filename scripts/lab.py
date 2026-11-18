"""Run real Terraform lab operations only after host preflight. No shell/Vagrant replacement."""

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["plan", "apply", "destroy"])
    parser.add_argument("--var-file", required=True)
    parser.add_argument("--confirm-prefix")
    parser.add_argument("--environment", choices=["lab", "staging", "production"], default="lab")
    args = parser.parse_args()
    if platform.system() != "Linux":
        raise RuntimeError(
            "Run under the prepared Linux/WSL control node, never through Windows local libvirt"
        )
    if args.operation != "destroy":
        subprocess.run([sys.executable, str(ROOT / "scripts/preflight-infra.py")], check=True)
    terraform = str(ROOT / ".infra-local/bin/linux/terraform")
    command = [terraform, "-chdir=" + str(ROOT / "infra/terraform")]
    var_file = Path(args.var_file).resolve()
    if not var_file.is_file():
        raise ValueError("Actual ignored tfvars file is required")
    subprocess.run(command + ["init", "-input=false", "-lockfile=readonly"], check=True)
    # Keep independent fleet states separate; never implicitly switch an existing fleet.
    workspace = subprocess.check_output(command + ["workspace", "show"], text=True).strip()
    if workspace != args.environment:
        raise ValueError(
            f"Select/create Terraform workspace {args.environment!r} explicitly before this operation; current={workspace!r}"
        )
    if args.operation == "destroy":
        nodes = json.loads(
            subprocess.check_output(command + ["output", "-json", "nodes"], text=True)
        )
        if (
            not args.confirm_prefix
            or not nodes
            or any(
                not item["name"].startswith(args.confirm_prefix + "-") for item in nodes.values()
            )
        ):
            raise ValueError("Confirm the actual project prefix; no unrelated VM teardown")
        subprocess.run(command + ["destroy", "-var-file=" + str(var_file)], check=True)
    else:
        plan = ROOT / ".infra-local" / (args.environment + ".tfplan")
        subprocess.run(
            command + ["plan", "-var-file=" + str(var_file), "-out=" + str(plan)], check=True
        )
        if args.operation == "apply":
            confirmation = input(f"Review the plan above. Type {args.environment!r} to apply: ")
            if confirmation != args.environment:
                raise ValueError("Apply cancelled; environment confirmation did not match")
            subprocess.run(command + ["apply", str(plan)], check=True)


if __name__ == "__main__":
    main()
