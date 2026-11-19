"""Promote scanned digests; fails closed until real Mốc3 overlays/credentials exist."""

import argparse
import copy
import hashlib
import json
import os
import re
import time

from ci.cluster import context
from ci.common import OUTPUT, ROOT, commit, read_json, run, write_json


def json_objects(content):
    decoder = json.JSONDecoder()
    remaining = content.lstrip()
    while remaining:
        item, offset = decoder.raw_decode(remaining)
        yield from item["items"] if item.get("kind") == "List" else [item]
        remaining = remaining[offset:].lstrip()


def render_release(resources, manifest, namespace):
    references = {
        item["tag"].rsplit(":", 1)[0]: item["reference"] for item in manifest["images"].values()
    }
    count = 0

    def walk(value):
        nonlocal count
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"containers", "initContainers"}:
                    for container in child:
                        source = container["image"]
                        repository = source.split("@", 1)[0].rsplit(":", 1)[0]
                        if repository not in references:
                            raise ValueError(
                                "Workload contains an image not covered by the scanned release"
                            )
                        container["image"] = references[repository]
                        count += 1
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for resource in resources:
        if resource.get("kind") not in {
            "Service",
            "ServiceAccount",
            "ConfigMap",
            "Deployment",
            "StatefulSet",
            "Job",
            "HorizontalPodAutoscaler",
            "ScaledObject",
            "TriggerAuthentication",
            "Certificate",
            "Ingress",
            "NetworkPolicy",
            "PodDisruptionBudget",
        }:
            raise ValueError("Cluster bootstrap does not belong to the application deployer")
        if resource.get("metadata", {}).get("namespace") != namespace:
            raise ValueError("Overlay must declare the correct deployment namespace")
        walk(resource.get("spec", {}))
    if not count:
        raise ValueError("Overlay has no release workload")
    return {"apiVersion": "v1", "kind": "List", "items": resources}


def phases(release, revision):
    resources = copy.deepcopy(release["items"])
    checksum = hashlib.sha256(json.dumps(resources, sort_keys=True).encode()).hexdigest()
    foundation, migration, workloads = [], [], []
    for resource in resources:
        kind = resource["kind"]
        if kind == "Job":
            command = resource["spec"]["template"]["spec"]["containers"][0]["command"]
            if command != ["alembic", "upgrade", "head"] or migration:
                raise ValueError("Exactly one controlled Alembic upgrade Job is required")
            resource["metadata"]["name"] = "clinic-migrate-" + revision[:12] + "-" + checksum[:8]
            migration.append(resource)
        elif (
            kind in {"Service", "ServiceAccount", "ConfigMap", "StatefulSet"}
            or resource["metadata"].get("labels", {}).get("clinic.anuyen.io/phase") == "foundation"
        ):
            foundation.append(resource)
        else:
            workloads.append(resource)
    if len(migration) != 1:
        raise ValueError("A migration Job must complete before application rollout")
    return {"foundation": foundation, "migration": migration, "workloads": workloads}, checksum


def apply_objects(namespace, objects, phase):
    path = OUTPUT / (namespace + "-" + phase + ".json")
    write_json(path, {"apiVersion": "v1", "kind": "List", "items": objects})
    for dry in [True, False]:
        command = ["kubectl", "-n", namespace, "apply", "-f", path]
        if dry:
            command.append("--dry-run=server")
        run(
            command,
            log=OUTPUT / (namespace + "-" + phase + ("-dry-run.log" if dry else "-apply.log")),
        )


def wait_workloads(namespace, objects):
    for resource in objects:
        if resource["kind"] in {"Deployment", "StatefulSet"}:
            target = resource["kind"].lower() + "/" + resource["metadata"]["name"]
            run(
                ["kubectl", "-n", namespace, "rollout", "status", target, "--timeout=180s"],
                log=OUTPUT / (namespace + "-" + resource["metadata"]["name"] + "-rollout.log"),
            )


def restore_snapshot(namespace, snapshot):
    resources = snapshot["resources"]
    if not resources or any(item["metadata"].get("namespace") != namespace for item in resources):
        raise ValueError("Rollback snapshot belongs to another namespace")
    resources = [item for item in resources if item["kind"] != "Job"]
    # Schema/data/rotated secrets are deliberately not downgraded.
    apply_objects(namespace, resources, "rollback")
    wait_workloads(namespace, resources)
    run(
        [os.sys.executable, "-m", "ci.smoke", namespace],
        log=OUTPUT / (namespace + "-rollback-smoke.log"),
    )


def deploy(namespace):
    if os.environ.get("CLINIC_IS_PR", "false").lower() == "true":
        raise ValueError("PR builds cannot deploy")
    context(namespace)
    overlay = ROOT / "deploy/k8s/overlays" / namespace
    if not overlay.is_dir():
        raise RuntimeError(
            "Mốc3 Kubernetes overlays do not exist; deployment is blocked, not passed"
        )
    manifest = read_json(OUTPUT / "release-manifest.json")
    if manifest["commit"] != commit():
        raise ValueError("Release manifest does not match the verified checkout")
    for item in manifest["images"].values():
        if not re.fullmatch(r"ghcr\.io/[^@]+@sha256:[a-f0-9]{64}", item["reference"]):
            raise ValueError("Immutable registry digests are required")
        if item["reference"].split("@", 1)[0] != item["tag"].rsplit(":", 1)[0]:
            raise ValueError("Release digest repository does not match its scanned tag")
    from ci.infrastructure import load_documents, schema_index, validate_policy, validate_schema

    resources = load_documents(run(["kubectl", "kustomize", overlay]).stdout)
    validate_schema(resources, schema_index())
    validate_policy(resources, namespace)
    release = render_release(resources, manifest, namespace)
    release_file = OUTPUT / ("rendered-" + namespace + ".json")
    write_json(release_file, release)
    plan, config_hash = phases(release, manifest["commit"])
    for name in ["app-secrets", "postgres-auth", "rabbitmq-auth", "registry-pull"]:
        run(["kubectl", "-n", namespace, "get", "secret", name, "-o", "name"])
    previous = run(
        [
            "kubectl",
            "-n",
            namespace,
            "get",
            "configmap",
            "clinic-release-state",
            "--ignore-not-found",
            "-o",
            "json",
        ]
    ).stdout.strip()
    previous = json.loads(json.loads(previous)["data"]["release.json"]) if previous else None
    if previous:
        write_json(OUTPUT / (namespace + "-previous.json"), previous)
    started = time.monotonic()
    try:
        apply_objects(namespace, plan["foundation"], "foundation")
        wait_workloads(namespace, plan["foundation"])
        apply_objects(namespace, plan["migration"], "migration")
        run(
            [
                "kubectl",
                "-n",
                namespace,
                "wait",
                "--for=condition=Complete",
                "job/" + plan["migration"][0]["metadata"]["name"],
                "--timeout=180s",
            ],
            log=OUTPUT / (namespace + "-migration-wait.log"),
        )
        apply_objects(namespace, plan["workloads"], "workloads")
        wait_workloads(namespace, plan["workloads"])
        run(
            [
                "kubectl",
                "-n",
                namespace,
                "wait",
                "--for=condition=Ready",
                "certificate/clinic-tls",
                "--timeout=180s",
            ],
            log=OUTPUT / (namespace + "-certificate.log"),
        )
        run(
            [os.sys.executable, "-m", "ci.smoke", namespace],
            log=OUTPUT / (namespace + "-smoke.log"),
        )
    except Exception:
        if previous:
            rollback_started = time.monotonic()
            restore_snapshot(namespace, previous)
            write_json(
                OUTPUT / (namespace + "-rollback-result.json"),
                {
                    "namespace": namespace,
                    "seconds": time.monotonic() - rollback_started,
                    "scope": "Previous images/config restored and smoke passed; no database or secret rollback",
                },
            )
        raise
    snapshot = {
        "commit": manifest["commit"],
        "config_sha256": config_hash,
        "manifest": manifest,
        "resources": plan["foundation"] + plan["migration"] + plan["workloads"],
    }
    write_json(OUTPUT / (namespace + "-release.json"), snapshot)
    receipt = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"namespace": namespace, "name": "clinic-release-state"},
        "data": {"release.json": json.dumps(snapshot)},
    }
    run(
        ["kubectl", "-n", namespace, "apply", "-f", "-"],
        input_text=json.dumps(receipt),
        log=OUTPUT / (namespace + "-record-release.log"),
    )
    write_json(
        OUTPUT / (namespace + "-deploy-result.json"),
        {
            "commit": manifest["commit"],
            "namespace": namespace,
            "seconds": time.monotonic() - started,
            "smoke": "passed",
            "config_sha256": config_hash,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("namespace", choices=["staging", "production"])
    deploy(parser.parse_args().namespace)
