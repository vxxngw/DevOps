"""Header-rewriting proxy between the local Fluentd collector and Elasticsearch.

fluent-plugin-elasticsearch 5.4.3 always sends
`application/vnd.elasticsearch+json; compatible-with=9` (and the x-ndjson
equivalent) on Accept and Content-Type. Elasticsearch 8.15 rejects those with
`media_type_header_exception: Content-Type version must be either version 8 or
7, but found 9`, and the plugin exposes no option to change the version.

This proxy sits in front of Elasticsearch inside the local compose network and
repairs exactly two things on the way through:

1. `compatible-with=9` -> `compatible-with=8`;
2. duplicate / unversioned `Accept` headers -> a single versioned value.

It does not parse, filter or reshape any document, so the documents that land
in Elasticsearch are exactly the ones Fluentd produced.

Only used by the local Docker runtime. The Kubernetes deployment talks to
Elasticsearch directly.
"""

from __future__ import annotations

import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = os.environ.get("ES_UPSTREAM_HOST", "elasticsearch")
UPSTREAM_PORT = int(os.environ.get("ES_UPSTREAM_PORT", "9200"))
LISTEN_PORT = int(os.environ.get("ES_PROXY_PORT", "9200"))

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def downgrade(value: str) -> str:
    return value.replace("compatible-with=9", "compatible-with=8")


def build_headers(pairs) -> dict:
    """Collapse inbound headers into a case-insensitive, single-valued dict."""
    merged: dict[str, str] = {}
    for key, value in pairs:
        lower = key.lower()
        if lower in HOP_BY_HOP:
            continue
        value = downgrade(value)
        if lower in merged:
            # Repeated header: keep the first value only, Elasticsearch rejects
            # multi-valued Accept/Content-Type.
            continue
        merged[lower] = value

    content_type = merged.get("content-type", "")
    accept = merged.get("accept", "")
    if "compatible-with=8" in content_type:
        if "compatible-with=" not in accept:
            media = "x-ndjson" if "x-ndjson" in content_type else "json"
            merged["accept"] = f"application/vnd.elasticsearch+{media}; compatible-with=8"
        else:
            merged["accept"] = accept
    return merged


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "es-header-proxy"

    def log_message(self, fmt, *args):  # noqa: A003 - silence per-request noise
        pass

    def _forward(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        headers = build_headers(self.headers.items())

        connection = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=60)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            status = response.status
            response_headers = response.getheaders()
        finally:
            connection.close()

        self.send_response(status)
        for key, value in response_headers:
            if key.lower() in HOP_BY_HOP:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_DELETE = _forward
    do_HEAD = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Proxy).serve_forever()
