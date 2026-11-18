import json
import os
import time

import httpx
import pika
import pytest
from clinic import publisher, worker
from clinic.broker import connect, publish, topology
from clinic.config import settings
from clinic.db import session
from clinic.dlq import replay
from clinic.models import Delivery, OutboxEvent, Reminder
from clinic.reminders import enqueue_due_reminders
from test_reminders import due_time, opt_in

pytestmark = pytest.mark.integration
MAILPIT_API = os.environ.get("MAILPIT_API_URL", "http://localhost:8025")


@pytest.fixture
def broker():
    if os.environ.get("RUN_BROKER_TESTS") != "1":
        pytest.skip("Real broker/Mailpit tests require --integration via scripts/dev/verify.py")
    with connect() as connection:
        channel = connection.channel()
        topology(channel)
        queues = [settings().queue_prefix + ".notifications", settings().queue_prefix + ".dlq"]
        queues += [f"{settings().queue_prefix}.retry.{d}" for d in settings().retries]
        for queue in queues:
            channel.queue_purge(queue)
        try:
            yield channel
        finally:
            for queue in queues:
                channel.queue_delete(queue)
            for exchange in [".events", ".dead"]:
                channel.exchange_delete(settings().queue_prefix + exchange)


def take(channel, queue="notifications", timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(
            settings().queue_prefix + "." + queue, auto_ack=False
        )
        if method:
            return method, properties, body
        time.sleep(0.1)
    raise AssertionError("Message did not arrive within bounded wait")


def test_real_broker_smtp_and_dedupe(event, broker):
    before = httpx.get(MAILPIT_API + "/api/v1/messages").json()["total"]
    assert publisher.publish_one(broker)
    worker.process(broker, *take(broker))
    assert httpx.get(MAILPIT_API + "/api/v1/messages").json()["total"] == before + 1
    publish(broker, event)
    worker.process(broker, *take(broker))
    assert httpx.get(MAILPIT_API + "/api/v1/messages").json()["total"] == before + 1
    with session() as db:
        assert db.get(OutboxEvent, event["event_id"]).published_at is not None
        assert db.get(Delivery, event["event_id"]).status == "SENT"


def test_real_unroutable_not_confirmed(event, broker):
    with pytest.raises(pika.exceptions.UnroutableError):
        broker.basic_publish(
            exchange=settings().queue_prefix + ".events",
            routing_key="no-such-route",
            body=json.dumps(event),
            mandatory=True,
            properties=pika.BasicProperties(delivery_mode=2),
        )


def test_real_smtp_outage_retry_dlq_replay(event, broker, monkeypatch):
    # Real connection refused from a closed local port, not a fake SMTP sender.
    config = settings()
    monkeypatch.setattr(config, "smtp_port", 1)
    assert publisher.publish_one(broker)
    for _ in range(4):
        worker.process(broker, *take(broker))
    with session() as db:
        assert db.get(Delivery, event["event_id"]).status == "FAILED_DLQ"
    monkeypatch.setattr(config, "smtp_port", 1025)
    replay(event["event_id"])
    worker.process(broker, *take(broker))
    with session() as db:
        delivery = db.get(Delivery, event["event_id"])
        assert delivery.status == "SENT" and delivery.replay_count == 1


def test_real_unacked_redelivered_after_connection_close(event, broker):
    publish(broker, event)
    with connect() as other:
        unacked_channel = other.channel()
        method, properties, body = take(unacked_channel)
        assert json.loads(body)["event_id"] == event["event_id"]
        # Closing without basic_ack simulates transport loss before acknowledgement.
    method, properties, body = take(broker)
    assert method.redelivered
    worker.process(broker, method, properties, body)


def test_real_scheduled_reminder_email_and_dedupe(client, patient, slot_id, broker):
    appointment = opt_in(client, patient, slot_id)
    assert publisher.publish_one(broker)  # Booking confirmation is a different event.
    worker.process(broker, *take(broker))
    assert enqueue_due_reminders(due_time(appointment["id"])) == 1
    assert publisher.publish_one(broker)
    worker.process(broker, *take(broker))
    with session() as db:
        event = dict(db.get(OutboxEvent, db.get(Reminder, appointment["id"]).event_id).payload)
        assert db.get(Delivery, event["event_id"]).status == "SENT"
    before = httpx.get(MAILPIT_API + "/api/v1/messages").json()["total"]
    publish(broker, event)
    worker.process(broker, *take(broker))
    assert httpx.get(MAILPIT_API + "/api/v1/messages").json()["total"] == before
    inbox = httpx.get(MAILPIT_API + "/api/v1/messages").json()["messages"]
    assert any("Nhắc lịch khám " + appointment["id"][:8] in message["Subject"] for message in inbox)
    detail = client.get("/api/appointments/" + appointment["id"], headers=patient).json()
    assert detail["reminder_status"] == "SENT"
    assert detail["notification_status"] == "SENT"
