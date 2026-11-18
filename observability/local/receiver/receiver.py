"""Minimal Alertmanager webhook receiver used only by the local runtime proof.

It appends every notification to a JSONL receipt so the verification script can
assert that a FIRING and a RESOLVED notification were actually delivered. It is
not a production notifier and never talks to Telegram.
"""

import json
import os
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RECEIPT_PATH = os.environ.get("RECEIPT_PATH", "/receipts/alertmanager-receipts.jsonl")
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep container logs quiet
        return

    def _reply(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, {"status": "ok"})
            return
        self._reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/alert":
            self._reply(404, {"error": "not found"})
            return
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._reply(400, {"error": "invalid json"})
            return
        received = datetime.now(UTC).isoformat()
        with LOCK, open(RECEIPT_PATH, "a", encoding="utf-8") as handle:
            for alert in body.get("alerts", []):
                handle.write(
                    json.dumps(
                        {
                            "received_at": received,
                            "status": alert.get("status"),
                            "alertname": alert.get("labels", {}).get("alertname"),
                            "labels": alert.get("labels", {}),
                            "annotations": alert.get("annotations", {}),
                            "startsAt": alert.get("startsAt"),
                            "endsAt": alert.get("endsAt"),
                            "fingerprint": alert.get("fingerprint"),
                            "groupKey": body.get("groupKey"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            handle.flush()
            os.fsync(handle.fileno())
        self._reply(200, {"status": "recorded", "alerts": len(body.get("alerts", []))})


if __name__ == "__main__":
    os.makedirs(os.path.dirname(RECEIPT_PATH), exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 9099), Handler).serve_forever()
