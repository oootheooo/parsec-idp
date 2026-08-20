# Test Plan and Acceptance Criteria

## 1. Mandatory automated test categories

### Backend unit
- password hashing/token rotation;
- tenant authorization helpers;
- schema validation;
- rule evaluation;
- confidence calculation;
- reviewer override application;
- webhook signing;
- URL/SSRF validation;
- provider mock.

### Backend integration
Using test PostgreSQL/Redis or suitable isolated containers:
- register/login;
- create processor/version/publish;
- upload document metadata;
- enqueue/process with mock provider;
- read extraction;
- correct field;
- approve document;
- API key auth;
- webhook delivery record.

### Frontend
- login form validation;
- processors list/editor critical behavior;
- upload form;
- document status;
- review field edit;
- approval interaction.

### End-to-end
At minimum one happy-path workflow:
1. register;
2. create processor;
3. upload a sample PDF;
4. mock extraction completes;
5. open review;
6. correct a field;
7. approve;
8. export JSON.

## 2. Required acceptance scenarios

### A. First run
Given a clean database and configured local Docker services,
when migrations and seeds run,
then user can register and use application.

### B. Processor
Given an owner,
when they create a processor with valid JSON Schema and publish,
then version is immutable and appears active.

### C. Upload
Given an active processor,
when supported PDF uploaded,
then document becomes queued without blocking the HTTP request.

### D. Parse
Given queued supported document,
when worker handles job,
then page count, canonical representation, text and page evidence are persisted.

### E. Extraction
Given parsed doc and MockExtractionProvider,
when extraction runs,
then schema-compatible result and materialized leaf fields exist.

### F. Real provider integration
Given valid OpenAI configuration,
when extraction runs,
then provider receives schema + document context and returns persisted structured result.
This should be integration-ready even if automated CI does not call paid API.

### G. Review
Given a low-confidence field,
review UI shows its confidence and evidence.
When corrected,
effective result changes while raw model result remains unchanged.

### H. Validation
Given invoice rule `subtotal + tax ~= total`,
invalid data produces visible validation failure and review-required state.

### I. Approval
Given all required review work done,
authorized member can approve.
Approval is audited.

### J. Export
JSON export reflects effective reviewed values.

### K. API key
Created API key is shown once.
Stored record does not contain plaintext.
Key can authenticate permitted endpoints.
Revoked key fails.

### L. Webhook
On processing completion:
- event generated;
- signed delivery attempted;
- result logged;
- transient failure is retryable.

### M. Tenant isolation
User in workspace A cannot fetch processor/document from workspace B by UUID.

## 3. Quality gates

Backend:
- `pytest`
- lint via Ruff
- type checking via mypy or pyright if configured

Frontend:
- ESLint
- TypeScript `tsc --noEmit`
- Vitest

Build:
- production frontend build passes
- backend imports cleanly
- migrations apply to empty DB

## 4. Manual smoke test document types
If sample files are available:
- native text PDF;
- scanned PDF/image;
- DOCX;
- XLSX with table.

## 5. Performance sanity
Not hard SLA, but verify:
- 50-document list paginates;
- upload endpoint does not perform parse;
- worker can process jobs independently;
- review UI does not download every full-res page on initial render.

## 6. Security sanity
- path traversal filename does not escape storage key;
- inaccessible UUID returns safe response;
- private webhook URL blocked in production mode;
- logs do not contain API keys;
- unsupported upload rejected.
