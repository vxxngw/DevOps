import hashlib
import json
import re
import time
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import exists, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from clinic.config import settings
from clinic.db import get_db
from clinic.events import add_event
from clinic.models import (
    Appointment,
    Delivery,
    Doctor,
    IdempotencyKey,
    OutboxEvent,
    Reminder,
    Slot,
    User,
    now,
    utc,
)
from clinic.reminders import cancel_reminder, set_reminder
from clinic.security import DUMMY_HASH, admin_user, create_token, current_user, passwords
from clinic.telemetry import HTTP_COUNT, HTTP_TIME, configure_logging, log

configure_logging()
app = FastAPI(title="An Uyên Hospital · API đặt lịch khám", version="0.1.0")


@app.middleware("http")
async def observe(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request.state.request_id = (
        supplied if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", supplied) else str(uuid.uuid4())
    )
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        # Unexpected application errors still need a safe, observable 5xx response.
        log(
            "appointment-api",
            "unhandled_error",
            level="ERROR",
            request_id=request.state.request_id,
            error_type=type(exc).__name__,
        )
        response = JSONResponse(
            {
                "error": {
                    "message": "Có lỗi xử lý. Vui lòng thử lại.",
                    "request_id": request.state.request_id,
                }
            },
            status_code=500,
        )
    route = getattr(request.scope.get("route"), "path", "unmatched")
    if route not in {"/health", "/ready", "/metrics"}:
        HTTP_COUNT.labels(route, request.method, str(response.status_code)).inc()
        HTTP_TIME.labels(route, request.method).observe(time.monotonic() - start)
        log(
            "appointment-api",
            "http_request",
            level="ERROR" if response.status_code >= 500 else "INFO",
            request_id=request.state.request_id,
            route=route,
            method=request.method,
            status=response.status_code,
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(
        {"error": {"message": exc.detail, "request_id": request.state.request_id}},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "error": {
                "message": "Dữ liệu đầu vào không hợp lệ",
                "request_id": request.state.request_id,
            }
        },
        status_code=422,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    log(
        "appointment-api",
        "database_error",
        level="ERROR",
        request_id=request.state.request_id,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        {
            "error": {
                "message": "CSDL tạm thời chưa sẵn sàng",
                "request_id": request.state.request_id,
            }
        },
        status_code=503,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "appointment-api"}


@app.get("/ready")
def ready(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)


@app.post("/api/auth/login")
def login(body: Login, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return {"access_token": create_token(user), "token_type": "bearer", "role": user.role}


@app.get("/api/doctors")
def doctors(db=Depends(get_db), user=Depends(current_user)):
    return [
        {"id": d.id, "name": d.name, "specialty": d.specialty, "active": d.active}
        for d in db.scalars(select(Doctor).where(Doctor.active.is_(True)).order_by(Doctor.name))
    ]


@app.get("/api/options")
def options(user=Depends(current_user)):
    return {"reminder_lead_minutes": settings().reminder_lead_minutes}


def slot_view(slot):
    return {
        "id": slot.id,
        "doctor_id": slot.doctor_id,
        "starts_at": utc(slot.starts_at).isoformat(),
        "ends_at": utc(slot.ends_at).isoformat(),
    }


@app.get("/api/doctors/{doctor_id}/slots")
def slots(
    doctor_id: str,
    include_unavailable: bool = False,
    db=Depends(get_db),
    user=Depends(current_user),
):
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


class Booking(BaseModel):
    slot_id: uuid.UUID
    reminder_enabled: bool = False


@app.post("/api/appointments", status_code=201)
def book(
    body: Booking,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=128),
    db=Depends(get_db),
    user=Depends(current_user),
):
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
        if previous.payload_hash != payload_hash and not legacy_match:
            raise HTTPException(409, "Idempotency-Key đã được dùng với nội dung khác")
        return previous.response

    previous = db.scalar(idem_query)
    if previous:
        return replay(previous)
    record = IdempotencyKey(user_id=user.id, key=idempotency_key, payload_hash=payload_hash)
    db.add(record)
    try:
        db.flush()  # PostgreSQL unique constraint serializes concurrent uses of the same key.
    except IntegrityError:
        db.rollback()
        previous = db.scalar(idem_query)
        if previous:
            return replay(previous)
        raise HTTPException(409, "Yêu cầu đang được xử lý; vui lòng thử lại") from None
    slot = db.scalar(select(Slot).where(Slot.id == str(body.slot_id)).with_for_update())
    if not slot or utc(slot.starts_at) <= now() or not db.get(Doctor, slot.doctor_id).active:
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
        add_event(db, appointment, "appointment.created.v1", request.state.request_id)
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


@app.get("/api/appointments")
def appointments(db=Depends(get_db), user=Depends(current_user)):
    return [
        appointment_view(db, a)
        for a in db.scalars(
            select(Appointment)
            .where(Appointment.user_id == user.id)
            .order_by(Appointment.created_at.desc())
            .limit(500)
        )
    ]


@app.get("/api/appointments/{appointment_id}")
def detail(appointment_id: str, db=Depends(get_db), user=Depends(current_user)):
    return appointment_view(db, owned(db, appointment_id, user))


@app.post("/api/appointments/{appointment_id}/cancel")
def cancel(appointment_id: str, request: Request, db=Depends(get_db), user=Depends(current_user)):
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
    add_event(db, appointment, "appointment.cancelled.v1", request.state.request_id)
    db.commit()
    return appointment_view(db, appointment)


class ReminderPreference(BaseModel):
    enabled: bool


@app.patch("/api/appointments/{appointment_id}/reminder")
def update_reminder(
    appointment_id: str, body: ReminderPreference, db=Depends(get_db), user=Depends(current_user)
):
    appointment = owned(db, appointment_id, user, lock=True)
    if appointment.status != "BOOKED" or utc(db.get(Slot, appointment.slot_id).starts_at) <= now():
        raise HTTPException(409, "Chỉ cập nhật nhắc lịch cho lịch hẹn sắp tới đang còn hiệu lực.")
    try:
        set_reminder(db, appointment, body.enabled)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    db.commit()
    return appointment_view(db, appointment)


class DoctorInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    specialty: str = Field(min_length=1, max_length=100)
    active: bool = True


@app.post("/api/admin/doctors", status_code=201)
def create_doctor(body: DoctorInput, db=Depends(get_db), user=Depends(admin_user)):
    doctor = Doctor(**body.model_dump())
    db.add(doctor)
    db.commit()
    return {"id": doctor.id, **body.model_dump()}


@app.put("/api/admin/doctors/{doctor_id}")
def update_doctor(doctor_id: str, body: DoctorInput, db=Depends(get_db), user=Depends(admin_user)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    for key, value in body.model_dump().items():
        setattr(doctor, key, value)
    db.commit()
    return {"id": doctor.id, **body.model_dump()}


class SlotInput(BaseModel):
    doctor_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime


@app.post("/api/admin/slots", status_code=201)
def create_slot(body: SlotInput, db=Depends(get_db), user=Depends(admin_user)):
    if (
        body.starts_at.tzinfo is None
        or body.ends_at.tzinfo is None
        or body.starts_at <= now()
        or body.ends_at <= body.starts_at
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


@app.delete("/api/admin/slots/{slot_id}")
def delete_slot(slot_id: str, db=Depends(get_db), user=Depends(admin_user)):
    slot = db.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
    if not slot:
        raise HTTPException(404, "Không tìm thấy khung giờ")
    if db.scalar(select(Appointment).where(Appointment.slot_id == slot.id).limit(1)):
        raise HTTPException(409, "Giữ khung giờ đã có lịch để bảo toàn lịch sử")
    db.delete(slot)
    db.commit()
    return {"deleted": True}


@app.get("/api/admin/appointments")
def admin_appointments(status: str | None = None, db=Depends(get_db), user=Depends(admin_user)):
    query = select(Appointment).order_by(Appointment.created_at.desc()).limit(500)
    if status:
        query = query.where(Appointment.status == status)
    return [appointment_view(db, a) for a in db.scalars(query)]


@app.post("/api/admin/appointments/{appointment_id}/complete")
def complete(appointment_id: str, db=Depends(get_db), user=Depends(admin_user)):
    appointment = owned(db, appointment_id, user, lock=True)
    if appointment.status != "BOOKED" or utc(db.get(Slot, appointment.slot_id).ends_at) > now():
        raise HTTPException(409, "Chỉ hoàn tất lịch đang đặt khi đã hết giờ khám")
    appointment.status = "COMPLETED"
    appointment.version += 1
    cancel_reminder(db, appointment)
    db.commit()
    return appointment_view(db, appointment)
