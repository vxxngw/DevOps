"""Explicit operator account provisioning, including first production login; never demo seed/reset."""

import argparse
import getpass
import json
import re
from pathlib import Path

from sqlalchemy import select

from clinic.db import session
from clinic.models import User
from clinic.security import passwords


def create_user(email, role, password):
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.test", email) or role not in {
        "admin",
        "patient",
    }:
        raise ValueError("This lab accepts synthetic .test accounts only")
    if len(password) < 12:
        raise ValueError("Use a password with at least 12 characters")
    with session() as db, db.begin():
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            if existing.role != role:
                raise ValueError("Existing account role differs; no account changed")
            return False
        db.add(User(email=email, role=role, password_hash=passwords.hash(password)))
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=["admin", "patient"], required=True)
    parser.add_argument("--password-file")
    args = parser.parse_args()
    password = (
        Path(args.password_file).read_text().strip()
        if args.password_file
        else getpass.getpass("New synthetic account password: ")
    )
    print(
        json.dumps(
            {
                "created": create_user(args.email, args.role, password),
                "role": args.role,
                "scope": "Explicit account creation; no password reset or doctor/slot seed",
            }
        )
    )


if __name__ == "__main__":
    main()
