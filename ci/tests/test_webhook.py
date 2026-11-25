import hashlib
import hmac

import pytest

from ci.webhook.relay import DeliveryStore, parameters, validate_signature


def push():
    return {
        "repository": {"full_name": "vxxngw/DevOps", "id": 1457478642},
        "ref": "refs/heads/main",
        "after": "a" * 40,
        "deleted": False,
    }


def test_signature_covers_exact_bytes():
    secret = b"generated-test-value-not-an-api-key"
    body = b'{"event":"push"}'
    signed = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    assert validate_signature(secret, body, signed)
    assert not validate_signature(secret, body + b" ", signed)
    assert not validate_signature(secret, body, None)


def test_main_push_pins_exact_commit_and_requests_release():
    result = parameters("push", push())
    assert result["SOURCE_REF"] == "a" * 40
    assert result["SOURCE_BRANCH"] == "main"
    assert result["IS_PR"] == "false"
    assert result["PUBLISH_IMAGES"] == "true"
    # Staging deploys automatically; production still waits for the Jenkins input approval.
    assert result["DEPLOY"] == "true"


def test_feature_push_does_not_receive_publication_or_deployment():
    event = push()
    event["ref"] = "refs/heads/codex/milestone-2"
    result = parameters("push", event)
    assert result["PUBLISH_IMAGES"] == "false"
    assert result["DEPLOY"] == "false"


def test_branch_named_like_main_is_not_a_release():
    event = push()
    event["ref"] = "refs/heads/main-hotfix"
    assert parameters("push", event)["DEPLOY"] == "false"


def test_deleted_branch_has_no_build():
    event = push()
    event["deleted"] = True
    assert parameters("push", event) is None


def test_foreign_repository_is_rejected():
    event = push()
    event["repository"]["full_name"] = "someone/else"
    with pytest.raises(ValueError):
        parameters("push", event)


@pytest.mark.parametrize("revision", ["main;command", "../main", "f" * 39, "https://example.test"])
def test_invalid_revision_cannot_reach_checkout(revision):
    event = push()
    event["after"] = revision
    with pytest.raises(ValueError):
        parameters("push", event)


def pr(owner="vxxngw/DevOps"):
    return {
        "repository": {"full_name": "vxxngw/DevOps", "id": 1457478642},
        "action": "synchronize",
        "pull_request": {
            "draft": False,
            "base": {"ref": "main"},
            "head": {
                "ref": "feature",
                "sha": "b" * 40,
                "repo": {
                    "full_name": owner,
                    "id": 1457478642 if owner == "vxxngw/DevOps" else 1,
                },
            },
        },
    }


def test_same_repo_pr_never_publishes_or_deploys():
    result = parameters("pull_request", pr())
    assert result["IS_PR"] == "true"
    assert result["PUBLISH_IMAGES"] == "false"
    assert result["DEPLOY"] == "false"


def test_fork_pr_does_not_run_on_trusted_agent():
    with pytest.raises(ValueError):
        parameters("pull_request", pr("outsider/fork"))


def test_delivery_deduplication_survives_restart(tmp_path):
    database = tmp_path / "deliveries.db"
    store = DeliveryStore(database)
    assert store.claim("payload-sha")
    store.finish("payload-sha", True)
    assert not DeliveryStore(database).claim("payload-sha")


def test_failed_queue_can_be_redelivered(tmp_path):
    store = DeliveryStore(tmp_path / "deliveries.db")
    assert store.claim("payload-sha")
    store.finish("payload-sha", False)
    assert store.claim("payload-sha")


@pytest.mark.parametrize("identifier", [None, 1, "1457478642"])
def test_matching_name_without_pinned_numeric_id_is_rejected(identifier):
    event = push()
    event["repository"]["id"] = identifier
    with pytest.raises(ValueError):
        parameters("push", event)


def test_old_name_is_not_accepted_just_because_repository_id_matches():
    event = push()
    event["repository"]["full_name"] = "vuongvo2207-gmail-com/DevOps"  # pre-transfer organization
    with pytest.raises(ValueError):
        parameters("push", event)


def test_pr_head_requires_matching_repository_id():
    event = pr()
    event["pull_request"]["head"]["repo"]["id"] = 1
    with pytest.raises(ValueError):
        parameters("pull_request", event)


def test_release_passes_this_hosts_cluster_url(monkeypatch):
    monkeypatch.setenv("CLINIC_CLUSTER_SERVER_URL", "https://192.168.1.102:6443")
    assert parameters("push", push())["CLUSTER_SERVER_URL"] == "https://192.168.1.102:6443"
    event = push()
    event["ref"] = "refs/heads/feature"
    assert "CLUSTER_SERVER_URL" not in parameters("push", event)


def test_release_rejects_a_malformed_cluster_url(monkeypatch):
    monkeypatch.setenv("CLINIC_CLUSTER_SERVER_URL", "http://192.168.1.102:6443/x")
    with pytest.raises(ValueError):
        parameters("push", push())
