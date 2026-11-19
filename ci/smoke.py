"""Real HTTPS appointment/email smoke for a configured Mốc3 namespace; no mock success."""

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from ci.common import OUTPUT, read_json, run, write_json


def mailpit_job(namespace, appointment_id, image):
    script = """import json,time,urllib.request
for attempt in range(15):
    with urllib.request.urlopen('http://mailpit:8025/api/v1/messages?limit=200',timeout=5) as response:
        inbox=json.load(response)
    if any(MARKER in item.get('Subject','') for item in inbox.get('messages',[])):
        print(json.dumps({'mailpit_receipt':True,'appointment_marker':MARKER}));break
    time.sleep(1)
else:
    raise RuntimeError('No matching email in the real Mailpit inbox')
""".replace("MARKER", repr(appointment_id[:8]))
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": "clinic-mail-check-" + uuid.uuid4().hex[:10], "namespace": namespace},
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 60,
            "ttlSecondsAfterFinished": 1800,
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/name": "mail-check"}},
                "spec": {
                    "restartPolicy": "Never",
                    "serviceAccountName": "clinic-app",
                    "automountServiceAccountToken": False,
                    "imagePullSecrets": [{"name": "registry-pull"}],
                    "securityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 10001,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [
                        {
                            "name": "check",
                            "image": image,
                            "command": ["python", "-c", script],
                            "resources": {
                                "requests": {"cpu": "50m", "memory": "64Mi"},
                                "limits": {"cpu": "250m", "memory": "128Mi"},
                            },
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]},
                                "readOnlyRootFilesystem": True,
                            },
                        }
                    ],
                },
            },
        },
    }


def verify_mailpit(namespace, appointment_id):
    manifest = read_json(OUTPUT / "release-manifest.json")
    image = manifest["images"]["app"]["reference"]
    job = mailpit_job(namespace, appointment_id, image)
    path = OUTPUT / (namespace + "-mail-check.json")
    write_json(path, job)
    run(
        ["kubectl", "-n", namespace, "create", "-f", path],
        log=OUTPUT / (namespace + "-mail-check-create.log"),
    )
    target = "job/" + job["metadata"]["name"]
    result = run(
        ["kubectl", "-n", namespace, "wait", "--for=condition=Complete", target, "--timeout=75s"],
        check=False,
        log=OUTPUT / (namespace + "-mail-check-wait.log"),
    )
    logs = run(
        ["kubectl", "-n", namespace, "logs", target],
        log=OUTPUT / (namespace + "-mail-check-result.log"),
    )
    if result.returncode or not any(
        json.loads(line).get("mailpit_receipt") is True
        for line in logs.stdout.splitlines()
        if line.startswith("{")
    ):
        raise RuntimeError("Mailpit receipt verification failed; SENT alone is not enough")


def smoke(namespace):
    base = os.environ.get("CLINIC_SMOKE_URL", "").rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("Set CLINIC_SMOKE_URL to the trusted HTTPS URL of the namespace")
    password = os.environ.get("CLINIC_SMOKE_PASSWORD")
    email = os.environ.get("CLINIC_SMOKE_EMAIL")
    if not password or not email or not email.endswith(".test"):
        raise ValueError("Provide a synthetic .test smoke account through Jenkins Credentials")
    context = ssl.create_default_context(cafile=os.environ.get("CLINIC_SMOKE_CA_FILE"))

    def request(path, *, data=None, token=None, key=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if key:
            headers["Idempotency-Key"] = key
        body = json.dumps(data).encode() if data is not None else None
        query = urllib.request.Request(base + path, data=body, headers=headers)
        try:
            with urllib.request.urlopen(query, timeout=15, context=context) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Smoke HTTP{error.code}; response body and credentials withheld"
            ) from None

    token = request("/api/auth/login", data={"email": email, "password": password})["access_token"]
    doctors = request("/api/doctors", token=token)
    selected = None
    for doctor in doctors:
        slots = request(
            "/api/doctors/" + urllib.parse.quote(doctor["id"], safe="") + "/slots", token=token
        )
        selected = next((slot for slot in slots if slot.get("available") is True), None)
        if selected:
            break
    if not selected:
        raise RuntimeError("No synthetic future slot available for smoke")
    appointment = request(
        "/api/appointments",
        data={"slot_id": selected["id"], "reminder_enabled": False},
        token=token,
        key="smoke-" + uuid.uuid4().hex,
    )
    try:
        for _ in range(30):
            state = request("/api/appointments/" + appointment["id"], token=token)
            if state["notification_status"] == "SENT":
                verify_mailpit(namespace, appointment["id"])
                print(
                    json.dumps(
                        {
                            "namespace": namespace,
                            "appointment_id": appointment["id"],
                            "notification_status": "SENT",
                            "scope": "Booking notification accepted and found in real internal Mailpit inbox; no external mailbox claim",
                        }
                    )
                )
                break
            if state["notification_status"] == "FAILED_DLQ":
                raise RuntimeError("Notification entered DLQ")
            time.sleep(2)
        else:
            raise TimeoutError("Notification did not reach SENT within60seconds")
    finally:
        request("/api/appointments/" + appointment["id"] + "/cancel", data={}, token=token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("namespace", choices=["staging", "production"])
    smoke(parser.parse_args().namespace)
