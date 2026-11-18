from fastapi import APIRouter, Depends

from clinic.application import auth as auth_actions
from clinic.db import get_db
from clinic.schemas.auth import Login

router = APIRouter()


@router.post("/api/auth/login")
def login(body: Login, db=Depends(get_db)):
    return auth_actions.login(body, db)
