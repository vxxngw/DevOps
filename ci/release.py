import argparse
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET

from ci.common import IMAGES, OUTPUT, PRIVATE, ROOT, TOOLS, commit, now, read_json, run, write_json


def verify_pull(reference, *, env, log, delays=(5, 10, 20, 40)):
    # GHCR may answer "not found" for a digest pushed a few seconds ago; the last attempt still fails hard.
    for delay in delays:
        if run(["docker", "pull", reference], env=env, log=log, check=False).returncode == 0:
            return
        time.sleep(delay)
    run(["docker", "pull", reference], env=env, log=log)


def junit_passed(path, *, allow_skips):
    cases = ET.parse(path).getroot().findall(".//testcase")
    if not cases or any(
        case.find("failure") is not None or case.find("error") is not None for case in cases
    ):
        raise ValueError(f"JUnit is missing real passing tests: {path.name}")
    if not allow_skips and any(case.find("skipped") is not None for case in cases):
        raise ValueError("Integration skips cannot count as a complete integration gate")
    return len(cases)


def verified_gates(revision):
    built = read_json(OUTPUT / "built-images.json")
    security = read_json(OUTPUT / "security-summary.json")
    secret = read_json(OUTPUT / "secret-gate.json")
    if any(item.get("commit") != revision for item in [built, security, secret]):
        raise ValueError("Gate evidence belongs to another commit")
    if set(security["images"]) != set(IMAGES) or secret.get("findings") != 0:
        raise ValueError("Incomplete security gates")
    for filename, expected in [
        ("gitleaks.json", secret["report_sha256"]),
        ("trivy-dependencies.json", security["dependency_report_sha256"]),
    ]:
        if hashlib.sha256((OUTPUT / "security" / filename).read_bytes()).hexdigest() != expected:
            raise ValueError("Security report changed after the gate")
    for name in IMAGES:
        record = security["images"][name]
        report = OUTPUT / "security" / ("trivy-" + name + ".json")
        if (
            record.get("critical") != 0
            or record["image_id"] != built["images"][name]["image_id"]
            or record["report_sha256"] != hashlib.sha256(report.read_bytes()).hexdigest()
        ):
            raise ValueError("Scanned image/report does not match build evidence")
    for kind in ["unit", "integration"]:
        receipt = read_json(OUTPUT / (kind + "-metadata.json"))
        report = OUTPUT / ("junit-" + kind + ".xml")
        if (
            receipt.get("commit") != revision
            or receipt.get("test_exit_code") != 0
            or receipt.get("report_sha256") != hashlib.sha256(report.read_bytes()).hexdigest()
        ):
            raise ValueError("Test evidence does not match this commit")
    junit_passed(OUTPUT / "junit-unit.xml", allow_skips=True)
    junit_passed(OUTPUT / "junit-integration.xml", allow_skips=False)
    return built


def auth_environment():
    environment = os.environ.copy()
    if not environment.get("DOCKER_HOST"):
        environment["DOCKER_HOST"] = run(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"]
        ).stdout.strip()
    directory = PRIVATE / "docker-auth"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment["DOCKER_CONFIG"] = str(directory)
    return environment


def publish():
    if os.environ.get("CLINIC_IS_PR", "false").lower() == "true":
        raise ValueError("PR builds cannot access publication credentials")
    revision = commit()
    built = verified_gates(revision)
    username = os.environ.get("CLINIC_REGISTRY_USER", TOOLS["registry"].split("/", 1)[1])
    token = os.environ.get("CLINIC_REGISTRY_TOKEN")
    if not token and (ROOT / ".registry-token").is_file():
        token = (ROOT / ".registry-token").read_text(encoding="utf-8-sig").strip()
    if not token:
        raise RuntimeError("Missing GHCR write:packages credential; no push attempted")
    environment = auth_environment()
    run(
        ["docker", "login", "ghcr.io", "--username", username, "--password-stdin"],
        input_text=token,
        env=environment,
        log=OUTPUT / "registry-login.log",
    )
    manifest = {
        "schema_version": 1,
        "commit": revision,
        "created_at_utc": now(),
        "source": TOOLS["repository"],
        "images": {},
    }
    try:
        for name, item in built["images"].items():
            current_id = run(
                ["docker", "image", "inspect", item["tag"], "--format", "{{.Id}}"], env=environment
            ).stdout.strip()
            if current_id != item["image_id"]:
                raise ValueError("Image tag changed after scanning")
            run(
                ["docker", "push", item["tag"]],
                env=environment,
                log=OUTPUT / "push" / (name + ".log"),
            )
            repository = item["tag"].rsplit(":", 1)[0]
            digests = json.loads(
                run(
                    [
                        "docker",
                        "image",
                        "inspect",
                        item["tag"],
                        "--format",
                        "{{json .RepoDigests}}",
                    ],
                    env=environment,
                ).stdout
            )
            matching = [
                digest
                for digest in digests or []
                if re.fullmatch(re.escape(repository) + r"@sha256:[a-f0-9]{64}", digest)
            ]
            if len(matching) != 1:
                raise RuntimeError("Cannot determine a unique pushed digest")
            reference = matching[0]
            verify_pull(
                reference, env=environment, log=OUTPUT / "push" / (name + "-verify-pull.log")
            )
            manifest["images"][name] = {
                **item,
                "reference": reference,
                "digest": reference.split("@", 1)[1],
            }
        write_json(OUTPUT / "release-manifest.json", manifest)
    finally:
        run(
            ["docker", "logout", "ghcr.io"],
            env=environment,
            check=False,
            log=OUTPUT / "registry-logout.log",
        )
        (PRIVATE / "docker-auth/config.json").unlink(missing_ok=True)


def cleanup():
    (PRIVATE / "docker-auth/config.json").unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["publish", "cleanup"])
    {"publish": publish, "cleanup": cleanup}[parser.parse_args().action]()


if __name__ == "__main__":
    main()
