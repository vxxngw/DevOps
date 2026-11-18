"""Offline schema/policy checks. Passing does not establish deployment or scaling."""

import copy
import hashlib
import json
import os
import platform
import shutil
import urllib.request

import jsonschema
import yaml

from ci.common import OUTPUT, ROOT, commit, now, run, write_json


def load_documents(content):
    return [document for document in yaml.safe_load_all(content) if document]


def normalize_schema(value):
    if isinstance(value, dict):
        if value.get("format") == "int-or-string" or value.get("x-kubernetes-int-or-string"):
            value.pop("type", None)
            value["anyOf"] = [{"type": "integer"}, {"type": "string"}]
        for child in value.values():
            normalize_schema(child)
    elif isinstance(value, list):
        for child in value:
            normalize_schema(child)


def schema_index():
    versions = json.loads((ROOT / "infra/versions.json").read_text(encoding="utf-8"))
    paths = [(ROOT / ".infra-local/vendor/kubernetes-swagger.json", versions["kubernetes_schema"])]
    paths += [
        (ROOT / ".infra-local/vendor" / (name + ".yaml"), item)
        for name, item in versions["addons"].items()
    ]
    for path, metadata in paths:
        if not path.exists():
            with urllib.request.urlopen(metadata["url"], timeout=120) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
                raise ValueError("Downloaded schema checksum mismatch")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("Schema/vendor content changed: " + path.name)
    definitions = json.loads(paths[0][0].read_text(encoding="utf-8"))["definitions"]
    normalize_schema(definitions)
    schemas = {}
    for name, definition in definitions.items():
        for gvk in definition.get("x-kubernetes-group-version-kind", []):
            version = (gvk["group"] + "/" if gvk["group"] else "") + gvk["version"]
            schemas[(version, gvk["kind"])] = {
                "$ref": "#/definitions/" + name,
                "definitions": definitions,
            }
    for path, _ in paths[1:]:
        for resource in load_documents(path.read_text(encoding="utf-8")):
            if resource.get("kind") != "CustomResourceDefinition":
                continue
            for version in resource["spec"]["versions"]:
                schema = copy.deepcopy(version["schema"]["openAPIV3Schema"])
                normalize_schema(schema)
                schemas[
                    (
                        resource["spec"]["group"] + "/" + version["name"],
                        resource["spec"]["names"]["kind"],
                    )
                ] = schema
    return schemas


def validate_schema(resources, schemas):
    for resource in resources:
        key = resource["apiVersion"], resource["kind"]
        if key not in schemas:
            raise ValueError("No verified schema for " + str(key))
        errors = list(jsonschema.Draft4Validator(schemas[key]).iter_errors(resource))
        if errors:
            error = errors[0]
            raise ValueError(
                f"{resource['kind']}/{resource['metadata']['name']} at {list(error.path)}: {error.message}"
            )


def pod_spec(resource):
    if resource["kind"] in {"Deployment", "StatefulSet", "Job"}:
        return resource["spec"]["template"]["spec"]
    return None


def validate_policy(resources, namespace):
    index = {(item["kind"], item["metadata"]["name"]): item for item in resources}
    for resource in resources:
        if resource["metadata"].get("namespace") != namespace:
            raise ValueError("Every app object must stay in " + namespace)
        if resource["kind"] in {"Secret", "Role", "RoleBinding", "ClusterRole", "Namespace"}:
            raise ValueError("Secrets/RBAC/namespaces belong to separate operator bootstrap")
        spec = pod_spec(resource)
        if spec:
            if (
                spec.get("automountServiceAccountToken") is not False
                or spec.get("securityContext", {}).get("runAsNonRoot") is not True
            ):
                raise ValueError("App pods must be non-root without Kubernetes API tokens")
            for container in spec["containers"] + spec.get("initContainers", []):
                security = container.get("securityContext", {})
                if security.get(
                    "allowPrivilegeEscalation"
                ) is not False or "ALL" not in security.get("capabilities", {}).get("drop", []):
                    raise ValueError("Container privileges are too broad")
                if not container.get("resources", {}).get("requests") or not container.get(
                    "resources", {}
                ).get("limits"):
                    raise ValueError("Requests/limits are mandatory")
                if resource["kind"] != "Job" and not all(
                    name in container
                    for name in ["startupProbe", "livenessProbe", "readinessProbe"]
                ):
                    raise ValueError("All long-running workloads need probes")
    api = index[("HorizontalPodAutoscaler", "api")]["spec"]
    if api["minReplicas"] < 2 or api["scaleTargetRef"]["name"] != "api":
        raise ValueError("API HPA must retain at least two replicas")
    worker = index[("ScaledObject", "worker")]["spec"]
    if any(
        item["kind"] == "HorizontalPodAutoscaler"
        and item["spec"]["scaleTargetRef"]["name"] == "worker"
        for item in resources
    ):
        raise ValueError("KEDA must be the only worker scaling controller")
    trigger = worker["triggers"][0]
    metadata = trigger["metadata"]
    if (
        metadata.get("mode") != "QueueLength"
        or metadata.get("protocol") != "http"
        or metadata.get("excludeUnacknowledged") != "false"
    ):
        raise ValueError("Worker must count ready and unacked via RabbitMQ HTTP scaler")
    if (
        metadata["queueName"] != f"clinic.{namespace}.notifications"
        or metadata["vhostName"] != "clinic-" + namespace
    ):
        raise ValueError("Queue/vhost do not match the actual environment")
    if "@" in metadata["host"] or not trigger.get("authenticationRef"):
        raise ValueError("Scaler credentials must be Secret references")
    for name in ["postgres", "rabbitmq"]:
        if not index[("StatefulSet", name)]["spec"].get("volumeClaimTemplates"):
            raise ValueError("Database/broker must retain persistent volumes")
    for name in ["frontend", "api"]:
        deployment = index[("Deployment", name)]["spec"]
        if (
            deployment.get("replicas", 1) < 2
            or deployment["strategy"]["rollingUpdate"]["maxUnavailable"] != 0
        ):
            raise ValueError("API/frontend continuity profile is missing")
    certificate = index[("Certificate", "clinic-tls")]["spec"]
    ingress = index[("Ingress", "clinic")]["spec"]
    if ingress["tls"][0]["hosts"] != certificate["dnsNames"]:
        raise ValueError("Ingress hostname must match the managed certificate")


def main():
    (OUTPUT / "infra/metadata.json").unlink(missing_ok=True)
    versions = json.loads((ROOT / "infra/versions.json").read_text(encoding="utf-8"))
    if os.name != "nt":
        run(
            ["bash", "-n", *sorted((ROOT / "scripts").glob("*.sh"))],
            log=OUTPUT / "infra/bash-syntax.log",
        )
    binary = (
        ROOT
        / ".infra-local/bin"
        / ("windows/terraform.exe" if os.name == "nt" else "linux/terraform")
    )
    terraform = str(binary) if binary.is_file() else shutil.which("terraform")
    if not terraform:
        raise RuntimeError("Install pinned infra tools first; verification is blocked")
    actual = json.loads(run([terraform, "version", "-json"]).stdout)["terraform_version"]
    if actual != versions["terraform"]:
        raise RuntimeError("Unexpected Terraform version")
    prefix = [terraform, "-chdir=" + str(ROOT / "infra/terraform")]
    environment = os.environ.copy()
    environment["TF_DATA_DIR"] = str(
        ROOT / ".infra-local" / ("terraform-" + platform.system().lower())
    )
    run(prefix + ["fmt", "-check", "-recursive"], log=OUTPUT / "infra/terraform-fmt.log")
    run(
        prefix + ["init", "-backend=false", "-input=false", "-lockfile=readonly"],
        env=environment,
        log=OUTPUT / "infra/terraform-init.log",
    )
    result = run(
        prefix + ["validate", "-json"],
        env=environment,
        log=OUTPUT / "infra/terraform-validate.json",
    )
    if not json.loads(result.stdout)["valid"]:
        raise RuntimeError("Terraform validation failed")
    schemas = schema_index()
    counts = {}
    for namespace in ["staging", "production"]:
        content = run(["kubectl", "kustomize", ROOT / "deploy/k8s/overlays" / namespace]).stdout
        resources = load_documents(content)
        validate_schema(resources, schemas)
        validate_policy(resources, namespace)
        write_json(OUTPUT / "infra" / (namespace + ".json"), resources)
        counts[namespace] = len(resources)
    for filename in ["namespaces-rbac.yaml", "local-ca.yaml"]:
        validate_schema(
            load_documents((ROOT / "deploy/k8s/bootstrap" / filename).read_text()), schemas
        )
    write_json(
        OUTPUT / "infra/metadata.json",
        {
            "at_utc": now(),
            "head_commit": commit(),
            "files": [
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in sorted(
                    set((ROOT / "deploy/k8s").rglob("*.yaml"))
                    | set((ROOT / "infra/terraform").rglob("*.tf"))
                    | {ROOT / "infra/versions.json", ROOT / "infra/lab-budget.json"}
                )
                if ".terraform" not in path.parts
            ],
            "scope": "Terraform validate and Kubernetes schema/policy/render only; no VM, host convergence, cluster, TLS trust or scaling claim",
            "counts": counts,
            "terraform": actual,
        },
    )
    print("Infrastructure static checks passed; runtime remains separate")


if __name__ == "__main__":
    main()
