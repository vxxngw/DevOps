import json
import logging
import sys
from datetime import UTC, datetime

from prometheus_client import Counter, Gauge, Histogram

HTTP_COUNT = Counter("clinic_http_requests_total", "HTTP requests", ["route", "method", "status"])
HTTP_TIME = Histogram("clinic_http_duration_seconds", "Business HTTP duration", ["route", "method"])
EVENT_COUNT = Counter("clinic_events_total", "Event outcomes", ["service", "outcome"])
EVENT_TIME = Histogram("clinic_event_duration_seconds", "Event processing time", ["service"])
QUEUE_WAIT = Histogram(
    "clinic_queue_delay_seconds",
    "Seconds since the most recent AMQP publication, including retry TTL when present",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
OUTBOX_PENDING = Gauge("clinic_outbox_pending", "Unpublished events")
OUTBOX_AGE = Gauge("clinic_outbox_oldest_seconds", "Age of oldest unpublished event")
DEPENDENCY = Gauge("clinic_dependency_ready", "Dependency connection status", ["dependency"])


def log(service, message, level="INFO", **fields):
    # Call sites pass identifiers and error class only, never payloads/credentials/recipient.
    from clinic.config import settings

    print(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "service": service,
                "environment": settings().environment,
                "message": message,
                **fields,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Suppress arbitrary library exception strings which can contain DSNs or email addresses.
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "service": "runtime",
                "message": record.name,
                "error_type": type(record.exc_info[1]).__name__ if record.exc_info else None,
            }
        )


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(handlers=[handler], level=logging.WARNING, force=True)
