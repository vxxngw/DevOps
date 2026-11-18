"""Create real synthetic bookings for queue/KEDA observation; explicit cleanup preserves a receipt."""

import argparse
import json
import ssl
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["burst", "cleanup"])
    parser.add_argument("--url", required=True)
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--ca-file", required=True)
    parser.add_argument("--email", default="smoke@example.test")
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    if (
        urlparse(args.url).scheme != "https"
        or urlparse(args.url).hostname != "staging.anuyen.test"
        or not args.email.endswith(".test")
        or not 1 <= args.count <= 200
    ):
        raise ValueError("Only trusted HTTPS staging/synthetic accounts; maximum200bookings")
    context = ssl.create_default_context(cafile=args.ca_file)
    base = args.url.rstrip("/")

    def request(path, data=None, token=None):
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": "load-" + uuid.uuid4().hex,
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        query = urllib.request.Request(
            base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=headers,
        )
        with urllib.request.urlopen(query, context=context, timeout=15) as response:
            return json.load(response)

    token = request(
        "/api/auth/login",
        {"email": args.email, "password": Path(args.password_file).read_text().strip()},
    )["access_token"]
    if args.action == "cleanup":
        receipt = json.loads(Path(args.receipt).read_text())
        if receipt["url"] != base:
            raise ValueError("Receipt belongs to another endpoint")
        for identifier in receipt["appointments"]:
            uuid.UUID(identifier)
            request("/api/appointments/" + identifier + "/cancel", {}, token)
        print(
            json.dumps(
                {
                    "cancelled": len(receipt["appointments"]),
                    "note": "Cancellation creates additional events; wait for queue to drain again",
                }
            )
        )
        return
    slots = []
    for doctor in request("/api/doctors", token=token):
        slots += [
            item
            for item in request("/api/doctors/" + doctor["id"] + "/slots", token=token)
            if item.get("available") is True
        ]
    if len(slots) < args.count:
        raise RuntimeError("Not enough synthetic future slots; no burst started")
    folder = ROOT / ".infra-local/load"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("queue-" + uuid.uuid4().hex + ".json")
    receipt = {"url": base, "appointments": [], "scope": "Actual bookings; not queue/scaling proof"}
    try:
        for slot in slots[: args.count]:
            receipt["appointments"].append(
                request(
                    "/api/appointments", {"slot_id": slot["id"], "reminder_enabled": False}, token
                )["id"]
            )
    finally:
        path.write_text(json.dumps(receipt, indent=2))
        print("Booking receipt:", path)
    print(
        json.dumps(
            {
                "created": len(receipt["appointments"]),
                "note": "Observe queue/replicas before explicit cleanup; no KEDA success inferred",
            }
        )
    )


if __name__ == "__main__":
    main()
