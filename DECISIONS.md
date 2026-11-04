# Implementation Decisions

- The product name is **Parsec**. API keys use the `psc_` prefix; webhook headers use `X-Parsec-*`.
- Multipart upload is used for the initial local flow. It validates and stores bytes but never parses synchronously; the endpoint persists a queued job and dispatches Celery.
- Canonical JSON is stored in PostgreSQL JSONB for the MVP. The model includes object-storage fields so large representations can move without changing the public contract.
- Docling is the primary broad-format converter in the worker image. PyMuPDF supplies dependable PDF page/block geometry and is also the fallback when Docling is unavailable.
- The deterministic mock provider produces schema-compatible neutral values and real evidence references from canonical blocks; it is a provider implementation, not hard-coded per-document demo data.
- Bounding boxes are normalized to top-left `[0,1]` coordinates. Missing geometry stays missing.
- Polling is used for status updates. Webhook delivery remains asynchronous and separately retryable.
- SQLite is used only by the isolated automated test suite; PostgreSQL remains the application system of record.
