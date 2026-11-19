import json
import smtplib
import time
from datetime import timedelta
from email.message import EmailMessage
from email.utils import formataddr
from zoneinfo import ZoneInfo

from sqlalchemy import select

from clinic.broker import connect, publish, topology
from clinic.config import settings
from clinic.contracts import validate
from clinic.db import session
from clinic.models import (
    Appointment,
    Delivery,
    Doctor,
    OutboxEvent,
    Reminder,
    Slot,
    User,
    now,
    uid,
    utc,
)
from clinic.telemetry import DEPENDENCY, EVENT_COUNT, EVENT_TIME, QUEUE_WAIT, log


def send_email(data):
    config = settings()
    message = EmailMessage()
    message["From"] = formataddr(("An Uyên Hospital", config.smtp_from))
    message["To"] = data["recipient"]
    is_reminder = data.get("event_type") == "appointment.reminder.v1"
    kind = "Nhắc lịch khám" if is_reminder else "Cập nhật lịch khám"
    message["Subject"] = "An Uyên Hospital | " + kind + " " + data["appointment_id"][:8]
    message["Message-ID"] = f"<{data['event_id']}@clinic.example.test>"
    local_time = (
        data["starts_at"].astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M")
    )
    message.set_content(
        "An Uyên Hospital\n\n"
        + ("Xin nhắc bạn về lịch khám sắp tới.\n" if is_reminder else "")
        + f"Mã lịch hẹn: {data['appointment_id']}\nBác sĩ: {data['doctor']}\n"
        f"Giờ Việt Nam: {local_time}\nTrạng thái: {data['status']}\n"
    )
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=config.smtp_timeout) as smtp:
        if config.smtp_starttls:
            smtp.starttls()
        if config.smtp_user:
            smtp.login(config.smtp_user, config.smtp_password.get_secret_value())
        smtp.send_message(message)


def claim_event(event):
    with session() as db, db.begin():
        stored = db.get(OutboxEvent, event["event_id"])
        if stored is None or stored.payload != event:
            raise ValueError("untrusted event contract")
        delivery = db.scalar(
            select(Delivery).where(Delivery.event_id == stored.id).with_for_update()
        )
        if delivery.status in {"SENT", "SKIPPED", "FAILED_DLQ"}:
            return "done", None
        if delivery.lease_until and utc(delivery.lease_until) > now():
            return "busy", None
        appointment = db.get(Appointment, stored.appointment_id)
        stale = event["event_type"] == "appointment.created.v1" and appointment.status != "BOOKED"
        stale |= (
            event["event_type"] == "appointment.cancelled.v1" and appointment.status != "CANCELLED"
        )
        stale |= appointment.version != event["appointment_version"]
        if event["event_type"] == "appointment.reminder.v1":
            task = db.get(Reminder, appointment.id)
            stale |= (
                appointment.status != "BOOKED"
                or not appointment.reminder_enabled
                or task is None
                or task.event_id != event["event_id"]
                or task.status == "CANCELLED"
                or utc(db.get(Slot, appointment.slot_id).starts_at) <= now()
            )
        if stale:
            delivery.status, delivery.updated_at = "SKIPPED", now()
            return "stale", None
        slot = db.get(Slot, appointment.slot_id)
        delivery.status = "PROCESSING"
        delivery.attempts += 1
        delivery.lease_token = uid()
        delivery.lease_until = now() + timedelta(seconds=settings().lease_seconds)
        data = {
            "recipient": db.get(User, appointment.user_id).email,
            "doctor": db.get(Doctor, slot.doctor_id).name,
            "starts_at": utc(slot.starts_at),
            "status": appointment.status,
            "appointment_id": appointment.id,
            "event_id": stored.id,
            "token": delivery.lease_token,
            "attempt": delivery.attempts,
            "event_type": event["event_type"],
        }
        return "claimed", data


def finish(event_id, token, status, error=None):
    with session() as db, db.begin():
        delivery = db.scalar(
            select(Delivery)
            .where(Delivery.event_id == event_id, Delivery.lease_token == token)
            .with_for_update()
        )
        if not delivery:
            raise RuntimeError("delivery lease lost")
        delivery.status, delivery.last_error = status, error
        delivery.lease_until, delivery.lease_token, delivery.updated_at = None, None, now()


def observe_queue_delay(properties):
    published = getattr(properties, "timestamp", None)
    current = time.time()
    # Legacy messages and clocks ahead of this consumer do not produce a fake zero.
    if isinstance(published, int) and not isinstance(published, bool) and 0 < published <= current:
        QUEUE_WAIT.observe(current - published)


def process(channel, method, properties, body, sender=send_email):
    start = time.monotonic()
    event = json.loads(body)
    validate(event)
    observe_queue_delay(properties)
    event_id = event.get("event_id")
    outcome, data = claim_event(event)
    if outcome in {"done", "stale"}:
        channel.basic_ack(method.delivery_tag)
        EVENT_COUNT.labels("notification-worker", outcome).inc()
        return
    if outcome == "busy":
        # Keep duplicate durable without a hot requeue loop while the other claim is alive.
        publish(channel, event, destination="retry", delay=settings().retries[0])
        channel.basic_ack(method.delivery_tag)
        return
    try:
        if settings().worker_delay_seconds:
            time.sleep(settings().worker_delay_seconds)
        # Recheck immediately before provider call; cancellation can still race the external call.
        with session() as db:
            appointment = db.get(Appointment, event["appointment_id"])
            reminder_disabled = event["event_type"] == "appointment.reminder.v1" and (
                not appointment.reminder_enabled
                or appointment.status != "BOOKED"
                or utc(db.get(Slot, appointment.slot_id).starts_at) <= now()
            )
            if appointment.version != event["appointment_version"] or reminder_disabled:
                finish(event_id, data["token"], "SKIPPED")
                channel.basic_ack(method.delivery_tag)
                return
        sender(data)
    except Exception as exc:
        error = type(
            exc
        ).__name__  # Never retain provider response containing addresses or secrets.
        retries = settings().retries
        attempt = data["attempt"]
        if attempt <= len(retries):
            publish(
                channel,
                event,
                destination="retry",
                delay=retries[attempt - 1],
                headers={"attempt": attempt, "reason": error},
            )
            finish(event_id, data["token"], "RETRY_PENDING", error)
            outcome = "retry"
        else:
            publish(
                channel, event, destination="dlq", headers={"attempt": attempt, "reason": error}
            )
            finish(event_id, data["token"], "FAILED_DLQ", error)
            outcome = "failed_dlq"
    else:
        finish(event_id, data["token"], "SENT")
        outcome = "sent"
    # Failure in confirm or database update propagates: connection closes without ack.
    channel.basic_ack(method.delivery_tag)
    EVENT_COUNT.labels("notification-worker", outcome).inc()
    EVENT_TIME.labels("notification-worker").observe(time.monotonic() - start)
    log(
        "notification-worker",
        "delivery_processed",
        event_id=event_id,
        correlation_id=event["correlation_id"],
        outcome=outcome,
    )


def run(stop):
    while not stop.is_set():
        try:
            with connect() as connection:
                channel = connection.channel()
                topology(channel)
                DEPENDENCY.labels("rabbitmq").set(1)
                for method, properties, body in channel.consume(
                    settings().queue_prefix + ".notifications", inactivity_timeout=1, auto_ack=False
                ):
                    if stop.is_set():
                        break
                    if method:
                        try:
                            process(channel, method, properties, body)
                        except (ValueError, KeyError, json.JSONDecodeError) as exc:
                            # Foreign/malformed messages are kept in a bounded, durable quarantine.
                            # Rejecting does not acknowledge arbitrary invalid data as successful work.
                            log(
                                "notification-worker",
                                "invalid_event",
                                level="ERROR",
                                error_type=type(exc).__name__,
                            )
                            channel.basic_reject(method.delivery_tag, requeue=False)
                channel.cancel()
        except Exception as exc:
            DEPENDENCY.labels("rabbitmq").set(0)
            log(
                "notification-worker",
                "consume_loop_failed",
                level="ERROR",
                error_type=type(exc).__name__,
            )
            stop.wait(2)
