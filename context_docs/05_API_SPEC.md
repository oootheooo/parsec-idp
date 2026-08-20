# REST API Specification

Base path: `/api/v1`

Exact response wrappers may be refined, but endpoints and behavior should remain.

## Auth

### POST `/auth/register`
Input:
```json
{"email":"user@example.com","password":"...","display_name":"...","workspace_name":"My Company"}
```

Creates user + initial workspace.

### POST `/auth/login`
Returns access token and sets/returns refresh mechanism according to implementation.
Prefer HttpOnly secure cookie for refresh token in browser; API access token can be returned in JSON.

### POST `/auth/refresh`
Rotate refresh token.

### POST `/auth/logout`
Revoke refresh session.

### GET `/me`
Current user and memberships.

## Workspaces

### GET `/workspaces`
### POST `/workspaces`
### GET `/workspaces/{id}`

Use header:
`X-Workspace-ID: <uuid>`
for browser API requests after authentication.

## Processors

### GET `/processors`
Query:
- `status`
- `search`
- `page`
- `page_size`

### POST `/processors`
Create blank or from template.

### GET `/processors/{id}`
### PATCH `/processors/{id}`
### POST `/processors/{id}/duplicate`
### POST `/processors/{id}/archive`

### GET `/processors/{id}/versions`
### POST `/processors/{id}/versions`
Create next draft version.

### PATCH `/processors/{id}/versions/{version_id}`
Only draft.

### POST `/processors/{id}/versions/{version_id}/publish`

### POST `/processors/schema-assist`
Input:
```json
{
  "description": "Extract supplier, invoice number, dates, line items, VAT and total",
  "sample_context": null
}
```
Output:
```json
{
  "schema": {},
  "instructions": "...",
  "validation_suggestions": []
}
```

## Uploads/Documents

Implementation can use direct multipart upload or pre-signed S3 upload. Preferred scalable flow:

### POST `/uploads`
Input metadata:
```json
{
  "filename":"invoice.pdf",
  "content_type":"application/pdf",
  "size":123456,
  "processor_id":"..."
}
```

Output:
- document ID;
- presigned PUT URL;
- required headers;
- object key/token.

### POST `/uploads/{document_id}/complete`
Server verifies object exists/size and enqueues.

Alternative local fallback: multipart `/documents/upload`.

### GET `/documents`
Filters:
- status
- processor_id
- review_required
- from/to
- search

### GET `/documents/{id}`
Return metadata, latest parse/extraction status, review summary.

### DELETE `/documents/{id}`

### POST `/documents/{id}/process`
Re-run with selected processor/version.
Input:
```json
{"processor_id":"...", "processor_version_id":null}
```

### POST `/documents/{id}/cancel`
Best effort.

### GET `/documents/{id}/status`
Lightweight polling endpoint.

## Parsed document

### GET `/documents/{id}/pages`
Page metadata and asset URLs.

### GET `/documents/{id}/pages/{page_number}`
Canonical blocks or page details.

### GET `/documents/{id}/parsed-text`
Optional text/markdown view.

Object URLs must be signed/short-lived.

## Extraction

### GET `/documents/{id}/extractions`
### GET `/documents/{id}/extractions/{run_id}`

Response should include:
```json
{
  "data": {},
  "effective_data": {},
  "fields": [],
  "validation_summary": {},
  "review_summary": {}
}
```

`effective_data` = raw model data with accepted reviewer overrides applied.

### POST `/documents/{id}/extractions/{run_id}/retry`

## Review

### POST `/documents/{id}/review/fields`
Input:
```json
{
  "extraction_run_id":"...",
  "json_path":"$.total",
  "action":"correct",
  "value":125000,
  "note":"Verified against document"
}
```

Actions:
- approve
- reject
- correct
- reset

### POST `/documents/{id}/review/approve`
Approves current extraction run if caller permitted.

### GET `/documents/review-queue`

## Export

### GET `/documents/{id}/export/json`
### GET `/documents/{id}/export/csv`

For complex exports, endpoint may return a signed generated file.

## API keys

### GET `/api-keys`
### POST `/api-keys`
Plaintext returned once.
### DELETE `/api-keys/{id}`

API-key request header:
`Authorization: Bearer hdl_live_...`

Backend distinguishes JWT vs API key format safely.

## Webhooks

### GET `/webhooks`
### POST `/webhooks`
### PATCH `/webhooks/{id}`
### DELETE `/webhooks/{id}`
### GET `/webhooks/{id}/deliveries`
### POST `/webhooks/{id}/test`
### POST `/webhook-deliveries/{id}/retry`

Webhook headers:
- `X-Handl-Event`
- `X-Handl-Delivery-ID`
- `X-Handl-Timestamp`
- `X-Handl-Signature`

Suggested signing base:
`{timestamp}.{raw_body}`

Signature:
`hex(hmac_sha256(secret, base))`

Reject replay in example webhook verification docs using a time window.

## Workflows

### GET `/workflow-rules`
### POST `/workflow-rules`
### PATCH `/workflow-rules/{id}`
### DELETE `/workflow-rules/{id}`

## Dashboard

### GET `/dashboard/summary?range=30d`

## Health

### GET `/health`
Process alive.

### GET `/ready`
Check DB and Redis; optionally storage.

## Common list response

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 100,
  "pages": 4
}
```

## Idempotency

Public upload/process endpoints should accept:
`Idempotency-Key`

Store idempotency record or derive job idempotency where relevant.

## HTTP status guidance

- 200 success
- 201 create
- 202 queued
- 204 delete/no body
- 400 malformed
- 401 unauthenticated
- 403 unauthorized
- 404 missing or inaccessible resource
- 409 conflict/state conflict
- 413 upload too large
- 415 unsupported media
- 422 validation
- 429 rate limited
- 500 unexpected
- 503 dependency unavailable
