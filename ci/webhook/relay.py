import hashlib
import hmac
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPOSITORY_CONFIG = json.loads(
    Path(__file__).with_name("repository.json").read_text(encoding="utf-8")
)
REPOSITORY = REPOSITORY_CONFIG["full_name"]
REPOSITORY_ID = REPOSITORY_CONFIG["id"]
MAX_BODY = 1024 * 1024


def validate_signature(secret, body, signature):
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def parameters(event, payload):
    repository = payload.get("repository", {})
    if repository.get("full_name") != REPOSITORY or repository.get("id") != REPOSITORY_ID:
        raise ValueError("Unexpected repository")
    if event == "ping":
        return None
    if event == "push":
        branch = payload.get("ref", "")
        if payload.get("deleted") or not branch.startswith("refs/heads/"):
            return None
        branch = branch.removeprefix("refs/heads/")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,160}", branch):
            raise ValueError("Invalid branch")
        revision = payload.get("after", "")
        is_pr = False
    elif event == "pull_request":
        if payload.get("action") not in {"opened", "reopened", "synchronize", "ready_for_review"}:
            return None
        pr = payload["pull_request"]
        if pr.get("draft") or pr.get("base", {}).get("ref") != "main":
            return None
        head_repo = pr.get("head", {}).get("repo", {})
        if head_repo.get("full_name") != REPOSITORY or head_repo.get("id") != REPOSITORY_ID:
            raise ValueError("Fork PRs are not allowed on the trusted build agent")
        branch = pr["head"]["ref"]
        revision = pr["head"]["sha"]
        is_pr = True
    else:
        return None
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid source revision")
    # Only a push to main is a release candidate: it publishes the scanned SHA images,
    # deploys staging and then waits at the Jenkins manual approval before production.
    release = branch == "main" and not is_pr
    return {
        "SOURCE_REF": revision,
        "SOURCE_BRANCH": branch,
        "IS_PR": str(is_pr).lower(),
        "PUBLISH_IMAGES": str(release).lower(),
        "DEPLOY": str(release).lower(),
        "SECURITY_DEMO": "none",
    }


class DeliveryStore:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS deliveries (payload_key TEXT PRIMARY KEY, state TEXT NOT NULL)"
            )

    def claim(self, key):
        with sqlite3.connect(self.path) as database:
            result = database.execute(
                "INSERT OR IGNORE INTO deliveries VALUES (?, 'PENDING')", (key,)
            )
            return result.rowcount == 1

    def finish(self, key, success):
        with sqlite3.connect(self.path) as database:
            if success:
                database.execute("UPDATE deliveries SET state='QUEUED' WHERE payload_key=?", (key,))
            else:
                database.execute("DELETE FROM deliveries WHERE payload_key=?", (key,))


def trigger(params):
    settings = json.loads(Path(os.environ["CLINIC_WEBHOOK_CONFIG"]).read_text(encoding="utf-8"))
    import base64

    authorization = base64.b64encode(
        (settings["username"] + ":" + settings["api_token"]).encode()
    ).decode()
    url = (
        settings["jenkins_url"].rstrip("/") + "/job/an-uyen/job/clinic-pipeline/buildWithParameters"
    )
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(params).encode(),
        headers={"Authorization": "Basic " + authorization},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status not in {200, 201, 202}:
            raise RuntimeError("Jenkins did not accept the webhook build")


class Handler(BaseHTTPRequestHandler):
    server_version = "ClinicWebhook/1"

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, message, *args):
        # Do not log webhook bodies, HMACs, URLs with inputs, tokens or PR text.
        return

    def do_GET(self):
        self.reply(
            200 if self.path == "/health" else 404,
            {"service": "clinic-webhook", "ok": self.path == "/health"},
        )

    def do_POST(self):
        if self.path != "/github":
            self.reply(404, {"error": "Unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 1 or length > MAX_BODY:
            self.reply(413, {"error": "Invalid payload size"})
            return
        body = self.rfile.read(length)
        secret = Path(os.environ["CLINIC_WEBHOOK_SECRET_FILE"]).read_bytes().strip()
        if not validate_signature(secret, body, self.headers.get("X-Hub-Signature-256")):
            self.reply(401, {"error": "Invalid signature"})
            return
        event = self.headers.get("X-GitHub-Event", "")
        try:
            params = parameters(event, json.loads(body))
        except (ValueError, KeyError, TypeError):
            self.reply(400, {"error": "Invalid or untrusted event"})
            return
        if params is None:
            self.reply(200, {"status": "No build required"})
            return
        key = hashlib.sha256(event.encode() + b"\0" + body).hexdigest()
        store = self.server.delivery_store
        if not store.claim(key):
            self.reply(200, {"status": "Already accepted"})
            return
        try:
            trigger(params)
        except Exception as error:
            store.finish(key, False)
            print(
                json.dumps(
                    {
                        "service": "clinic-webhook",
                        "event": "queue_failed",
                        "error_type": type(error).__name__,
                    }
                ),
                flush=True,
            )
            self.reply(502, {"error": "Build queue unavailable; GitHub may redeliver"})
            return
        store.finish(key, True)
        print(
            json.dumps(
                {
                    "service": "clinic-webhook",
                    "event": "queued",
                    "commit": params["SOURCE_REF"],
                    "is_pr": params["IS_PR"],
                }
            ),
            flush=True,
        )
        self.reply(202, {"status": "Queued", "commit": params["SOURCE_REF"]})


if __name__ == "__main__":
    data_dir = Path(os.environ.get("CLINIC_WEBHOOK_DATA", "/data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", 8085), Handler)
    server.delivery_store = DeliveryStore(data_dir / "deliveries.db")
    server.serve_forever()
