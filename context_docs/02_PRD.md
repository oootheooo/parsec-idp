# Product Requirements Document (PRD)

## 1. Goal

Build a production-oriented web application that converts arbitrary supported documents into user-defined structured data with traceable evidence, validation, human review, and automation hooks.

## 2. Success criteria

A new user can:
1. create an account;
2. enter a workspace;
3. create or use a processor;
4. upload a document;
5. see visible processing progress;
6. receive structured extracted fields;
7. review each value against the original document;
8. correct mistakes;
9. approve the result;
10. export JSON/CSV or receive it via API/webhook.

## 3. User roles

### Owner
- workspace settings;
- member management;
- API keys;
- webhooks;
- all processor/document permissions.

### Admin
- all document and processor functions;
- workflows;
- can manage most settings;
- cannot delete workspace or transfer ownership.

### Member
- upload documents;
- view/process documents;
- review and approve;
- create/edit processors if permitted by current simple role model.

### Viewer
- read-only access to documents and results.

MVP may implement Owner/Admin/Member/Viewer without custom granular permissions.

## 4. Functional requirements

### 4.1 Authentication
- Register.
- Login.
- Logout.
- Refresh access token.
- Password hashing with Argon2.
- JWT access token.
- Rotating refresh token.
- Store refresh token hashes in DB.
- Revoke refresh sessions on logout.
- Basic account profile.

Password reset email may be implemented if SMTP is configured; otherwise architecture/routes should be ready but not block MVP acceptance.

### 4.2 Workspaces
- Every account belongs to at least one workspace.
- Create workspace.
- Workspace switcher.
- Invite/membership may be MVP-light; direct owner-created membership is acceptable.
- Every domain object is tenant-isolated.

### 4.3 Processor management
A processor has:
- ID;
- workspace;
- name;
- description;
- status: draft/active/archived;
- current version;
- instructions;
- JSON Schema;
- validation config;
- review config;
- created/updated timestamps.

Features:
- list/search processors;
- create from blank;
- create from preset;
- duplicate;
- edit draft;
- publish version;
- archive;
- inspect version history.

Published processor versions are immutable. New edits create a new draft/version.

### 4.4 AI schema builder
A user may describe desired fields in natural language, e.g.:
> Extract supplier name, invoice number, invoice date, line items, VAT and grand total.

Backend calls an LLM to propose:
- JSON Schema;
- field descriptions;
- optional validation hints.

The user must be able to review/edit before publishing.

AI schema builder is convenience only; manual JSON schema editing must exist.

### 4.5 Document ingestion
Supported initial formats:
- PDF;
- PNG/JPEG/TIFF/WEBP;
- DOCX;
- XLSX;
- PPTX;
- HTML;
- CSV;
- Markdown/text where practical.

Upload options:
- web UI;
- authenticated API.

Requirements:
- validate MIME/extension;
- configurable max file size;
- calculate SHA-256;
- immutable original;
- status lifecycle;
- optional chosen processor;
- reject unsupported or dangerous content cleanly.

### 4.6 Document processing lifecycle
Statuses:
- `uploaded`
- `queued`
- `parsing`
- `parsed`
- `extracting`
- `validating`
- `review_required`
- `completed`
- `failed`
- `cancelled`

Status transitions must be persisted as job events.

### 4.7 Parsing / OCR
The parser must generate a canonical representation including, when available:
- pages;
- dimensions;
- text blocks;
- block type;
- reading order;
- bounding boxes;
- tables;
- cells;
- source text;
- embedded text vs OCR indication;
- document-level plain text/markdown.

Use Docling as primary conversion. Use suitable fallback/helper tooling for PDFs.

For scanned/image documents, enable OCR.

### 4.8 Document classification
If a processor is selected by the user, no automatic classification is necessary.

Optional assisted mode:
- classify against active processors;
- return suggested processor + confidence;
- require user confirmation if ambiguous.

This can be implemented after the main selected-processor flow.

### 4.9 Structured extraction
Given:
- selected processor version;
- canonical parsed document;
- optionally page images;
- extraction instructions;
- JSON Schema;

the extraction provider must produce schema-conforming JSON.

Use strict structured output when supported by provider.

The provider layer must support:
- `OpenAIExtractionProvider`;
- `MockExtractionProvider`.

Store:
- provider;
- model;
- prompt/version;
- request metadata (non-secret);
- raw structured response;
- latency;
- usage if returned;
- failure metadata.

### 4.10 Evidence mapping
For each leaf field where feasible:
- normalized JSON path;
- value;
- page;
- source text;
- block IDs and/or bbox;
- evidence strength.

LLM may return evidence hints, but backend should match evidence to canonical blocks where possible.

If precise bbox cannot be determined, field remains usable with source text/page or `evidence_unavailable`.

### 4.11 Validation
Support generic validations:
- required;
- type;
- enum;
- regex;
- min/max;
- minLength/maxLength;
- date parseability;
- numeric parseability.

Support custom processor validation rules using a safe declarative expression format, not arbitrary Python execution.

Initial rule examples:
- `subtotal + tax ~= total` within tolerance;
- `invoice_date <= today`;
- `currency in ["PHP", "USD"]`.

Use JSON-Logic-like declarative rules or a small internally implemented safe expression DSL.

Validation outputs:
- passed;
- warning;
- failed;
- field/document scope;
- message.

### 4.12 Confidence
Return a platform confidence from 0 to 1 per field.

Suggested initial weighted score:
- evidence available/matched: 0.30
- parser/OCR confidence if available: 0.20
- model-reported certainty/evidence quality: 0.20
- validation success: 0.20
- cross-source consistency: 0.10

If a signal is unavailable, redistribute weights across available signals or use a documented fallback.

Thresholds:
- >= 0.90: high
- 0.70–0.899: medium
- < 0.70: low

Processor review config may set a different threshold.

### 4.13 Human review
Review screen:
- document viewer;
- extraction fields;
- confidence badge;
- validation messages;
- source evidence;
- editable values;
- arrays/tables editable;
- field approval/rejection;
- document approval.

Changes create reviewer overrides with:
- original value;
- corrected value;
- reviewer;
- timestamp;
- optional note.

Final result is computed from model result + latest accepted overrides.

### 4.14 Exports
- JSON export of final approved/current result.
- CSV export:
  - flat scalar fields;
  - arrays/tables may be serialized or exported as separate CSVs in a ZIP.
- downloadable parsed Markdown/text is optional but useful.

### 4.15 API keys
Workspace owner/admin can:
- create API key;
- see plaintext only once;
- revoke key;
- set name;
- optionally expiration.

Store only hash/prefix.

API key auth enables:
- upload document;
- query document/job;
- fetch extraction result.

### 4.16 Webhooks
Workspace webhook endpoints:
- URL;
- signing secret;
- event subscriptions;
- enabled status.

Events:
- `document.processing_started`
- `document.processing_completed`
- `document.processing_failed`
- `document.review_required`
- `document.approved`

Delivery:
- signed HMAC SHA-256;
- retry with exponential backoff;
- delivery log;
- manual retry.

### 4.17 Workflow rules
MVP simple rules, not a general workflow engine.

Rule triggers:
- extraction completed;
- document approved.

Conditions:
- validation failed;
- confidence below threshold;
- extracted field comparison;
- processor ID.

Actions:
- mark review required;
- send webhook;
- auto-approve when all validations pass and all fields exceed threshold.

### 4.18 Dashboard
Show:
- documents processed last 7/30 days;
- status counts;
- review queue count;
- average processing time;
- pages processed;
- failure count;
- recent documents.

### 4.19 Search/filter
Documents:
- filename;
- processor;
- status;
- uploaded date;
- review state.

Processors:
- name;
- status.

## 5. Non-functional requirements

### Reliability
- job retries;
- idempotency;
- no duplicate processing from retries;
- processing error persisted.

### Performance
- upload API returns quickly after persistence.
- list APIs paginated.
- document processing is asynchronous.
- review screen should render metadata before all page thumbnails.

### Security
See `08_SECURITY_PRIVACY.md`.

### Observability
- structured logs;
- request IDs;
- job IDs;
- health/readiness endpoints;
- processing timing metrics persisted.

## 6. MVP exclusions
- billing;
- SSO/SAML;
- SCIM;
- advanced annotation training;
- custom fine-tuning;
- advanced handwriting engine selection UI;
- on-prem installer;
- complex multi-step BPM designer;
- email inbox ingestion.

## 7. Future-friendly extension points
- additional OCR engines;
- Azure/AWS/Google document AI;
- alternate LLM providers;
- email ingestion;
- scheduled SFTP ingestion;
- ERP connectors;
- custom review forms;
- learning from corrections;
- per-processor evaluation datasets.
