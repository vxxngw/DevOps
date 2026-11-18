"""Exercise the real dev stack. --faults stops only clinic-dev RabbitMQ/worker, then restores."""

import argparse
import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--faults", action="store_true")
    args = parser.parse_args()
    root = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
        ),
        Path.cwd(),
    )
    values = dotenv_values(root / ".env")
    output = root / "docs/evidence" / ("runtime-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    output.mkdir(parents=True)
    metadata = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "commit": "UNCOMMITTED",
        "scope": "Compose frontend proxy -> FastAPI -> PostgreSQL -> RabbitMQ -> SMTP/Mailpit",
        "checks": [],
        "commands": [],
        "faults_requested": args.faults,
    }
    client = httpx.Client(
        base_url="http://localhost:" + values.get("FRONTEND_PORT", "18080"),
        timeout=15,
        trust_env=False,
    )
    cleanup = []
    metadata["created_appointments"] = cleanup
    worker_modified, broker_stopped = False, False

    def command(arguments):
        result = subprocess.run(
            ["docker", "compose", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        metadata["commands"].append(
            {
                "arguments": ["docker", "compose", *arguments],
                "at_utc": datetime.now(UTC).isoformat(),
                "exit_code": result.returncode,
                "output": result.stdout + result.stderr,
            }
        )
        if result.returncode:
            raise RuntimeError("Compose operation failed; see command evidence")

    def api(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def wait_for(predicate, timeout=45):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return
            except httpx.HTTPError:
                pass  # Bounded readiness wait tolerates transport resets during restarts.
            time.sleep(0.5)
        raise AssertionError("Condition not met before deadline")

    def book():
        doctors = api("GET", "/api/doctors")
        available = api("GET", f"/api/doctors/{doctors[0]['id']}/slots")
        if not available:
            raise AssertionError("Seed has no available slots")
        key = str(uuid.uuid4())
        result = api(
            "POST",
            "/api/appointments",
            json={"slot_id": available[0]["id"]},
            headers={"Idempotency-Key": key, "X-Request-ID": "runtime-" + key},
        )
        cleanup.append(result["id"])
        return result

    def sent(appointment_id):
        return api("GET", "/api/appointments/" + appointment_id)["notification_status"] == "SENT"

    try:
        login = api(
            "POST",
            "/api/auth/login",
            json={"email": "patient@example.test", "password": values["DEMO_PASSWORD"]},
        )
        client.headers["Authorization"] = "Bearer " + login["access_token"]
        first = book()
        wait_for(lambda: sent(first["id"]))
        messages = httpx.get(
            "http://localhost:8025/api/v1/messages", timeout=5, trust_env=False
        ).json()["messages"]
        email_found = False
        for message in messages[:50]:
            detail = httpx.get(
                "http://localhost:8025/api/v1/message/" + message["ID"], timeout=5, trust_env=False
            ).json()
            if first["id"] in detail.get("Text", "") and "BOOKED" in detail.get("Text", ""):
                email_found = True
                break
        assert email_found, "No matching appointment email body in Mailpit"
        metadata["checks"].append(
            {"name": "booking_email_body_and_sent", "appointment_id": first["id"]}
        )
        if args.faults:
            command(["up", "-d", "--wait", "--force-recreate", "--no-deps", "api"])
            wait_for(lambda: bool(api("GET", "/api/doctors")), timeout=20)
            metadata["checks"].append({"name": "frontend_proxy_recovers_api_recreation"})
            command(["stop", "rabbitmq"])
            broker_stopped = True
            assert (
                httpx.get("http://localhost:8000/ready", timeout=5, trust_env=False).status_code
                == 200
            )
            pending = book()
            with psycopg.connect(
                values["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1),
                connect_timeout=5,
            ) as db:
                row = db.execute(
                    "SELECT published_at FROM outbox_events WHERE appointment_id=%s",
                    (pending["id"],),
                ).fetchone()
                assert row is not None and row[0] is None
            assert not sent(pending["id"])
            for port in [8001, 8002]:
                assert (
                    httpx.get(
                        f"http://localhost:{port}/health", timeout=5, trust_env=False
                    ).status_code
                    == 200
                )
            command(["up", "-d", "--wait", "rabbitmq"])
            broker_stopped = False
            wait_for(lambda: sent(pending["id"]))
            metadata["checks"].append(
                {"name": "broker_stop_booking_outbox_recovery", "appointment_id": pending["id"]}
            )
            overlay = root / "tmp/worker-delay.yaml"
            overlay.write_text(
                "services:\n  worker:\n    environment:\n      WORKER_DELAY_SECONDS: '10'\n",
                encoding="utf-8",
            )
            worker_modified = True
            command(["-f", "compose.yaml", "-f", str(overlay), "up", "-d", "--wait", "worker"])
            crash = book()
            with httpx.Client(
                auth=("clinic", values["RABBITMQ_PASSWORD"]), timeout=5, trust_env=False
            ) as management:
                wait_for(
                    lambda: (
                        management.get(
                            "http://localhost:15673/api/queues/clinic-dev/clinic.dev.notifications"
                        )
                        .json()
                        .get("messages_unacknowledged", 0)
                        > 0
                    ),
                    timeout=20,
                )
            recovery_start = time.monotonic()
            command(["kill", "-s", "SIGKILL", "worker"])
            command(["up", "-d", "--wait", "worker"])
            worker_modified = False
            wait_for(lambda: sent(crash["id"]), timeout=150)
            metadata["checks"].append(
                {
                    "name": "worker_killed_before_ack_recovered",
                    "appointment_id": crash["id"],
                    "recovery_seconds": round(time.monotonic() - recovery_start, 3),
                }
            )
        for appointment_id in cleanup:
            api("POST", f"/api/appointments/{appointment_id}/cancel")
            wait_for(lambda: sent(appointment_id))
        metadata["checks"].append(
            {"name": "cancellation_email_sent_and_slots_released", "count": len(cleanup)}
        )
        metadata["exit_code"] = 0
    except Exception as exc:
        metadata["exit_code"], metadata["error_type"] = 1, type(exc).__name__
        if isinstance(exc, httpx.HTTPStatusError):
            metadata["http_error"] = {
                "method": exc.request.method,
                "path": exc.request.url.path,
                "status": exc.response.status_code,
            }
        # No request/auth objects or full DSNs written when an operation fails.
        print("Runtime smoke failed:", type(exc).__name__)
    finally:
        try:
            if broker_stopped:
                command(["up", "-d", "--wait", "rabbitmq"])
            if worker_modified:
                command(["up", "-d", "--wait", "worker"])
        except Exception as exc:
            metadata["cleanup_error_type"] = type(exc).__name__
            metadata["exit_code"] = 1
        if metadata.get("exit_code") == 1:
            for appointment_id in cleanup:
                try:
                    if api("GET", "/api/appointments/" + appointment_id)["status"] == "BOOKED":
                        api("POST", f"/api/appointments/{appointment_id}/cancel")
                except Exception as exc:
                    metadata.setdefault("cleanup_appointment_errors", []).append(
                        {"id": appointment_id, "error_type": type(exc).__name__}
                    )
        client.close()
        metadata["ended_at_utc"] = datetime.now(UTC).isoformat()
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("Runtime evidence:", output.relative_to(root), "exit", metadata["exit_code"])
    raise SystemExit(metadata["exit_code"])


if __name__ == "__main__":
    main()
