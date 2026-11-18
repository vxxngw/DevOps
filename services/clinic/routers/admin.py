from fastapi import APIRouter, Depends

from clinic.application import appointments as appointments_actions
from clinic.application import catalog as catalog_actions
from clinic.db import get_db
from clinic.schemas.catalog import DoctorInput, SlotInput
from clinic.security import admin_user

router = APIRouter()


@router.post("/api/admin/doctors", status_code=201)
def create_doctor(body: DoctorInput, db=Depends(get_db), user=Depends(admin_user)):
    return catalog_actions.create_doctor(body, db, user)


@router.put("/api/admin/doctors/{doctor_id}")
def update_doctor(doctor_id: str, body: DoctorInput, db=Depends(get_db), user=Depends(admin_user)):
    return catalog_actions.update_doctor(doctor_id, body, db, user)


@router.post("/api/admin/slots", status_code=201)
def create_slot(body: SlotInput, db=Depends(get_db), user=Depends(admin_user)):
    return catalog_actions.create_slot(body, db, user)


@router.delete("/api/admin/slots/{slot_id}")
def delete_slot(slot_id: str, db=Depends(get_db), user=Depends(admin_user)):
    return catalog_actions.delete_slot(slot_id, db, user)


@router.get("/api/admin/appointments")
def admin_appointments(status: str | None = None, db=Depends(get_db), user=Depends(admin_user)):
    return appointments_actions.admin_appointments(status, db, user)


@router.post("/api/admin/appointments/{appointment_id}/complete")
def complete(appointment_id: str, db=Depends(get_db), user=Depends(admin_user)):
    return appointments_actions.complete(appointment_id, db, user)
