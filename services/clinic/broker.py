import json
import time

import pika

from clinic.config import settings


def connect():
    params = pika.URLParameters(settings().rabbitmq_url.get_secret_value())
    params.heartbeat = 60
    params.blocked_connection_timeout = 15
    params.socket_timeout = 5
    params.connection_attempts = 1
    return pika.BlockingConnection(params)


def topology(channel):
    prefix = settings().queue_prefix
    channel.exchange_declare(exchange=prefix + ".events", exchange_type="direct", durable=True)
    channel.exchange_declare(exchange=prefix + ".dead", exchange_type="direct", durable=True)
    channel.queue_declare(
        queue=prefix + ".notifications",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": prefix + ".dead",
            "x-dead-letter-routing-key": "failed",
            "x-overflow": "reject-publish",
            "x-dead-letter-strategy": "at-least-once",
        },
    )
    channel.queue_bind(
        queue=prefix + ".notifications", exchange=prefix + ".events", routing_key="notify"
    )
    channel.queue_declare(queue=prefix + ".dlq", durable=True, arguments={"x-queue-type": "quorum"})
    channel.queue_bind(queue=prefix + ".dlq", exchange=prefix + ".dead", routing_key="failed")
    for delay in settings().retries:
        channel.queue_declare(
            queue=f"{prefix}.retry.{delay}",
            durable=True,
            arguments={
                "x-message-ttl": delay * 1000,
                "x-dead-letter-exchange": prefix + ".events",
                "x-dead-letter-routing-key": "notify",
                "x-queue-type": "quorum",
                "x-overflow": "reject-publish",
                "x-dead-letter-strategy": "at-least-once",
            },
        )
    channel.basic_qos(prefetch_count=1)
    channel.confirm_delivery()


def publish(channel, event, *, destination="main", delay=None, headers=None):
    prefix = settings().queue_prefix
    exchange, key = prefix + ".events", "notify"
    if destination == "retry":
        exchange, key = "", f"{prefix}.retry.{delay}"
    elif destination == "dlq":
        exchange, key = prefix + ".dead", "failed"
    channel.basic_publish(
        exchange=exchange,
        routing_key=key,
        body=json.dumps(event).encode(),
        mandatory=True,
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
            message_id=event["event_id"],
            correlation_id=event["correlation_id"],
            timestamp=int(time.time()),
            headers=headers or {},
        ),
    )
