# Architecture Decisions and Rationale

## ADR-001 — React/Vite instead of Next.js
Decision: React SPA with Vite.

Reason:
- FastAPI owns backend/auth/API;
- no need for duplicate server runtime;
- simpler local/deployment topology;
- excellent fit for operational dashboard/review UI.

## ADR-002 — Celery + Redis
Decision: heavy document work through Celery.

Reason:
- OCR/parsing/model calls are long-running;
- retry and multi-worker execution are required;
- FastAPI's lightweight background tasks are not intended to be the primary heavy compute queue.

## ADR-003 — Docling as primary parser
Decision: use Docling adapter.

Reason:
- unified document representation;
- OCR support;
- table structure extraction;
- broad format support;
- local processing capabilities.

Keep an application canonical schema so Docling can be swapped later.

## ADR-004 — Hybrid parser + multimodal LLM
Decision:
do not rely exclusively on OCR or exclusively on direct LLM vision.

Reason:
- native parsing is cheap and gives geometry/structure;
- OCR handles scans;
- LLM handles semantic variability;
- combined evidence supports review.

## ADR-005 — Immutable extraction runs
Decision:
model output never mutates.

Reason:
- auditability;
- debugging;
- reproducibility;
- corrections can be compared to original output.

## ADR-006 — User-defined JSON Schema
Decision:
processor extraction contract is JSON Schema.

Reason:
- standard;
- machine-validatable;
- maps well to strict structured LLM output;
- flexible nested fields/arrays.

## ADR-007 — Backend-owned authentication
Decision:
implement local auth instead of requiring a third-party auth provider.

Reason:
- self-contained Codex build;
- no external setup blocker;
- can migrate/add SSO later.

## ADR-008 — Polling first
Decision:
frontend polls document status rather than requiring WebSockets.

Reason:
- simpler;
- robust;
- adequate for jobs lasting seconds/minutes;
- can add SSE later.

## ADR-009 — Evidence can degrade gracefully
Decision:
bbox evidence is preferred but not mandatory.

Evidence levels:
exact block/bbox > matched quote > page-only > unavailable.

Reason:
not every file/parser/model combination yields reliable geometry.

## ADR-010 — Safe declarative rule engine
Decision:
no user code execution.

Reason:
validation expressions are untrusted tenant input.
