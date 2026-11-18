"""Business smoke restricted to a newly restored, isolated dev database."""

import json
import os
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from alembic.config import Config
from alembic.script import ScriptDirectory
from clinic.config import settings
from clinic.db import session
from clinic.models import OutboxEvent, User
from clinic.security import passwords
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text


def main():
    expected = os.environ["CLINIC_RESTORE_DB"]
    if not re.fullmatch(r"clinic_restore_[a-f0-9]{20}", expected):
        raise ValueError("Business smoke is restricted to the owned restore database")
    if settings().environment != "test":
        raise ValueError("Restore smoke requires ENVIRONMENT=test")
    checks = []
    with session() as db:
        if db.scalar(text("SELECT current_database()")) != expected:
            raise ValueError("Refusing to write fixtures to another database")
        current = set(db.scalars(text("SELECT version_num FROM alembic_version")))
        if current != set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads()):
            raise ValueError("Restored backup schema does not match the current migration heads")
    checks.extend(["owned_restore_database", "migration_heads_match_without_migrating"])
    marker = uuid.uuid4().hex[:16]
    password = secrets.token_urlsafe(24)
    hashed = passwords.hash(password)
    emails = {role: f"restore.{role}.{marker}@example.test" for role in ["admin", "patient"]}
    with session() as db, db.begin():
        for role, email in emails.items():
            db.add(User(email=email, password_hash=hashed, role=role))

    from clinic.api import app

    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        headers = {}
        for role, email in emails.items():
            response = client.post("/api/auth/login", json={"email": email, "password": password})
            assert response.status_code == 200, "Restored database login failed"
            headers[role] = {"Authorization": "Bearer " + response.json()["access_token"]}
        checks.append("synthetic_admin_patient_login")
        doctor = client.post(
            "/api/admin/doctors",
            headers=headers["admin"],
            json={"name": "BS. Restore Drill", "specialty": "Synthetic verification"},
        )
        assert doctor.status_code == 201
        start = datetime.now(UTC) + timedelta(days=7)
        slot = client.post(
            "/api/admin/slots",
            headers=headers["admin"],
            json={
                "doctor_id": doctor.json()["id"],
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(minutes=30)).isoformat(),
            },
        )
        assert slot.status_code == 201
        checks.append("admin_doctor_and_slot_creation")
        body = {"slot_id": slot.json()["id"], "reminder_enabled": True}
        booking_headers = {**headers["patient"], "Idempotency-Key": "restore-" + marker}
        booked = client.post("/api/appointments", headers=booking_headers, json=body)
        assert booked.status_code == 201
        appointment_id = booked.json()["id"]
        replay = client.post("/api/appointments", headers=booking_headers, json=body)
        assert replay.status_code == 201 and replay.json() == booked.json()
        duplicate = client.post(
            "/api/appointments",
            headers={**headers["patient"], "Idempotency-Key": "other-" + marker},
            json=body,
        )
        assert duplicate.status_code == 409
        checks.extend(["booking_with_reminder", "idempotent_replay", "taken_slot_rejected"])
        cancelled = client.post(
            f"/api/appointments/{appointment_id}/cancel", headers=headers["patient"]
        )
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
        slots = client.get(
            f"/api/doctors/{doctor.json()['id']}/slots?include_unavailable=true",
            headers=headers["patient"],
        )
        assert (
            slots.status_code == 200
            and next(row for row in slots.json() if row["id"] == slot.json()["id"])["available"]
        )
        with session() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(OutboxEvent.appointment_id == appointment_id)
                )
                == 2
            )
        checks.extend(["cancellation_releases_slot", "two_transactional_outbox_events"])
    print(
        json.dumps(
            {
                "passed": True,
                "database": expected,
                "checks": checks,
                "notification_transport": "NOT_EXERCISED: only restored DB/API/outbox; no publisher, worker or SMTP in this drill",
                "synthetic_fixtures_only": True,
            }
        )
    )


if __name__ == "__main__":
    main()
