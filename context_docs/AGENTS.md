# AGENTS.md — Repository Rules for Codex

## Product
HANDL Document Intelligence is a multi-tenant intelligent document processing platform that turns arbitrary business documents into structured, validated, reviewable data.

## Engineering principles

- Build real features, not placeholders.
- Prefer simple, explicit code over premature framework abstraction.
- Keep frontend and backend independently testable.
- Preserve source evidence for extracted values.
- Treat documents as untrusted input.
- Heavy processing belongs in Celery workers.
- Keep model/vendor integration replaceable.
- Use PostgreSQL as the system of record.
- Use object storage for binaries and large derived artifacts.
- Use UUID primary keys.
- Use UTC timestamps.
- Use JSONB when the structure is user-defined, but keep searchable operational fields relational.

## Repository layout

```text
/
  frontend/
  backend/
  infra/
  docs/
  docker-compose.yml
  README.md
  .env.example
```

Recommended backend layout:

```text
backend/app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  processing/
  providers/
  workers/
  tests/
```

Recommended frontend layout:

```text
frontend/src/
  api/
  components/
  features/
  hooks/
  layouts/
  pages/
  routes/
  types/
  utils/
```

## Backend conventions

- FastAPI routers are thin.
- Business logic goes in services.
- SQLAlchemy ORM entities do not double as public Pydantic schemas.
- All tenant-scoped service methods require workspace context.
- Never return object storage credentials to the client.
- Prefer pre-signed uploads/downloads where practical.
- Webhook delivery must be signed.
- API keys are stored hashed, never plaintext after creation.

## Frontend conventions

- TypeScript strict mode.
- TanStack Query owns server state.
- React Hook Form + Zod owns complex form state/validation.
- Keep API types generated or centrally defined.
- Avoid giant page components.
- All destructive actions require confirmation.
- Critical async states must be visible.

## Testing

A change is incomplete when it breaks:
- backend tests,
- frontend tests,
- lint,
- type check,
- migration bootstrapping.

## Security

Never log:
- access tokens,
- refresh tokens,
- API keys,
- full extracted sensitive data,
- raw document bytes.

Use signed short-lived object URLs.

## Source-of-truth docs

Read all numbered markdown documents in the repository root before making architectural changes.
