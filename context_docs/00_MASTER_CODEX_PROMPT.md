# HANDL Document Intelligence — Master Codex Execution Prompt

You are ChatGPT Codex acting as the principal engineer, product engineer, and implementation owner for **HANDL Document Intelligence**, a production-oriented intelligent document processing (IDP) platform.

Your job is to build the entire working application described by the files in this repository. Do not stop at scaffolding, pseudocode, mockups, or architectural discussion. Implement a coherent end-to-end application that can be run locally and deployed.

## Read these files first, in this order

1. `AGENTS.md`
2. `01_PRODUCT_CONTEXT.md`
3. `02_PRD.md`
4. `03_TECHNICAL_ARCHITECTURE.md`
5. `04_DATA_MODEL.md`
6. `05_API_SPEC.md`
7. `06_DOCUMENT_PROCESSING_SPEC.md`
8. `07_UX_UI_SPEC.md`
9. `08_SECURITY_PRIVACY.md`
10. `09_TEST_AND_ACCEPTANCE.md`
11. `10_DEPLOYMENT_AND_OPERATIONS.md`
12. `11_IMPLEMENTATION_PLAN.md`

Treat these documents as the source of truth. When there is a conflict, use this precedence:
`02_PRD.md` > `03_TECHNICAL_ARCHITECTURE.md` > specialized specs > `11_IMPLEMENTATION_PLAN.md`.

## Core mandate

Build a full-stack multi-tenant web application that allows a user to:

- create a workspace;
- create reusable "Processors";
- define or AI-generate a JSON extraction schema;
- upload PDFs, images, DOCX, XLSX, PPTX, HTML, CSV, and other supported document types;
- asynchronously parse/OCR the document;
- extract text, layout, tables, pages, and source evidence;
- use a multimodal LLM to return schema-conforming structured data;
- validate extracted values;
- compute per-field confidence and review status;
- show a document viewer alongside extracted fields;
- highlight the page/source region associated with an extracted value when coordinates exist;
- allow human correction and approval;
- persist an audit trail;
- export JSON and CSV;
- expose an API for programmatic uploads/extraction;
- support API keys;
- support webhook delivery of completed extraction results;
- implement simple workflow rules and exception routing;
- provide a dashboard for processing jobs and usage.

## Required technology

### Frontend
- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui-compatible component patterns
- React Hook Form + Zod
- PDF.js / react-pdf for PDF display
- Recharts only where charts are useful

### Backend
- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Celery worker
- Redis broker/result backend
- S3-compatible object storage
- Docling as the primary document conversion/layout extraction layer
- PyMuPDF as a PDF fallback/helper
- OpenAI Responses API through a provider abstraction for multimodal structured extraction

### Authentication
Implement email/password auth directly in the backend using:
- Argon2 password hashing
- JWT access tokens
- rotating refresh tokens stored hashed in PostgreSQL

Do not make the core local development experience depend on an external auth vendor.

## Architecture rules

1. The HTTP API must never perform heavy OCR or LLM extraction synchronously.
2. Upload endpoints persist metadata and enqueue jobs.
3. Processing must be idempotent and retryable.
4. Raw originals must remain immutable.
5. Parsed document representation must be stored separately from extracted business data.
6. Extraction result values must preserve provenance/evidence.
7. Each extraction run is immutable; corrections are stored as review overrides/revisions rather than silently overwriting model output.
8. Every tenant-owned row must carry `workspace_id` directly or through an unambiguous parent relationship.
9. Never trust model-generated confidence blindly. Confidence is a platform score based on evidence availability, parser quality, validation checks, and model self-assessment.
10. LLM integration must be behind an interface so a different provider/model can be added later.

## Initial UX target

The UI should feel like a modern B2B SaaS application.

Primary navigation:
- Dashboard
- Documents
- Processors
- Workflows
- API & Webhooks
- Settings

The critical screen is `/documents/:id/review`:
- left: page/document viewer;
- right: extracted structured fields;
- click a field -> navigate to page and highlight source bounding box if known;
- show confidence, validation status, source text, model value, reviewer override;
- allow edit, approve field, reject field, approve entire document;
- tables/arrays must be editable.

## Initial processor presets

Seed useful sample processor templates:
- Invoice
- Receipt
- Purchase Order
- Generic Contract Metadata
- Bank Statement Summary
- ID / Identity Document
- Custom Blank Processor

Do not hard-code product logic to these types. They are example schemas over a generic engine.

## Local development mandate

A developer must be able to run:

```bash
docker compose up --build
```

and get:
- PostgreSQL
- Redis
- MinIO
- FastAPI API
- Celery worker
- frontend

Provide `.env.example` files and a README with exact setup instructions.

The application should still boot without an OpenAI API key. In that state:
- parsing/OCR should work;
- LLM extraction jobs must fail gracefully with a clear configuration error;
- include a deterministic `MockExtractionProvider` for automated tests and demo/dev mode.

## Quality expectations

Implement:
- meaningful type safety;
- migrations;
- proper error handling;
- loading/empty/error states;
- form validation;
- API pagination;
- optimistic or responsive UI where appropriate;
- structured logging;
- health endpoints;
- unit tests;
- backend integration tests;
- frontend component/interaction tests for critical flows;
- at least one end-to-end happy path if practical.

Do not:
- leave TODOs for core requirements;
- substitute hard-coded demo results for real processing;
- put secrets in the repo;
- use an in-memory database for the actual application;
- couple the database schema to one document type;
- store only flattened text and throw away page/layout metadata.

## Implementation behavior

Before changing files:
1. inspect the repository;
2. produce an internal implementation plan;
3. create the project structure;
4. implement vertical slices that stay runnable.

Preferred vertical slice order:
1. infrastructure + auth + workspace;
2. processor CRUD/schema editor;
3. document upload/object storage;
4. background parsing;
5. extraction provider + extraction job;
6. document review UI;
7. validation/confidence;
8. API keys/webhooks;
9. workflow rules;
10. exports, dashboard, polish, tests.

When ambiguity remains, choose the simplest production-sensible option compatible with the specs and document that choice in `DECISIONS.md`.

## Definition of done

The project is done only when the acceptance criteria in `09_TEST_AND_ACCEPTANCE.md` pass and the README contains an end-to-end runbook.

At the end:
- run tests;
- run lint/type checks;
- run migrations from scratch;
- report what was implemented;
- list any genuinely unresolved limitations;
- do not claim features that are not working.
