import importlib.util
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ci_bootstrap", ROOT / "scripts/bootstrap-ci.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def test_public_source_never_queries_local_credentials(monkeypatch):
    monkeypatch.delenv("CLINIC_GITHUB_TOKEN", raising=False)

    def refuse(*args, **kwargs):
        raise AssertionError("Public SCM must not read credential helpers")

    monkeypatch.setattr(subprocess, "run", refuse)
    assert bootstrap.github_credential() is None
    root = ET.fromstring(bootstrap.job_xml())
    assert root.find(".//credentialsId") is None


def test_explicit_source_token_remains_supported(monkeypatch):
    monkeypatch.setenv("CLINIC_GITHUB_TOKEN", "unit-test-only-not-a-deployment-token")
    monkeypatch.setenv("CLINIC_GITHUB_USER", "unit-user")
    assert bootstrap.github_credential() == ("unit-user", "unit-test-only-not-a-deployment-token")
    assert ET.fromstring(bootstrap.job_xml(True)).findtext(".//credentialsId") == "clinic-github"


def test_registry_namespace_is_configurable(monkeypatch):
    monkeypatch.setenv("CLINIC_REGISTRY", "ghcr.io/baolong205")
    root = ET.fromstring(bootstrap.job_xml())
    parameters = {
        field.findtext("name"): field.findtext("defaultValue")
        for field in root.findall(".//hudson.model.StringParameterDefinition")
    }
    assert parameters["REGISTRY_NAMESPACE"] == "ghcr.io/baolong205"
