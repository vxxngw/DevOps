"""Exercise real dev pg_dump/restore without replacing or writing to the source DB.

Uses the existing local clinic-dev PostgreSQL and the current Python environment.
Private dumps stay in .infra-local; public evidence contains only aggregates/hashes.
"""

import csv
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import URL

ROOT = next(
    path
    for path in Path(__file__).resolve().parents
    if (path / "Jenkinsfile").is_file() and (path / "pyproject.toml").is_file()
)
sys.path.insert(0, str(ROOT))
from ci.backup_schema import canonical_schema_definition  # noqa: E402
from ci.bash_sources import bash_executable  # noqa: E402

SCHEMA_SQL = """
    SELECT t.relname || '.' || c.conname || ':' || pg_get_constraintdef(c.oid, true)
    FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' ORDER BY 1;
    SELECT tablename || '.' || indexname || ':' || indexdef
    FROM pg_indexes WHERE schemaname='public' ORDER BY 1;
"""


class Drill:
    def __init__(self):
        self.identifier = uuid.uuid4().hex[:20]
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.evidence = ROOT / "docs/evidence" / f"backup-restore-{stamp}"
        self.private = ROOT / ".infra-local/db-backups" / self.identifier
        self.container = "clinic-dev-postgres-1"
        self.target = "clinic_restore_" + self.identifier
        self.env = os.environ.copy()
        self.env.update(
            CLINIC_BACKUP_ROOT=self.private.as_posix(),
            CLINIC_BACKUP_CONTAINER=self.container,
            CLINIC_BACKUP_RETENTION_DAYS="7",
        )
        values = dotenv_values(ROOT / ".env")
        self.redactions = [
            value
            for key, value in values.items()
            if value and any(word in key for word in ["PASSWORD", "SECRET", "TOKEN", "URL"])
        ]
        self.values = values
        self.records = []
        self.owned = set()
        self.summary = {
            "status": "RUNNING",
            "started_at": datetime.now(UTC).isoformat(),
            "scope": "Local existing Docker dev PostgreSQL; separate restored DB; current source API via native Python TestClient",
            "not_verified": [
                "systemd/cron timer execution",
                "VM/Ansible convergence or idempotency",
                "Kubernetes/staging/production restore",
                "offsite backup and disaster RPO/RTO",
                "RabbitMQ/worker/SMTP notification delivery in this drill",
            ],
        }

    def safe(self, value):
        for secret in self.redactions:
            value = value.replace(secret, "[REDACTED]")
        return value

    def execute(self, label, arguments, *, stdin=None, env=None, required=True):
        started = time.perf_counter()
        try:
            result = subprocess.run(
                arguments,
                cwd=ROOT,
                env=env or self.env,
                input=stdin,
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as error:
            result = subprocess.CompletedProcess(
                arguments, 124, error.stdout or b"", (error.stderr or b"") + b"\nTimed out"
            )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        for line in stdout.splitlines():
            if line.startswith('{"event":"restore_database_created"'):
                database = json.loads(line)["database"]
                if database != self.target:
                    raise ValueError("Unexpected database creation marker")
                self.owned.add(database)
        log = self.safe(stdout + ("\nSTDERR:\n" + stderr if stderr else ""))
        (self.evidence / f"{label}.log").write_text(log, encoding="utf-8")
        self.records.append(
            {
                "check": label,
                "command": self.safe(subprocess.list2cmdline([str(arg) for arg in arguments])),
                "exit_code": result.returncode,
                "duration_seconds": round(time.perf_counter() - started, 3),
                "log": f"{label}.log",
            }
        )
        if required and result.returncode:
            raise RuntimeError(f"{label} failed (exit {result.returncode}); see sanitized evidence")
        return result

    def sql(self, database, statement, label):
        return (
            self.execute(
                label,
                [
                    "docker",
                    "exec",
                    "-i",
                    "--user",
                    "postgres",
                    self.container,
                    "sh",
                    "-ec",
                    'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -X -qAt -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1',
                    "sh",
                    database,
                ],
                stdin=statement.encode(),
            )
            .stdout.decode()
            .strip()
        )

    def exists(self, database, label):
        if not re.fullmatch(r"clinic_restore_[a-f0-9]{20}", database):
            raise ValueError("Unsafe target database")
        return (
            self.sql(
                "postgres", f"SELECT count(*) FROM pg_database WHERE datname='{database}';", label
            )
            == "1"
        )

    def shell(self, label, name, args, *, required=True):
        return self.execute(
            label,
            [bash_executable(), (ROOT / "scripts/infra" / name).as_posix(), *args],
            required=required,
        )

    def private_directory(self):
        self.private.mkdir(parents=True, exist_ok=False)
        if os.name == "nt":
            identity = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"])
            sid = next(csv.reader(io.StringIO(identity.decode().strip())))[1]
            if not re.fullmatch(r"S-1-[0-9-]+", sid):
                raise ValueError("Cannot identify the current Windows user for private backups")
            self.execute(
                "private-backup-acl",
                [
                    "icacls",
                    str(self.private),
                    "/inheritance:r",
                    "/grant:r",
                    f"*{sid}:(OI)(CI)F",
                    "*S-1-5-18:(OI)(CI)F",
                ],
            )
        else:
            self.private.chmod(0o700)

    def run(self):
        self.evidence.mkdir(parents=True, exist_ok=False)
        before = None
        try:
            self.private_directory()
            endpoint = (
                self.execute(
                    "docker-endpoint",
                    ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                )
                .stdout.decode()
                .strip()
            )
            if not self.env.get("DOCKER_HOST", endpoint).startswith(("unix://", "npipe://")):
                raise ValueError("Only a local Docker engine is allowed")
            identity = (
                self.execute(
                    "postgres-identity",
                    [
                        "docker",
                        "inspect",
                        "--format",
                        '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Running}}',
                        self.container,
                    ],
                )
                .stdout.decode()
                .strip()
            )
            if identity != "clinic-dev|postgres|true":
                raise ValueError("Expected the running clinic-dev Postgres service")
            source = self.sql(
                "postgres", "SELECT current_user; SHOW server_version;", "postgres-version"
            ).splitlines()
            user, version = source
            # The dev service declares POSTGRES_DB=clinic; query the container, never all its env.
            database = (
                self.execute(
                    "source-database-name",
                    ["docker", "exec", self.container, "printenv", "POSTGRES_DB"],
                )
                .stdout.decode()
                .strip()
            )
            if not re.fullmatch(r"[a-zA-Z0-9_]+", database) or database.startswith(
                "clinic_restore_"
            ):
                raise ValueError("Unexpected source database")
            size = int(
                self.sql(database, "SELECT pg_database_size(current_database());", "source-size")
            )
            free = shutil.disk_usage(self.private).free
            if size > 128 * 1024**2 or free < 5 * size + 2 * 1024**3:
                raise ValueError("Insufficient space or source too large for this small dev drill")
            self.summary.update(
                source_database=database,
                postgres_version=version,
                source_database_bytes=size,
                backup_drive_free_bytes=free,
                git_base=self.execute(
                    "git-base",
                    ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
                )
                .stdout.decode()
                .strip(),
                working_tree_uncommitted=bool(
                    self.execute(
                        "git-status",
                        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "status", "--porcelain"],
                    ).stdout.strip()
                ),
            )
            if self.exists(self.target, "target-absent-before"):
                raise ValueError("Restore target already exists; nothing will be replaced")
            fingerprint_sql = (ROOT / "scripts/dev/backup-fingerprint.sql").read_text()
            before = self.sql(database, fingerprint_sql, "source-fingerprint-before")
            source_schema = canonical_schema_definition(
                self.sql(database, SCHEMA_SQL, "source-schema")
            )
            self.shell("backup-first", "backup.sh", ["dev"])
            artifacts = sorted((self.private / "dev").glob("*.dump"))
            if len(artifacts) != 1 or artifacts[0].read_bytes()[:5] != b"PGDMP":
                raise ValueError("Expected exactly one real PostgreSQL custom-format dump")
            artifact = artifacts[0]
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if artifact.with_suffix(".dump.sha256").read_text().split()[0] != digest:
                raise ValueError("Backup checksum mismatch")
            self.summary["backup"] = {
                "filename": artifact.name,
                "bytes": artifact.stat().st_size,
                "sha256": digest,
            }
            # Retention fixtures are copies inside this run's private directory only.
            old = artifact.with_name("clinic-dev-20000101T000000Z.dump")
            shutil.copyfile(artifact, old)
            sidecar = old.with_suffix(".dump.sha256")
            sidecar.write_text(digest + "  " + old.name + "\n")
            sentinel = old.with_name("unrelated-file.keep")
            sentinel.write_text("Retention must preserve unrelated files.\n")
            stale = time.time() - 10 * 86400
            for path in [old, sidecar, sentinel]:
                os.utime(path, (stale, stale))
            time.sleep(1.1)  # Artifact names have second resolution.
            self.shell("backup-retention", "backup.sh", ["dev"])
            if old.exists() or sidecar.exists() or not sentinel.exists() or not artifact.exists():
                raise ValueError("Retention affected the wrong files")
            self.summary["retention"] = (
                "PASS: stale scoped dump/checksum removed; unrelated and fresh files retained"
            )
            if self.sql(database, fingerprint_sql, "source-fingerprint-after-backups") != before:
                raise ValueError(
                    "Source changed during backups; cannot claim an exact snapshot comparison"
                )
            started = time.perf_counter()
            self.shell(
                "restore-new-database", "restore.sh", ["dev", artifact.as_posix(), self.target]
            )
            if self.sql(self.target, fingerprint_sql, "restored-fingerprint") != before:
                raise ValueError("Restored table data fingerprints differ")
            restored_schema = canonical_schema_definition(
                self.sql(self.target, SCHEMA_SQL, "restored-schema")
            )
            if source_schema != restored_schema:
                raise ValueError(
                    "Restored constraint/index definitions differ after narrow cast normalization"
                )
            self.summary["schema"] = {
                "definitions": len(source_schema.splitlines()),
                "canonical_sha256": hashlib.sha256(source_schema.encode()).hexdigest(),
                "normalization": "Only equivalent unbounded varchar-array-to-text casts; values/operators/typmods/other types preserved",
            }
            self.summary["fingerprint_match"] = True
            self.summary["fingerprints"] = [line.split("\t") for line in before.splitlines()]
            again = self.shell(
                "reject-existing-database",
                "restore.sh",
                ["dev", artifact.as_posix(), self.target],
                required=False,
            )
            if (
                again.returncode == 0
                or self.sql(self.target, fingerprint_sql, "existing-target-unchanged") != before
            ):
                raise ValueError("Existing database protection failed")
            corrupt = artifact.with_name("clinic-dev-20000102T000000Z.dump")
            shutil.copyfile(artifact, corrupt)
            corrupt.with_suffix(".dump.sha256").write_text(digest + "  " + corrupt.name + "\n")
            with corrupt.open("ab") as stream:
                stream.write(b"corrupt-checksum-fixture")
            negative_db = "clinic_restore_" + uuid.uuid4().hex[:20]
            bad = self.shell(
                "reject-corrupt-backup",
                "restore.sh",
                ["dev", corrupt.as_posix(), negative_db],
                required=False,
            )
            if bad.returncode == 0 or self.exists(negative_db, "corrupt-target-remains-absent"):
                raise ValueError("Corrupt backup guard failed")
            metrics = self.private / "metrics"
            if (
                'namespace="dev"} 1'
                not in (metrics / "clinic-backup-last-run-dev.prom").read_text()
            ):
                raise ValueError("Successful backup status metric missing")
            self.summary["negative_checks"] = [
                "existing database rejected and unchanged",
                "corrupt checksum rejected before database creation",
            ]
            ports = json.loads(
                self.execute(
                    "postgres-loopback-binding",
                    [
                        "docker",
                        "inspect",
                        "--format",
                        '{{json (index .NetworkSettings.Ports "5432/tcp")}}',
                        self.container,
                    ],
                ).stdout
            )
            binding = next(item for item in ports if item["HostIp"] == "127.0.0.1")
            password = self.values["POSTGRES_PASSWORD"]
            self.redactions.append(password)
            smoke_env = self.env.copy()
            smoke_env.update(
                ENVIRONMENT="test",
                CLINIC_RESTORE_DB=self.target,
                PYTHONPATH=str(ROOT / "services"),
                JWT_SECRET=secrets.token_hex(32),
                DATABASE_URL=URL.create(
                    "postgresql+psycopg",
                    username=user,
                    password=password,
                    host="127.0.0.1",
                    port=int(binding["HostPort"]),
                    database=self.target,
                ).render_as_string(hide_password=False),
                RABBITMQ_URL="amqp://unused:unused@127.0.0.1:1/restore-no-consumer",
            )
            self.redactions.extend([smoke_env["JWT_SECRET"], smoke_env["DATABASE_URL"]])
            smoke = self.execute(
                "restored-business-smoke",
                [sys.executable, str(ROOT / "scripts/dev/restore-db-smoke.py")],
                env=smoke_env,
            )
            self.summary["business_smoke"] = json.loads(smoke.stdout.decode().splitlines()[-1])
            self.summary["dev_restore_to_business_seconds"] = round(
                time.perf_counter() - started, 3
            )
            self.summary["status"] = "PASS"
        except Exception as error:
            self.summary.update(status="FAIL", error=self.safe(str(error)))
        finally:
            dropped = []
            try:
                if before is not None:
                    unchanged = (
                        self.sql(database, fingerprint_sql, "source-fingerprint-final") == before
                    )
                    self.summary["source_unchanged"] = unchanged
                    if not unchanged:
                        self.summary["status"] = "FAIL"
            except Exception as error:
                self.summary.update(status="FAIL", source_check_error=self.safe(str(error)))
            try:
                for owned in self.owned:
                    if owned != self.target or not re.fullmatch(
                        r"clinic_restore_[a-f0-9]{20}", owned
                    ):
                        raise ValueError("Refusing cleanup of an unowned database")
                    self.execute(
                        "drop-owned-restore-database",
                        [
                            "docker",
                            "exec",
                            "--user",
                            "postgres",
                            self.container,
                            "sh",
                            "-ec",
                            'export PGPASSWORD="$POSTGRES_PASSWORD"; exec dropdb -U "$POSTGRES_USER" --force "$1"',
                            "sh",
                            owned,
                        ],
                    )
                    if self.exists(owned, "owned-target-absent-after-cleanup"):
                        raise ValueError("Owned restore database cleanup failed")
                    dropped.append(owned)
                self.summary["cleanup"] = {
                    "status": "PASS",
                    "owned_databases_dropped": dropped,
                    "private_dumps": "retained; never committed",
                }
            except Exception as error:
                self.summary.update(status="FAIL", cleanup=self.safe(str(error)))
            self.summary.update(
                finished_at=datetime.now(UTC).isoformat(),
                commands=self.records,
                private_artifact_directory=self.private.relative_to(ROOT).as_posix(),
                source_files={
                    path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in [
                        Path(__file__),
                        ROOT / "scripts/dev/restore-db-smoke.py",
                        ROOT / "scripts/dev/backup-fingerprint.sql",
                        ROOT / "ci/backup_schema.py",
                        *[
                            ROOT / "scripts/infra" / name
                            for name in ["backup.sh", "restore.sh", "backup-common.sh"]
                        ],
                    ]
                },
            )
            (self.evidence / "metadata.json").write_text(
                json.dumps(self.summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(
            json.dumps(
                {
                    "status": self.summary["status"],
                    "evidence": self.evidence.relative_to(ROOT).as_posix(),
                    "cleanup": self.summary.get("cleanup"),
                },
                ensure_ascii=False,
            )
        )
        return 0 if self.summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(Drill().run())
