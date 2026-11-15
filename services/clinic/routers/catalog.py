from fastapi import APIRouter, Depends

from clinic.application import catalog as catalog_actions
from clinic.db import get_db
from clinic.security import current_user

router = APIRouter()


@router.get("/api/doctors")
def doctors(db=Depends(get_db), user=Depends(current_user)):
    return catalog_actions.doctors(db, user)


@router.get("/api/options")
def options(user=Depends(current_user)):
    return catalog_actions.options(user)


@router.get("/api/doctors/{doctor_id}/slots")
def slots(
    doctor_id: str,
    include_unavailable: bool = False,
    db=Depends(get_db),
    user=Depends(current_user),
):
    return catalog_actions.slots(doctor_id, include_unavailable, db, user)
