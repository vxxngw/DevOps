import fs from 'node:fs';
import crypto from 'node:crypto';

const envPath = '.env';
if (fs.existsSync(envPath)) {
  console.log('.env already exists; left unchanged');
} else {
  const dbPassword = crypto.randomBytes(24).toString('hex');
  const brokerPassword = crypto.randomBytes(24).toString('hex');
  const jwtSecret = crypto.randomBytes(32).toString('hex');
  const demoPassword = crypto.randomBytes(18).toString('base64url');

  const content = [
    `POSTGRES_PASSWORD=${dbPassword}`,
    `RABBITMQ_PASSWORD=${brokerPassword}`,
    `DATABASE_URL=postgresql+psycopg://clinic:${dbPassword}@localhost:5433/clinic`,
    `RABBITMQ_URL=amqp://clinic:${brokerPassword}@localhost:5673/clinic-dev`,
    `JWT_SECRET=${jwtSecret}`,
    `DEMO_PASSWORD=${demoPassword}`,
    'ENVIRONMENT=development',
    'QUEUE_PREFIX=clinic.dev',
    'SMTP_HOST=localhost',
    'SMTP_PORT=1025',
    'SMTP_FROM=clinic@example.test',
    'RETRY_SECONDS=10,30,60',
    'REMINDER_LEAD_MINUTES=60',
    ''
  ].join('\n');

  fs.writeFileSync(envPath, content, { encoding: 'utf-8' });
  console.log('Created .env with random local-only credentials. Read it locally; do not commit/share it.');
}
