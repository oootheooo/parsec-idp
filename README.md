# Parsec

Parsec is a multi-tenant document intelligence application that turns PDFs, images, Office files, and text documents into schema-conforming, evidence-backed data with validation and human review.

## Run locally

Prerequisite: Docker Desktop with Compose v2.

```bash
docker compose up --build
```

No `.env` file is required for the first run; Compose loads safe development defaults from `.env.example`. To customize configuration:

```bash
cp .env.example .env
```

Open:

- Parsec web app: http://localhost:5173
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/health
- MinIO console: http://localhost:9001 (`minioadmin` / `minioadmin` in the default local configuration)

The API container applies Alembic migrations and seeds seven processor presets on startup. Register a user in the web app; registration creates the first workspace and owner membership.

## End-to-end runbook

1. Register at `/register`.
2. Open **Processors**, create from Invoice or another preset, review the schema, and publish it.
3. Open **Documents → Upload**, select the published processor, and upload a supported file.
4. The HTTP request returns in the queued state. The Celery worker parses with Docling (with PyMuPDF helpers/fallback), extracts through the configured provider, validates, and calculates confidence.
5. When the status becomes **Review required**, open **Review**. Select a field to navigate to its evidence page and bounding box when geometry exists.
6. Correct or approve fields. Corrections are stored as overrides; the immutable model result remains available.
7. Approve the document, then export effective JSON or CSV.
8. Use **API & Webhooks** to create a one-time-visible API key or signed webhook endpoint.

The default `EXTRACTION_PROVIDER=mock` is deterministic and costs nothing. To use OpenAI, set:

```env
EXTRACTION_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_EXTRACTION_MODEL=your-structured-output-model
OPENAI_SCHEMA_MODEL=your-schema-model
```

Without an OpenAI key, parsing still works and an OpenAI extraction attempt ends with a safe `PROVIDER_NOT_CONFIGURED` error.

## Supported uploads

PDF, PNG, JPEG, TIFF, WEBP, DOCX, XLSX, PPTX, HTML, CSV, Markdown, and plain text. Upload size and page limits are configurable. Originals use generated private object keys and short-lived signed downloads.

## Architecture

- `frontend/`: React, TypeScript, Vite, React Router, TanStack Query, React Hook Form/Zod, Tailwind, react-pdf.
- `backend/`: FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL, Celery/Redis, S3/MinIO, Docling/PyMuPDF, provider abstraction.
- `context_docs/`: product and engineering source specifications.

Parsing and AI calls never run in the HTTP process. Processor publications and extraction runs are immutable. All tenant resources are scoped through an authenticated workspace context.

## API quick start

Create an API key in the UI, then:

```bash
curl -X POST 'http://localhost:8000/api/v1/documents/upload?processor_id=<processor-uuid>' \
  -H 'Authorization: Bearer psc_live_…' \
  -F 'file=@invoice.pdf'
```

Poll `GET /api/v1/documents/{id}/status`, then retrieve the extraction or approved export. Browser JWT calls additionally send `X-Workspace-ID`; API keys resolve their workspace automatically.

## Development and quality gates

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check app tests
.venv/bin/mypy app
.venv/bin/pytest
```

Frontend (Node 22 recommended):

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Migration bootstrap:

```bash
cd backend
alembic upgrade head
python -m app.seed
```

Health endpoints are `/health` and `/ready`. Webhooks use `X-Parsec-*` headers with an HMAC SHA-256 signature over `{timestamp}.{raw_body}` and are delivered without redirects.

## Operational notes

- Set strong `APP_SECRET_KEY`, `JWT_SECRET`, MinIO/S3 credentials, and `WEBHOOK_MASTER_KEY` in production.
- Set `ALLOW_PRIVATE_WEBHOOK_URLS=false` in production to block loopback, private, link-local, reserved, and multicast targets.
- Use HTTPS and production CORS origins.
- Parsing workers need more CPU/RAM than the API and should use conservative concurrency.
- Document contents, tokens, API keys, and raw extracted payloads are not logged.

## Current limits

- Evidence geometry depends on the source format and parser output; the UI degrades to page/quote evidence without inventing boxes.
- The visual schema and workflow builders intentionally expose the supported MVP subset; raw JSON Schema editing remains available.
- OCR quality depends on Docling’s configured local OCR backend. Specialized handwriting guarantees and legacy binary Office formats are outside MVP scope.

