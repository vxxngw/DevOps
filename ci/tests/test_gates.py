import copy
import hashlib
import json
import xml.etree.ElementTree as ET

import pytest

from ci import release
from ci.deploy import json_objects, render_release
from ci.release import junit_passed
from ci.security import critical_findings


@pytest.mark.parametrize("report", [{}, {"Results": []}, {"Results": None}, []])
def test_missing_scanner_results_never_count_as_clean(report):
    with pytest.raises(ValueError):
        critical_findings(report)


def test_unfixed_critical_is_not_ignored():
    finding = {"Severity": "CRITICAL", "VulnerabilityID": "CVE-DEMO", "FixedVersion": ""}
    assert critical_findings({"Results": [{"Vulnerabilities": [finding]}]}) == [finding]


def test_valid_clean_report():
    assert (
        critical_findings({"Results": [{"Target": "actual-scan", "Vulnerabilities": None}]}) == []
    )


def test_junit_failure_or_empty_does_not_allow_publication(tmp_path):
    report = tmp_path / "junit.xml"
    for content in [
        "<testsuites/>",
        '<testsuites><testcase name="x"><failure/></testcase></testsuites>',
    ]:
        report.write_text(content)
        with pytest.raises(ValueError):
            junit_passed(report, allow_skips=True)


def test_integration_skip_does_not_allow_publication(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite><testcase name="x"><skipped/></testcase></testsuite></testsuites>'
    )
    with pytest.raises(ValueError):
        junit_passed(report, allow_skips=False)
    assert junit_passed(report, allow_skips=True) == 1


def test_passing_junit(tmp_path):
    report = tmp_path / "junit.xml"
    tree = ET.Element("testsuites")
    ET.SubElement(ET.SubElement(tree, "testsuite"), "testcase", name="actual-test")
    ET.ElementTree(tree).write(report)
    assert junit_passed(report, allow_skips=False) == 1


def fixture_release():
    reference = "ghcr.io/vxxngw/devops-app@sha256:" + "a" * 64
    manifest = {
        "images": {
            "app": {
                "tag": "ghcr.io/vxxngw/devops-app:commit",
                "reference": reference,
            }
        }
    }
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"namespace": "staging", "name": "appointment-api"},
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "api",
                            "image": "ghcr.io/vxxngw/devops-app:previous",
                        }
                    ]
                }
            }
        },
    }
    return manifest, deployment, reference


def test_promotion_reuses_scanned_digest():
    manifest, deployment, reference = fixture_release()
    rendered = render_release([deployment], manifest, "staging")
    assert rendered["items"][0]["spec"]["template"]["spec"]["containers"][0]["image"] == reference


def test_promotion_rejects_wrong_namespace_or_unscanned_image():
    manifest, deployment, _ = fixture_release()
    with pytest.raises(ValueError):
        render_release([copy.deepcopy(deployment)], manifest, "production")
    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = "unscanned/image:tag"
    with pytest.raises(ValueError):
        render_release([deployment], manifest, "staging")


def test_app_deployer_cannot_create_cluster_admin():
    manifest, _, _ = fixture_release()
    with pytest.raises(ValueError):
        render_release(
            [{"kind": "ClusterRoleBinding", "metadata": {"namespace": "staging"}}],
            manifest,
            "staging",
        )


def test_kubectl_json_stream_or_list_parses_without_yaml_rewriting():
    assert list(
        json_objects('{"kind":"List","items":[{"kind":"Service"}]}\n{"kind":"ConfigMap"}')
    ) == [{"kind": "Service"}, {"kind": "ConfigMap"}]


def prepared_gates(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "OUTPUT", tmp_path)
    monkeypatch.setattr(release, "IMAGES", ("app",))
    (tmp_path / "security").mkdir()

    def report(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    secret_hash = report("security/gitleaks.json", "[]")
    dependency_hash = report(
        "security/trivy-dependencies.json", '{"Results":[{"Target":"dependencies"}]}'
    )
    image_hash = report("security/trivy-app.json", '{"Results":[{"Target":"app"}]}')
    revision = "a" * 40
    image = {"image_id": "sha256:actual-built-image"}
    metadata = {
        "built-images": {"commit": revision, "images": {"app": image}},
        "security-summary": {
            "commit": revision,
            "images": {
                "app": {
                    **image,
                    "critical": 0,
                    "report_sha256": image_hash,
                }
            },
            "dependency_report_sha256": dependency_hash,
        },
        "secret-gate": {"commit": revision, "findings": 0, "report_sha256": secret_hash},
    }
    for kind in ["unit", "integration"]:
        checksum = report(
            "junit-" + kind + ".xml", '<testsuites><testcase name="real-result"/></testsuites>'
        )
        metadata[kind + "-metadata"] = {
            "commit": revision,
            "test_exit_code": 0,
            "report_sha256": checksum,
        }
    for name, value in metadata.items():
        (tmp_path / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    return revision


@pytest.mark.parametrize(
    "target",
    [
        "security/gitleaks.json",
        "security/trivy-dependencies.json",
        "junit-unit.xml",
        "junit-integration.xml",
    ],
)
def test_changed_gate_report_cannot_authorize_registry_push(tmp_path, monkeypatch, target):
    revision = prepared_gates(tmp_path, monkeypatch)
    release.verified_gates(revision)
    with (tmp_path / target).open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError):
        release.verified_gates(revision)


def test_test_receipt_from_another_commit_cannot_authorize_registry_push(tmp_path, monkeypatch):
    revision = prepared_gates(tmp_path, monkeypatch)
    path = tmp_path / "integration-metadata.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["commit"] = "b" * 40
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError):
        release.verified_gates(revision)
