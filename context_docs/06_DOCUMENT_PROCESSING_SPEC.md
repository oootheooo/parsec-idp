# Document Processing and Extraction Specification

## 1. Objective

Create a generic engine that can process many document types while preserving enough structure and evidence to support review.

## 2. Ingestion safety

Before parsing:
- enforce size limit;
- normalize filename;
- never execute uploaded files;
- detect content type;
- reject unsupported type;
- checksum;
- store with generated object key, never user-controlled path;
- optionally perform malware scanning through an integration point.

## 3. Parser selection

Primary path:
- Docling conversion.

Format-specific helpers:
- PDF: PyMuPDF can inspect page count/text and render images.
- Images: Docling OCR pipeline.
- legacy Office: convert in isolated subprocess/container only if enabled.

All parser errors become safe application errors.

## 4. OCR policy

Use embedded/native text when high quality.

OCR when:
- page has no meaningful text;
- document is an image;
- parser reports scanned content;
- forced by processor extraction config.

Do not OCR every native PDF by default because it adds cost/time and may reduce text fidelity.

## 5. Table handling

Preserve:
- table ID;
- page;
- bounding box;
- rows;
- columns;
- cell text;
- merged cell info if available.

Model prompt may include markdown tables plus original page imagery for difficult layouts.

## 6. Canonical block identifiers

Stable within parse run:
`p{page_number}_b{sequence}`

Table:
`p{page_number}_t{sequence}`

Cells:
`p{page_number}_t{sequence}_r{row}_c{col}`

## 7. Page assets

Generate:
- full page image only when needed for LLM/review;
- review-friendly rendition;
- optional thumbnail.

Store page dimensions and render scale metadata.

## 8. Extraction prompting

System/developer instructions to model should include these principles:
- extract only from supplied document;
- never infer absent values unless schema explicitly asks for derived values;
- use null when uncertain/absent where schema permits;
- preserve exact IDs/account numbers as strings;
- normalize dates to ISO only when unambiguous;
- do not silently convert currencies;
- return evidence per extracted leaf where possible;
- cite page and block IDs from supplied context;
- arrays must represent actual repeated items.

## 9. Dynamic JSON Schema

Processor schema restrictions for MVP:
- JSON object root;
- nested objects;
- arrays;
- string/number/integer/boolean/null;
- enum;
- descriptions;
- required;
- common numeric/string constraints.

Frontend schema builder may support common field types visually plus raw JSON mode.

Unsupported complex schema keywords should be validated/rejected before publishing.

## 10. Long-document strategy

Avoid hard requirement that all pages fit one request.

Algorithm:
1. parse entire document locally;
2. derive concise page summaries/keywords if necessary;
3. inspect schema field descriptions;
4. rank pages/sections for relevance;
5. include:
   - document metadata;
   - table of contents/section map where available;
   - relevant chunks;
   - relevant page images;
6. perform extraction;
7. if required fields absent and pages omitted, run targeted recovery pass.

For MVP, a simpler configurable maximum document size/page count is acceptable, but code should isolate the "context selection" service.

## 11. Evidence mapping

Model evidence object:
- json path;
- page;
- exact short quote;
- block IDs when available;
- self confidence.

Backend mapping:
1. verify block IDs exist;
2. if only quote exists, fuzzy-match against page blocks;
3. aggregate bbox around matched blocks;
4. save source text and evidence strength.

Evidence strength:
- 1.0: exact block match
- 0.8: strong quote match
- 0.5: page-only evidence
- 0.0: unavailable

Do not fabricate geometry.

## 12. Normalization

Store raw values in extraction run.

For materialized fields, derive normalized text and optional typed normalization:
- dates;
- currency amount;
- number;
- emails;
- phone strings.

Do not destroy original form.

## 13. Validation engine

### Layer A: JSON Schema
Validate structured data against published processor schema.

### Layer B: built-in semantic validators
Examples:
- date parses;
- email format;
- number finite;
- required value non-empty.

### Layer C: declarative business rules
Recommended condition format:
```json
{
  "op": "approx_equal",
  "left": {"op":"add","args":[{"path":"$.subtotal"},{"path":"$.tax"}]},
  "right": {"path":"$.total"},
  "tolerance": 0.02
}
```

Implement an explicit allowlist of operators.

Suggested operators:
- eq, neq
- gt, gte, lt, lte
- and, or, not
- add, subtract, multiply, divide
- in
- exists
- regex
- approx_equal

Never `eval()` user expressions.

## 14. Confidence algorithm

Each leaf field receives signals:

```text
evidence_score
parser_score
model_score
validation_score
consistency_score
```

Default weights:
```text
0.30 / 0.20 / 0.20 / 0.20 / 0.10
```

Validation:
- all pass -> 1.0
- warnings only -> 0.8
- failed -> 0.3

If parser OCR confidence unavailable, omit and renormalize.

`confidence = weighted_average(available_signals)`

Confidence is heuristic and must be labeled accordingly in UI.

## 15. Review decision

Default:
Review required if ANY:
- extraction failed;
- required field null;
- validation error;
- confidence < processor threshold;
- processor configured `always_review=true`.

Auto-complete if:
- processor allows auto approval;
- all required fields present;
- no validation error;
- all leaf confidence >= threshold.

## 16. Reviewer overrides

Effective document result:
1. start raw extraction JSON;
2. apply latest non-reset override per JSON path;
3. preserve audit trail;
4. recalculate applicable validation and review state.

## 17. Retrying

Retrying extraction:
- never delete old extraction run;
- create new run;
- new run becomes latest if succeeded;
- keep previous runs visible in history.

## 18. Provider interface

Python protocol/interface concept:

```python
class ExtractionProvider(Protocol):
    async def extract(
        self,
        *,
        schema: dict,
        instructions: str,
        document_context: DocumentContext,
        config: ExtractionConfig,
    ) -> ProviderExtractionResult: ...
```

OpenAI-specific logic must stay inside provider module.

## 19. OpenAI implementation guidance

Use the Responses API.

Prefer structured JSON Schema output where supported.

Use image/file inputs selectively when visual structure matters.

Never hard-code credentials or assume one permanent model ID.

Record provider usage/latency metadata when available.

## 20. Failure classes

Safe error codes:
- UNSUPPORTED_DOCUMENT
- FILE_TOO_LARGE
- STORAGE_ERROR
- PARSER_ERROR
- OCR_ERROR
- PROCESSOR_SCHEMA_INVALID
- PROVIDER_NOT_CONFIGURED
- PROVIDER_RATE_LIMIT
- PROVIDER_TIMEOUT
- PROVIDER_INVALID_OUTPUT
- VALIDATION_ENGINE_ERROR
- INTERNAL_PROCESSING_ERROR
