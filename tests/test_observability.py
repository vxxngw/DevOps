import json
from types import SimpleNamespace

from clinic.api import app
from clinic.broker import publish
from clinic.telemetry import HTTP_COUNT, QUEUE_WAIT
from clinic.worker import observe_queue_delay
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY


def test_unexpected_error_is_counted_and_returns_safe_request_id(capsys):
    async def crash():
        raise RuntimeError("private@example.test hidden-provider-response")

    original = list(app.router.routes)
    route = "/api/test-observability-fault"
    app.add_api_route(route, crash, methods=["GET"])
    counter = HTTP_COUNT.labels(route, "GET", "500")
    before = counter._value.get()
    try:
        with TestClient(app) as client:
            response = client.get(route, headers={"X-Request-ID": "observability-error-1"})
        assert response.status_code == 500
        assert response.headers["X-Request-ID"] == "observability-error-1"
        assert response.json()["error"]["request_id"] == "observability-error-1"
        assert counter._value.get() == before + 1
        output = capsys.readouterr().out
        assert "private@example.test" not in output + response.text
        assert "hidden-provider-response" not in output + response.text
        records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        assert any(
            item.get("message") == "http_request"
            and item["status"] == 500
            and item["level"] == "ERROR"
            for item in records
        )
    finally:
        app.router.routes[:] = original


def test_publication_timestamp_does_not_change_delivery_guarantees(monkeypatch):
    calls = []
    channel = SimpleNamespace(basic_publish=lambda **kw: calls.append(kw))
    monkeypatch.setattr("clinic.broker.time.time", lambda: 1800000000.75)
    publish(channel, {"event_id": "synthetic-event", "correlation_id": "synthetic-request"})
    assert calls[0]["mandatory"] is True
    assert calls[0]["properties"].delivery_mode == 2
    assert calls[0]["properties"].timestamp == 1800000000
    assert calls[0]["properties"].message_id == "synthetic-event"


def test_queue_delay_is_separate_from_processing_and_skips_unknown_timestamp(monkeypatch):
    monkeypatch.setattr("clinic.worker.time.time", lambda: 1800000020.0)
    before_sum = QUEUE_WAIT._sum.get()
    before_count = REGISTRY.get_sample_value("clinic_queue_delay_seconds_count")
    observe_queue_delay(SimpleNamespace(timestamp=1800000000))
    observe_queue_delay(SimpleNamespace())
    observe_queue_delay(SimpleNamespace(timestamp=1800001000))
    assert QUEUE_WAIT._sum.get() == before_sum + 20
    assert REGISTRY.get_sample_value("clinic_queue_delay_seconds_count") == before_count + 1
