import copy
import importlib.util
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from clinic import manage_user
from clinic.models import Base, User
from clinic.security import passwords
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ci import cluster
from ci.common import ROOT
from ci.deploy import phases, render_release
from ci.infrastructure import load_documents, validate_policy
from ci.smoke import mailpit_job


@pytest.fixture(scope="module")
def rendered():
    if not shutil.which("kubectl"):
        pytest.skip(
            "Unit policy checks need kubectl; mandatory infrastructure stage fails if missing"
        )
    content = subprocess.check_output(
        ["kubectl", "kustomize", str(ROOT / "deploy/k8s/overlays/staging")], text=True
    )
    return load_documents(content)


def test_missing_migration_blocks_deployment(rendered):
    without_job = [resource for resource in rendered if resource["kind"] != "Job"]
    with pytest.raises(ValueError, match="migration"):
        phases({"items": without_job}, "a" * 40)


def test_migration_is_separate_from_foundation_and_application_rollout(rendered):
    plan, _ = phases({"items": rendered}, "a" * 40)
    assert len(plan["migration"]) == 1
    assert plan["migration"][0]["metadata"]["name"].startswith("clinic-migrate-" + "a" * 12)
    assert {
        item["metadata"]["name"] for item in plan["foundation"] if item["kind"] == "StatefulSet"
    } == {"postgres", "rabbitmq"}
    assert not any(
        item["kind"] == "Deployment" and item["metadata"]["name"] in {"api", "publisher", "worker"}
        for item in plan["foundation"]
    )
    assert any(
        item["kind"] == "Deployment" and item["metadata"]["name"] == "api"
        for item in plan["workloads"]
    )


def test_arbitrary_job_cannot_be_used_as_a_migration(rendered):
    resources = copy.deepcopy(rendered)
    job = next(item for item in resources if item["kind"] == "Job")
    job["spec"]["template"]["spec"]["containers"][0]["command"] = ["alembic", "downgrade", "base"]
    with pytest.raises(ValueError, match="controlled"):
        phases({"items": resources}, "a" * 40)


def test_second_worker_scaling_controller_is_rejected(rendered):
    resources = copy.deepcopy(rendered)
    resources.append(
        {
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": "unsafe-worker", "namespace": "staging"},
            "spec": {"scaleTargetRef": {"name": "worker"}},
        }
    )
    with pytest.raises(ValueError, match="only worker"):
        validate_policy(resources, "staging")


def test_wrong_environment_queue_is_rejected(rendered):
    resources = copy.deepcopy(rendered)
    next(item for item in resources if item["kind"] == "ScaledObject")["spec"]["triggers"][0][
        "metadata"
    ]["queueName"] = "clinic.production.notifications"
    with pytest.raises(ValueError, match="environment"):
        validate_policy(resources, "staging")


def test_app_cannot_receive_api_token(rendered):
    resources = copy.deepcopy(rendered)
    next(item for item in resources if item["kind"] == "Deployment")["spec"]["template"]["spec"][
        "automountServiceAccountToken"
    ] = True
    with pytest.raises(ValueError, match="tokens"):
        validate_policy(resources, "staging")


def test_registry_digest_substitution_covers_every_workload(rendered):
    names = ["app", "frontend", "postgres", "rabbitmq", "mailpit"]
    manifest = {
        "images": {
            name: {
                "tag": "ghcr.io/vuongvo2207-gmail-com/devops-" + name + ":candidate",
                "reference": "ghcr.io/vuongvo2207-gmail-com/devops-" + name + "@sha256:" + "a" * 64,
            }
            for name in names
        }
    }
    result = render_release(copy.deepcopy(rendered), manifest, "staging")
    for item in result["items"]:
        if item["kind"] in {"Deployment", "StatefulSet", "Job"}:
            assert all(
                "@sha256:" in container["image"]
                for container in item["spec"]["template"]["spec"]["containers"]
            )


def test_context_must_match_cluster_and_namespace(monkeypatch):
    metadata = {
        "clusters": [{"cluster": {"server": "https://cluster.test:6443"}}],
        "contexts": [{"context": {"namespace": "staging"}}],
    }
    monkeypatch.setattr(
        cluster, "run", lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(metadata))
    )
    cluster.context("staging", "https://cluster.test:6443")
    with pytest.raises(ValueError, match="namespace"):
        cluster.context("production", "https://cluster.test:6443")
    with pytest.raises(ValueError, match="actual Terraform"):
        cluster.context("staging", "https://unrelated.test:6443")
    metadata["clusters"][0]["cluster"]["insecure-skip-tls-verify"] = True
    with pytest.raises(ValueError, match="verified HTTPS"):
        cluster.context("staging", "https://cluster.test:6443")


def test_mail_check_is_read_only_and_has_no_cluster_token():
    image = "ghcr.io/vuongvo2207-gmail-com/devops-app@sha256:" + "a" * 64
    job = mailpit_job("staging", "a" * 8 + "-0000-0000-0000-000000000000", image)
    spec = job["spec"]["template"]["spec"]
    assert spec["automountServiceAccountToken"] is False
    assert spec["containers"][0]["image"] == image
    assert "/api/v1/messages" in spec["containers"][0]["command"][-1]
    assert not spec["containers"][0].get("envFrom")


def test_namespace_credentials_are_distinct_and_consistent():
    spec = importlib.util.spec_from_file_location(
        "cluster_secrets", ROOT / "scripts/infra/prepare-cluster-secrets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = {
        item["metadata"]["name"]: item["stringData"]
        for item in module.manifest("staging", "synthetic-unit-input-never-a-real-token")["items"]
    }
    second = {
        item["metadata"]["name"]: item["stringData"]
        for item in module.manifest("production", "synthetic-unit-input-never-a-real-token")[
            "items"
        ]
    }
    assert first["app-secrets"]["JWT_SECRET"] != second["app-secrets"]["JWT_SECRET"]
    assert first["postgres-auth"]["POSTGRES_PASSWORD"] in first["app-secrets"]["DATABASE_URL"]
    assert first["rabbitmq-auth"]["RABBITMQ_DEFAULT_PASS"] in first["app-secrets"]["RABBITMQ_URL"]
    assert (
        first["rabbitmq-auth"]["RABBITMQ_DEFAULT_VHOST"]
        != second["rabbitmq-auth"]["RABBITMQ_DEFAULT_VHOST"]
    )


def test_explicit_account_creation_never_resets_or_elevates_existing_user(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(manage_user, "session", lambda: Session(engine))
    assert manage_user.create_user("smoke@example.test", "patient", "original-unit-password")
    assert not manage_user.create_user("smoke@example.test", "patient", "different-unit-password")
    with pytest.raises(ValueError, match="role differs"):
        manage_user.create_user("smoke@example.test", "admin", "different-unit-password")
    with Session(engine) as database:
        user = database.scalar(select(User))
        assert user.role == "patient"
        assert passwords.verify("original-unit-password", user.password_hash)
        assert not passwords.verify("different-unit-password", user.password_hash)


def test_account_tool_rejects_real_email_address():
    with pytest.raises(ValueError, match="synthetic"):
        manage_user.create_user("someone@example.com", "patient", "only-unit-test-password")
