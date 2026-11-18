"""Create local synthetic-dev credentials without printing secrets or overwriting .env."""

import secrets
from pathlib import Path

root = next(
    p
    for p in Path(__file__).resolve().parents
    if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
)
path = root / ".env"
if path.exists():
    raise SystemExit(".env already exists; left unchanged")
db_password, broker_password = secrets.token_hex(24), secrets.token_hex(24)
path.write_text(
    f"POSTGRES_PASSWORD={db_password}\nRABBITMQ_PASSWORD={broker_password}\n"
    f"DATABASE_URL=postgresql+psycopg://clinic:{db_password}@localhost:5433/clinic\n"
    f"RABBITMQ_URL=amqp://clinic:{broker_password}@localhost:5673/clinic-dev\n"
    f"JWT_SECRET={secrets.token_hex(32)}\nDEMO_PASSWORD={secrets.token_urlsafe(18)}\n"
    "ENVIRONMENT=development\nQUEUE_PREFIX=clinic.dev\nSMTP_HOST=localhost\nSMTP_PORT=1025\n"
    "SMTP_FROM=clinic@example.test\nRETRY_SECONDS=10,30,60\nREMINDER_LEAD_MINUTES=60\n",
    encoding="utf-8",
)
print("Created .env with random local-only credentials. Read it locally; do not commit/share it.")
