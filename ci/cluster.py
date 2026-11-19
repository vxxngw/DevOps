"""Cluster safety checks shared by operator bootstrap and namespace deployment."""

import json
import os
from urllib.parse import urlparse

from ci.common import run


def context(namespace=None, expected_server=None):
    data = json.loads(run(["kubectl", "config", "view", "--minify", "-o", "json"]).stdout)
    cluster = data["clusters"][0]["cluster"]
    server = cluster["server"].rstrip("/")
    if urlparse(server).scheme != "https" or cluster.get("insecure-skip-tls-verify"):
        raise ValueError("A verified HTTPS Kubernetes context is required")
    expected = expected_server or os.environ.get("CLINIC_EXPECTED_CLUSTER_SERVER")
    if not expected or server != expected.rstrip("/"):
        raise ValueError(
            "Set CLINIC_EXPECTED_CLUSTER_SERVER to the actual Terraform k3s server URL"
        )
    if namespace and data["contexts"][0]["context"].get("namespace") != namespace:
        raise ValueError("Kubeconfig must select the exact target namespace")
    return data
