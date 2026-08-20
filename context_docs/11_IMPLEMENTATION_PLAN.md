# Implementation Plan for Codex

This is a recommended build order, not a substitute for the requirements.

## Phase 0 — Repository and tooling
- monorepo folders;
- Docker Compose;
- backend project;
- frontend project;
- env examples;
- Makefile or task commands;
- CI-friendly scripts.

## Phase 1 — Core backend
- settings;
- DB;
- migrations;
- error model;
- request IDs;
- auth;
- workspaces/memberships;
- audit service.

Deliverable:
register/login and authenticated workspace API.

## Phase 2 — Frontend shell/auth
- routes;
- auth storage/refresh handling;
- app shell;
- workspace context;
- dashboard placeholder backed by real summary endpoint.

Deliverable:
usable authenticated SaaS shell.

## Phase 3 — Processors
Backend:
- models;
- versions;
- publish immutability;
- preset seed;
- schema validation.

Frontend:
- list;
- create;
- edit;
- raw JSON schema;
- basic visual field editor;
- publish.

Deliverable:
active reusable processor.

## Phase 4 — Upload/storage
- S3 abstraction;
- MinIO config;
- create upload;
- direct upload or multipart;
- finalize;
- document list/detail;
- worker enqueue.

Deliverable:
document persisted and queued.

## Phase 5 — Parsing
- Celery;
- Docling adapter;
- canonical models;
- PyMuPDF helper;
- page assets;
- status events;
- parse run.

Deliverable:
native/scanned PDF can produce parsed representation.

## Phase 6 — Extraction
- provider interface;
- mock provider;
- OpenAI provider;
- dynamic schema;
- prompt builder;
- extraction run;
- field materialization;
- evidence mapping.

Deliverable:
end-to-end structured extraction.

## Phase 7 — Validation/confidence
- JSON Schema validation;
- safe rule engine;
- confidence scoring;
- review-required decision.

Deliverable:
operationally meaningful extraction state.

## Phase 8 — Review UI
- split viewer;
- page navigation;
- bbox overlay;
- recursive schema field renderer;
- edit/correct/approve;
- effective data;
- document approval.

Deliverable:
human-in-the-loop workflow.

## Phase 9 — Developer features
- API keys;
- API auth;
- webhook config;
- event generation;
- signing;
- retries;
- delivery log.

## Phase 10 — Workflow rules
- simple DB model;
- evaluator;
- auto-approve / review / webhook actions;
- constrained UI.

## Phase 11 — Export/dashboard/polish
- JSON/CSV;
- usage events;
- dashboard stats;
- empty/error states;
- responsive polish.

## Phase 12 — Testing
- unit;
- integration;
- frontend;
- E2E;
- migrations from scratch;
- README runbook.

## Important implementation shortcuts that ARE allowed

- Polling instead of WebSocket/SSE.
- One Celery worker container for all queues locally.
- MinIO instead of cloud storage locally.
- Limited visual schema builder as long as raw JSON schema editor works.
- Declarative workflow builder with only supported condition/action types.
- Page-only evidence when bbox cannot be obtained.
- Mock provider in CI.

## Shortcuts that are NOT allowed

- synchronous OCR in upload endpoint;
- mock-only extraction in product runtime;
- no tenant authorization;
- overwrite model output during review;
- public object storage;
- hard-coded invoice-only schema;
- pretending all evidence has bbox when it does not;
- arbitrary Python/eval validation expressions.
