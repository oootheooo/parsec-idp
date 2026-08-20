# Deployment and Operations

## 1. Local Docker Compose

Required services:
- `postgres`
- `redis`
- `minio`
- `api`
- `worker`
- `frontend`

Optional:
- `minio-init` bucket creation
- `flower` only as optional developer profile

One command:
```bash
docker compose up --build
```

Then:
- frontend: `http://localhost:5173` or proxy port
- API docs: `http://localhost:8000/docs`
- MinIO console: documented dev port

## 2. Environment variables

Example categories:

```env
APP_ENV=development
APP_SECRET_KEY=
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173

DATABASE_URL=postgresql+asyncpg://...
DATABASE_SYNC_URL=postgresql+psycopg://...

REDIS_URL=redis://redis:6379/0

S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=handl-documents
S3_REGION=us-east-1
S3_FORCE_PATH_STYLE=true

JWT_SECRET=
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30

OPENAI_API_KEY=
OPENAI_EXTRACTION_MODEL=
OPENAI_SCHEMA_MODEL=
EXTRACTION_PROVIDER=mock

MAX_UPLOAD_BYTES=52428800
MAX_DOCUMENT_PAGES=200
SIGNED_URL_TTL_SECONDS=900

WEBHOOK_MASTER_KEY=
ALLOW_PRIVATE_WEBHOOK_URLS=true
```

Use separate sync DB URL if Celery/job libraries require sync DB access; otherwise stay async where possible.

## 3. Production topology

Reasonable initial deployment:
- frontend: Vercel/Cloudflare Pages/static host;
- API: container service (Cloud Run/ECS/Fly/etc.);
- worker: always-on or job-capable container compute;
- PostgreSQL: managed Postgres;
- Redis: managed Redis;
- S3-compatible object storage;
- secret manager.

Important: document parsing workers may need more RAM/CPU than API.

## 4. Worker queues

Recommended queues:
- `document_parse`
- `document_extract`
- `webhooks`
- `exports`

MVP can run them on one worker but route tasks by queue.

## 5. Concurrency

Parsing/OCR can be CPU/RAM heavy.
Set worker concurrency conservatively.

LLM extraction is I/O-heavy but rate-limited by provider.

Expose env-configurable:
- worker concurrency;
- task hard/soft time limit;
- provider concurrency.

## 6. Migrations

Deployment:
1. migrate DB;
2. deploy API;
3. deploy workers;
4. deploy frontend.

Provide `make migrate` or equivalent.

## 7. Health
- `/health`: process liveness
- `/ready`: DB + Redis + object storage (lightweight)

Worker health may be monitored via Celery inspect or dedicated heartbeat.

## 8. Structured logs

JSON in production.

Fields:
- timestamp
- level
- service
- request_id
- job_id
- workspace_id
- document_id
- event
- duration_ms
- error_code

No document contents.

## 9. Backup
- managed PostgreSQL backups;
- object storage versioning/backup policy where appropriate.

## 10. Retention
Provide config placeholders:
- original retention days;
- derived artifact retention days;
- audit retention.

MVP default: no automatic deletion until explicitly configured.

## 11. Provider outage behavior

If OpenAI unavailable:
- job transitions retrying;
- bounded retries;
- eventual failed state;
- user sees safe retry action.

Parsing result remains available and does not need rerun for extraction retry.

## 12. Cost controls

Record:
- pages;
- input/output tokens;
- model;
- provider latency;
- estimated cost if configured.

Enforce:
- max pages;
- max file size;
- configurable extraction context limits.
