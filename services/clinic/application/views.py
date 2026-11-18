from sqlalchemy import select

from clinic.models import Delivery, Doctor, OutboxEvent, Reminder, Slot, utc


def slot_view(slot):
    return {
        "id": slot.id,
        "doctor_id": slot.doctor_id,
        "starts_at": utc(slot.starts_at).isoformat(),
        "ends_at": utc(slot.ends_at).isoformat(),
    }


def appointment_view(db, appointment):
    slot = db.get(Slot, appointment.slot_id)
    doctor = db.get(Doctor, slot.doctor_id)
    latest = db.scalar(
        select(OutboxEvent)
        .where(
            OutboxEvent.appointment_id == appointment.id,
            OutboxEvent.payload["event_type"]
            .as_string()
            .in_(["appointment.created.v1", "appointment.cancelled.v1"]),
        )
        .order_by(OutboxEvent.created_at.desc())
        .limit(1)
    )
    delivery = db.get(Delivery, latest.id) if latest else None
    task = db.get(Reminder, appointment.id)
    reminder_delivery = db.get(Delivery, task.event_id) if task and task.event_id else None
    reminder_status = "OFF"
    if reminder_delivery and reminder_delivery.status == "SENT":
        reminder_status = "SENT"
    elif task and appointment.reminder_enabled:
        if task.status == "CANCELLED" or appointment.status != "BOOKED":
            reminder_status = "CANCELLED"
        else:
            reminder_status = reminder_delivery.status if reminder_delivery else "SCHEDULED"
    return {
        "id": appointment.id,
        "status": appointment.status,
        "version": appointment.version,
        "doctor": doctor.name,
        "slot": slot_view(slot),
        "notification_status": delivery.status if delivery else "PENDING",
        "notification_error": delivery.last_error if delivery else None,
        "reminder_enabled": appointment.reminder_enabled,
        "reminder_at": utc(task.due_at).isoformat() if task else None,
        "reminder_status": reminder_status,
    }
