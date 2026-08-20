# Technical Architecture

## 1. Chosen stack

### Frontend
- React + TypeScript + Vite
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui patterns
- React Hook Form + Zod
- react-pdf / PDF.js
- Recharts for dashboard charts

Why:
- clean SPA architecture;
- fast development;
- backend remains the authoritative API;
- simpler than introducing a second server framework.

### API backend
- FastAPI
- Pydantic v2
- SQLAlchemy 2 async
- asyncpg
- Alembic
- PostgreSQL

### Async jobs
- Celery
- Redis

Heavy OCR/model work must not run in the web process.

### Object storage
- S3-compatible
- MinIO locally
- AWS S3 / Cloudflare R2 / other S3-compatible provider in production

### Document parsing
Primary:
- Docling

Helpers/fallback:
- PyMuPDF
- Pillow
- optional LibreOffice conversion only when necessary for legacy Office formats

Docling is appropriate because it creates a unified document representation, supports OCR and table structure extraction, and supports many document formats.

### AI
Provider interface:
- `ExtractionProvider`
- `SchemaGenerationProvider`

Initial implementation:
- OpenAI Responses API
- structured JSON schema output
- multimodal page/file inputs as required

Test/dev:
- deterministic mock provider.

## 2. System diagram

```text
Browser
  |
  v
React SPA
  |
  | HTTPS / REST
  v
FastAPI --------------------------------> PostgreSQL
  |                                         |
  | presigned upload                        | metadata/results/audit
  v                                         |
S3/MinIO                                    |
  ^                                         |
  |                                         |
  +--------- Celery Worker <---- Redis -----+
               |
               +--> Docling / OCR
               |
               +--> page rendering / evidence mapping
               |
               +--> OpenAI provider
               |
               +--> validation + confidence
               |
               +--> derived artifacts to object storage
```

## 3. Processing pipeline

```text
UPLOAD
  -> checksum & metadata
  -> enqueue process_document(document_id)

PARSE
  -> fetch immutable original
  -> Docling conversion
  -> canonical document JSON
  -> page images/thumbnails as needed
  -> persist parse run

EXTRACT
  -> load processor version
  -> select relevant parsed representation
  -> send structured extraction request
  -> persist immutable extraction run

EVIDENCE
  -> map model evidence references to page blocks/bboxes
  -> persist extraction fields/evidence

VALIDATE
  -> JSON schema validation
  -> declarative business rules
  -> confidence calculation

DECIDE
  -> review required OR complete/auto-approved
  -> dispatch webhook events
```

## 4. Canonical document representation

Do not couple internal storage directly to Docling classes.

Create application-owned Pydantic models:

```python
CanonicalDocument:
  version: str
  page_count: int
  mime_type: str
  title: str | None
  text: str
  markdown: str | None
  pages: list[CanonicalPage]
  tables: list[CanonicalTable]
  metadata: dict

CanonicalPage:
  page_number: int
  width: float | None
  height: float | None
  text: str
  blocks: list[CanonicalBlock]

CanonicalBlock:
  id: str
  type: str
  text: str
  bbox: BBox | None
  confidence: float | None
  source: "embedded" | "ocr" | "derived"

BBox:
  x0, y0, x1, y1
  coordinate_system: "top_left_normalized"
```

Normalize bbox coordinates to `[0,1]` relative to page dimensions whenever possible. This makes the frontend independent of renderer pixel dimensions.

Store large canonical JSON in object storage if it becomes large; keep DB summary/index metadata. MVP may store JSONB if size remains reasonable, but design a storage abstraction.

## 5. LLM extraction request design

Do not send unbounded entire documents blindly.

Strategy:
- small documents: parsed text + page images if useful;
- larger documents: use parsed sections/page chunks and select relevant pages;
- enforce configurable page/token limits;
- preserve page IDs in prompts;
- ask model to return field values plus evidence references.

Provider output shape:

```json
{
  "data": { "... user schema ..." },
  "field_evidence": [
    {
      "path": "$.invoice_number",
      "page": 1,
      "quote": "Invoice No. INV-10293",
      "block_ids": ["p1_b14"],
      "self_confidence": 0.96
    }
  ],
  "document_notes": []
}
```

The user data schema is dynamic, so wrap it or issue two structured calls if strict schema composition is cumbersome. The implementation should prefer strict schema adherence for `data`.

## 6. Job model

A document can have multiple jobs/runs.

Use:
- `processing_jobs`
- `parse_runs`
- `extraction_runs`

Job idempotency key:
`{document_id}:{processor_version_id}:{operation}:{input_version}`

Celery retry:
- transient storage/network/LLM failures: retry;
- invalid file/permanent parser error: fail without infinite retry;
- use bounded exponential backoff.

## 7. Status updates

Frontend may poll every few seconds using TanStack Query. SSE is optional.

Keep status endpoint lightweight.

## 8. API versioning

All API routes under:
`/api/v1`

## 9. Multi-tenancy

Every request resolves:
- authenticated user;
- active workspace or API-key workspace.

Service-level authorization must enforce membership.

Never rely solely on frontend filtering.

## 10. Configuration

Use Pydantic Settings.

Environment groups:
- app
- DB
- Redis
- S3
- auth
- OpenAI
- upload limits
- model/processing limits
- CORS

## 11. Model/provider selection

Do not hard-code a dated model name throughout the app.

Use env/config:
- `OPENAI_EXTRACTION_MODEL`
- `OPENAI_SCHEMA_MODEL`

Provide sensible example placeholders in `.env.example`.

## 12. Error model

API standard error:

```json
{
  "error": {
    "code": "PROCESSOR_NOT_FOUND",
    "message": "Processor not found",
    "details": {},
    "request_id": "..."
  }
}
```

## 13. Auditability

Audit:
- processor publishing;
- document upload/delete;
- extraction run;
- review override;
- approval;
- API key create/revoke;
- webhook changes.

## 14. Deletion

Soft-delete business records where operationally useful.

Document deletion workflow:
- mark deleted;
- enqueue binary/derived artifact deletion;
- preserve minimal audit record without extracted content where policy allows.
