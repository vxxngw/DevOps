"""Run an isolated full stack of previously built SHA images inside the CI agent."""

import argparse
import base64
import hashlib
import json
import re
import secrets
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

CLIENT = r"""
import json, os, time, uuid, urllib.request
base='http://frontend:8080'
headers={}
def call(method,path,payload=None,extra=None,url=None):
    h=dict(headers);h.update(extra or {})
    data=None if payload is None else json.dumps(payload).encode()
    if data is not None:h['Content-Type']='application/json'
    request=urllib.request.Request((url or base)+path,data=data,headers=h,method=method)
    with urllib.request.urlopen(request,timeout=5) as response:
        raw=response.read()
        return response.status,raw

def api(method,path,payload=None,extra=None):
    return json.loads(call(method,path,payload,extra)[1])

def wait(predicate):
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.5)
    raise AssertionError('Notification did not reach SENT before deadline')

health=[]
for service,port in [('api',8000),('publisher',8001),('worker',8002)]:
    for endpoint in ['health','ready','metrics']:
        deadline=time.monotonic()+30
        while True:
            try:
                status,body=call('GET','/'+endpoint,url='http://'+service+':'+str(port))
                assert status==200 and body
                health.append({'service':service,'endpoint':endpoint,'status':status,'bytes':len(body)})
                break
            except Exception:
                if time.monotonic()>deadline:raise
                time.sleep(.5)
page=call('GET','/');assert page[0]==200
login=api('POST','/api/auth/login',{'email':'patient@example.test','password':os.environ['DEMO_PASSWORD']})
headers['Authorization']='Bearer '+login['access_token']
doctors=api('GET','/api/doctors');assert doctors
slots=api('GET','/api/doctors/'+doctors[0]['id']+'/slots');assert slots
key=str(uuid.uuid4())
appointment=api('POST','/api/appointments',{'slot_id':slots[0]['id']},{'Idempotency-Key':key,'X-Request-ID':'sha-smoke-'+key})
identifier=appointment['id']
def sent():return api('GET','/api/appointments/'+identifier)['notification_status']=='SENT'
def email(kind):
    messages=json.loads(call('GET','/api/v1/messages',url='http://mailpit:8025')[1])['messages']
    return any(identifier in (detail:=json.loads(call('GET','/api/v1/message/'+m['ID'],url='http://mailpit:8025')[1])).get('Text','') and kind in detail.get('Text','') for m in messages[:50])
wait(sent);wait(lambda:email('BOOKED'))
api('POST','/api/appointments/'+identifier+'/cancel')
wait(sent);wait(lambda:email('CANCELLED'))
assert api('GET','/api/appointments/'+identifier)['status']=='CANCELLED'
print(json.dumps({'http_checks':health,'frontend_status':page[0],'appointment_id':identifier,'booking_email_body_matched':True,'cancellation_email_body_matched':True,'final_status':'CANCELLED','notification_status':'SENT','synthetic_patient':'patient@example.test'}))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--compose-base64", required=True)
    parser.add_argument("--images-base64", required=True)
    parser.add_argument("--verifier-sha256", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[a-f0-9]{40}", args.revision):
        raise ValueError("Require a full commit SHA")
    expected = json.loads(base64.b64decode(args.images_base64))
    if expected["commit"] != args.revision:
        raise ValueError("Image receipt belongs to another commit")
    kinds = {"app", "frontend", "postgres", "rabbitmq", "mailpit"}
    if set(expected["images"]) != kinds:
        raise ValueError("Require all five images")
    project = "clinic-sha-smoke-" + args.revision[:12] + "-" + uuid.uuid4().hex[:8]
    if not re.fullmatch(r"clinic-sha-smoke-[a-f0-9]{12}-[a-f0-9]{8}", project):
        raise ValueError("Unsafe project")
    root = Path("/home/jenkins/agent/runtime-smoke")
    work = root / project
    work.mkdir(parents=True, mode=0o700)
    if not work.resolve().is_relative_to(root.resolve()):
        raise ValueError("Unexpected work path")
    compose_source = base64.b64decode(args.compose_base64)
    (work / "compose.yaml").write_bytes(compose_source)
    passwords = [secrets.token_hex(24) for _ in range(2)]
    jwt, demo = secrets.token_hex(32), secrets.token_urlsafe(24)
    private_values = [*passwords, jwt, demo]
    environment = {
        "POSTGRES_PASSWORD": passwords[0],
        "RABBITMQ_PASSWORD": passwords[1],
        "JWT_SECRET": jwt,
        "DEMO_PASSWORD": demo,
        "ENVIRONMENT": "sha-runtime-smoke",
        "QUEUE_PREFIX": "clinic.dev",
        "SMTP_FROM": "clinic@example.test",
        "RETRY_SECONDS": "10,30,60",
        "REMINDER_LEAD_MINUTES": "60",
    }
    env_file = work / ".env"
    env_file.write_text("".join(k + "=" + v + "\n" for k, v in environment.items()))
    env_file.chmod(0o600)
    record = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "commit": args.revision,
        "project": project,
        "compose_source_sha256": hashlib.sha256(compose_source).hexdigest(),
        "verifier_sha256": args.verifier_sha256,
        "scope": "Original dev Compose, SHA image substitution and all published ports removed; unique test network/volumes in dedicated CI engine, no host dev changes",
        "commands": [],
    }
    logs = {}

    def run(command, log=None, check=True, input_text=None, timeout=240):
        result = subprocess.run(
            command,
            cwd=work,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        record["commands"].append({"command": command, "exit_code": result.returncode, "log": log})
        if log:
            output = result.stdout + result.stderr
            for value in private_values:
                output = output.replace(value, "[REDACTED]")
            logs[log] = output
        if check and result.returncode:
            raise RuntimeError("Command failed: " + (log or command[0]))
        return result

    source_prefix = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-p",
        project,
        "-f",
        str(work / "compose.yaml"),
    ]
    resolved = work / "runtime-private.json"
    prefix = ["docker", "compose", "--env-file", str(env_file), "-p", project, "-f", str(resolved)]
    created = False
    failure = None
    try:
        plan = json.loads(run(source_prefix + ["config", "--format", "json"]).stdout)
        for kind in ["volumes", "networks"]:
            for resource in plan.get(kind, {}).values():
                if resource.get("external") or not resource["name"].startswith(project + "_"):
                    raise ValueError("Refusing resources outside the unique test project")
        mapping = {name: "app" for name in ["api", "publisher", "worker", "migrate", "seed"]}
        mapping.update({name: name for name in ["frontend", "postgres", "rabbitmq", "mailpit"]})
        for service, configuration in plan["services"].items():
            kind = mapping[service]
            tag = f"ghcr.io/vxxngw/devops-{kind}:{args.revision}"
            if expected["images"][kind]["tag"] != tag:
                raise ValueError("Image tag does not match source SHA")
            configuration["image"] = tag
            configuration["pull_policy"] = "never"
            configuration.pop("ports", None)
            configuration.pop("build", None)
            if configuration.get("container_name"):
                raise ValueError("Fixed container names are forbidden")
        resolved.write_text(json.dumps(plan))
        resolved.chmod(0o600)
        created = True
        run(prefix + ["up", "-d", "--no-build", "--pull", "never", "--wait"], "up.log")
        ids = run(prefix + ["ps", "-aq"]).stdout.split()
        inspection = json.loads(run(["docker", "inspect", *ids]).stdout)
        services = []
        for container in inspection:
            service = container["Config"]["Labels"]["com.docker.compose.service"]
            kind = mapping[service]
            if container["Image"] != expected["images"][kind]["image_id"]:
                raise ValueError("Container image differs from scanned build receipt")
            state = container["State"]
            data = {
                "service": service,
                "image_id": container["Image"],
                "state": state["Status"],
                "health": state.get("Health", {}).get("Status"),
                "exit_code": state["ExitCode"],
            }
            if service in ["migrate", "seed"]:
                if data["state"] != "exited" or data["exit_code"] != 0:
                    raise ValueError("Migration or seed did not complete successfully")
            else:
                if data["state"] != "running" or data["health"] != "healthy":
                    raise ValueError("Long-running service not healthy: " + service)
                uid = int(run(prefix + ["exec", "-T", service, "id", "-u"]).stdout.strip())
                if uid == 0:
                    raise ValueError("Service running as root: " + service)
                data["uid"] = uid
            services.append(data)
        record["services"] = services
        if len(services) != 9:
            raise ValueError("Expected seven long-running services and two jobs")
        response = run(
            prefix + ["exec", "-T", "api", "python", "-"], "client.log", input_text=CLIENT
        )
        record["business_smoke"] = json.loads(response.stdout.strip().splitlines()[-1])
        json_logs = []
        for service in ["api", "publisher", "worker"]:
            result = run(prefix + ["logs", "--no-log-prefix", "--tail", "100", service])
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            parsed = 0
            for line in lines:
                try:
                    json.loads(line)
                    parsed += 1
                except json.JSONDecodeError:
                    pass
            json_logs.append({"service": service, "lines": len(lines), "json_lines": parsed})
            if not lines or parsed != len(lines):
                raise ValueError("Backend stdout is not entirely JSON: " + service)
        record["backend_json_logs"] = json_logs
    except Exception as exc:
        failure = type(exc).__name__ + ": " + str(exc)
    finally:
        if created:
            cleanup = run(
                prefix + ["down", "--volumes", "--remove-orphans"], "cleanup.log", check=False
            )
            record["cleanup_exit_code"] = cleanup.returncode
            if cleanup.returncode:
                failure = failure or "CleanupFailed"
            else:
                resolved.unlink(missing_ok=True)
                env_file.unlink(missing_ok=True)
        record["exit_code"] = 1 if failure else 0
        record["error"] = failure
        record["ended_at_utc"] = datetime.now(UTC).isoformat()
        record["public_logs"] = logs
        print(json.dumps(record), flush=True)
    return record["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
