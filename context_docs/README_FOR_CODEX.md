# HANDL Document Intelligence — Build Pack

This folder is a requirements and execution pack intended to be placed at the root of a new repository and given to ChatGPT Codex.

## Start with

`00_MASTER_CODEX_PROMPT.md`

Then Codex should read `AGENTS.md` and all numbered specifications.

## What this pack defines

- product vision/context;
- complete MVP PRD;
- frontend/backend technology;
- system architecture;
- relational data model;
- REST API;
- document parsing/OCR/extraction pipeline;
- evidence/validation/confidence strategy;
- review UX;
- auth/security/privacy;
- API keys/webhooks/workflows;
- deployment;
- test acceptance;
- implementation order;
- seed processor schemas.

## Intended result

A fully working application that can run locally through Docker Compose and can later be deployed using managed Postgres, Redis, S3-compatible storage, containerized FastAPI/Celery, and a static React frontend.

The pack intentionally does not pin a single OpenAI model name. The implementation must use environment configuration so the chosen model can be changed without code changes.
