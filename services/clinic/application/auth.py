from fastapi import HTTPException
from sqlalchemy import select

from clinic.models import User
from clinic.security import DUMMY_HASH, create_token, passwords


def login(body, db):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return {"access_token": create_token(user), "token_type": "bearer", "role": user.role}
