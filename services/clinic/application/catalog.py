from fastapi import HTTPException
from sqlalchemy import exists, select

from clinic.application.views import slot_view
from clinic.config import settings
from clinic.models import Appointment, Doctor, Slot, now, utc


def doctors(db, user):
    return [
        {"id": d.id, "name": d.name, "specialty": d.specialty, "active": d.active}
        for d in db.scalars(select(Doctor).where(Doctor.active.is_(True)).order_by(Doctor.name))
    ]


def options(user):
    return {"reminder_lead_minutes": settings().reminder_lead_minutes}


def slots(doctor_id, include_unavailable, db, user):
    occupied = exists().where(Appointment.slot_id == Slot.id, Appointment.status != "CANCELLED")
    query = (
        select(Slot, occupied)
        .where(Slot.doctor_id == doctor_id, Slot.starts_at > now())
        .order_by(Slot.starts_at)
        .limit(500)
    )
    if not include_unavailable:
        query = query.where(~occupied)
    return [
        {**slot_view(slot), "available": not is_occupied} for slot, is_occupied in db.execute(query)
    ]


def create_doctor(body, db, user):
    doctor = Doctor(**body.model_dump())
    db.add(doctor)
    db.commit()
    return {"id": doctor.id, **body.model_dump()}


def update_doctor(doctor_id, body, db, user):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    for key, value in body.model_dump().items():
        setattr(doctor, key, value)
    db.commit()
    return {"id": doctor.id, **body.model_dump()}


def create_slot(body, db, user):
    if (
        body.starts_at.tzinfo is None
        or body.ends_at.tzinfo is None
        or body.starts_at <= now()
        or (body.ends_at <= body.starts_at)
    ):
        raise HTTPException(422, "Khung giờ phải ở tương lai, có múi giờ và kết thúc sau bắt đầu")
    doctor = db.scalar(select(Doctor).where(Doctor.id == str(body.doctor_id)).with_for_update())
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    overlap = db.scalar(
        select(Slot).where(
            Slot.doctor_id == doctor.id,
            Slot.starts_at < body.ends_at,
            Slot.ends_at > body.starts_at,
        )
    )
    if overlap:
        raise HTTPException(409, "Khung giờ bị chồng lấn")
    slot = Slot(doctor_id=doctor.id, starts_at=utc(body.starts_at), ends_at=utc(body.ends_at))
    db.add(slot)
    db.commit()
    return slot_view(slot)


def delete_slot(slot_id, db, user):
    slot = db.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
    if not slot:
        raise HTTPException(404, "Không tìm thấy khung giờ")
    if db.scalar(select(Appointment).where(Appointment.slot_id == slot.id).limit(1)):
        raise HTTPException(409, "Giữ khung giờ đã có lịch để bảo toàn lịch sử")
    db.delete(slot)
    db.commit()
    return {"deleted": True}
