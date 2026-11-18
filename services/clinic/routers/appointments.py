from fastapi import APIRouter, Depends, Header, Request

from clinic.application import appointments as appointments_actions
from clinic.db import get_db
from clinic.schemas.appointments import Booking, ReminderPreference
from clinic.security import current_user

router = APIRouter()


@router.post("/api/appointments", status_code=201)
def book(
    body: Booking,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=128),
    db=Depends(get_db),
    user=Depends(current_user),
):
    return appointments_actions.book(body, request.state.request_id, idempotency_key, db, user)


@router.get("/api/appointments")
def appointments(db=Depends(get_db), user=Depends(current_user)):
    return appointments_actions.appointments(db, user)


@router.get("/api/appointments/{appointment_id}")
def detail(appointment_id: str, db=Depends(get_db), user=Depends(current_user)):
    return appointments_actions.detail(appointment_id, db, user)


@router.post("/api/appointments/{appointment_id}/cancel")
def cancel(appointment_id: str, request: Request, db=Depends(get_db), user=Depends(current_user)):
    return appointments_actions.cancel(appointment_id, request.state.request_id, db, user)


@router.patch("/api/appointments/{appointment_id}/reminder")
def update_reminder(
    appointment_id: str, body: ReminderPreference, db=Depends(get_db), user=Depends(current_user)
):
    return appointments_actions.update_reminder(appointment_id, body, db, user)
