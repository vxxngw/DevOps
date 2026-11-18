import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from clinic.application.views import appointment_view
from clinic.events import add_event
from clinic.models import Appointment, Doctor, IdempotencyKey, Slot, now, utc
from clinic.reminders import cancel_reminder, set_reminder


def book(body, request_id, idempotency_key, db, user):
    legacy_hash = hashlib.sha256(str(body.slot_id).encode()).hexdigest()
    payload_hash = hashlib.sha256(
        json.dumps(
            {"slot_id": str(body.slot_id), "reminder_enabled": body.reminder_enabled},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    idem_query = select(IdempotencyKey).where(
        IdempotencyKey.user_id == user.id,
        IdempotencyKey.operation == "book",
        IdempotencyKey.key == idempotency_key,
    )

    def replay(previous):
        legacy_match = not body.reminder_enabled and previous.payload_hash == legacy_hash
        if previous.payload_hash != payload_hash and (not legacy_match):
            raise HTTPException(409, "Idempotency-Key đã được dùng với nội dung khác")
        return previous.response

    previous = db.scalar(idem_query)
    if previous:
        return replay(previous)
    record = IdempotencyKey(user_id=user.id, key=idempotency_key, payload_hash=payload_hash)
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(idem_query)
        if previous:
            return replay(previous)
        raise HTTPException(409, "Yêu cầu đang được xử lý; vui lòng thử lại") from None
    slot = db.scalar(select(Slot).where(Slot.id == str(body.slot_id)).with_for_update())
    if not slot or utc(slot.starts_at) <= now() or (not db.get(Doctor, slot.doctor_id).active):
        raise HTTPException(409, "Khung giờ không tồn tại hoặc không còn nhận lịch")
    occupied = db.scalar(
        select(Appointment).where(Appointment.slot_id == slot.id, Appointment.status != "CANCELLED")
    )
    if occupied:
        raise HTTPException(409, "Khung giờ đã được đặt")
    appointment = Appointment(user_id=user.id, slot_id=slot.id, status="BOOKED", version=1)
    db.add(appointment)
    try:
        db.flush()
        add_event(db, appointment, "appointment.created.v1", request_id)
        try:
            set_reminder(db, appointment, body.reminder_enabled)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        record.response = appointment_view(db, appointment)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Khung giờ đã được đặt") from None
    return record.response


def owned(db, appointment_id, user, lock=False):
    query = select(Appointment).where(Appointment.id == appointment_id)
    appointment = db.scalar(query.with_for_update() if lock else query)
    if not appointment or (appointment.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy lịch hẹn")
    return appointment


def appointments(db, user):
    return [
        appointment_view(db, a)
        for a in db.scalars(
            select(Appointment)
            .where(Appointment.user_id == user.id)
            .order_by(Appointment.created_at.desc())
            .limit(500)
        )
    ]


def detail(appointment_id, db, user):
    return appointment_view(db, owned(db, appointment_id, user))


def cancel(appointment_id, request_id, db, user):
    appointment = owned(db, appointment_id, user, lock=True)
    if appointment.status == "CANCELLED":
        return appointment_view(db, appointment)
    if appointment.status != "BOOKED":
        raise HTTPException(409, "Không thể hủy lịch đã hoàn tất")
    if utc(db.get(Slot, appointment.slot_id).starts_at) <= now():
        raise HTTPException(409, "Không thể hủy lịch đã đến giờ khám")
    appointment.status = "CANCELLED"
    appointment.version += 1
    cancel_reminder(db, appointment)
    add_event(db, appointment, "appointment.cancelled.v1", request_id)
    db.commit()
    return appointment_view(db, appointment)


def update_reminder(appointment_id, body, db, user):
    appointment = owned(db, appointment_id, user, lock=True)
    if appointment.status != "BOOKED" or utc(db.get(Slot, appointment.slot_id).starts_at) <= now():
        raise HTTPException(409, "Chỉ cập nhật nhắc lịch cho lịch hẹn sắp tới đang còn hiệu lực.")
    try:
        set_reminder(db, appointment, body.enabled)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    db.commit()
    return appointment_view(db, appointment)


def admin_appointments(status, db, user):
    query = select(Appointment).order_by(Appointment.created_at.desc()).limit(500)
    if status:
        query = query.where(Appointment.status == status)
    return [appointment_view(db, a) for a in db.scalars(query)]


def complete(appointment_id, db, user):
    appointment = owned(db, appointment_id, user, lock=True)
    if appointment.status != "BOOKED" or utc(db.get(Slot, appointment.slot_id).ends_at) > now():
        raise HTTPException(409, "Chỉ hoàn tất lịch đang đặt khi đã hết giờ khám")
    appointment.status = "COMPLETED"
    appointment.version += 1
    cancel_reminder(db, appointment)
    db.commit()
    return appointment_view(db, appointment)
