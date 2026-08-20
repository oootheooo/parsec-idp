import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import (
    Document,
    DocumentApproval,
    ExtractionField,
    ExtractionRun,
    FieldEvidence,
    ParseRun,
    ProcessingJob,
    ProcessorVersion,
    UsageEvent,
    ValidationResult,
    WorkflowRule,
)
from app.providers import extraction_provider
from app.services.common import transition
from app.services.confidence import calculate_confidence, confidence_level
from app.services.parser import prepare_document
from app.services.rules import evaluate
from app.services.schema_tools import flatten_leaves
from app.services.storage import get_bytes
from app.services.webhooks import emit


async def apply_workflows(
    db, document, run, version, *, needs_review: bool,
    validation_failed: bool, min_confidence: float,
) -> tuple[bool, bool]:
    rules = (await db.scalars(select(WorkflowRule).where(
        WorkflowRule.workspace_id == document.workspace_id,
        WorkflowRule.enabled,
        WorkflowRule.trigger == "extraction_completed",
    ))).all()
    auto_approved = False
    for rule in rules:
        if rule.processor_id and rule.processor_id != document.selected_processor_id:
            continue
        condition = rule.conditions or {}
        op = condition.get("op")
        matches = (
            not condition
            or (op == "validation_failed" and validation_failed)
            or (op == "confidence_below" and min_confidence < float(condition.get("value", 0.7)))
            or (op == "all_validations_pass" and not validation_failed)
            or (op not in {"validation_failed", "confidence_below", "all_validations_pass"}
                and bool(evaluate(condition, run.raw_data)))
        )
        if not matches:
            continue
        for action in rule.actions or []:
            kind = action.get("type")
            if kind == "mark_review_required":
                needs_review = True
            elif kind == "auto_approve" and not validation_failed:
                threshold = float(action.get("threshold", version.review_config.get("threshold", 0.7)))
                if min_confidence >= threshold:
                    needs_review = False
                    auto_approved = True
                    db.add(DocumentApproval(
                        document_id=document.id, extraction_run_id=run.id,
                        approved_by_user_id=version.created_by_user_id,
                        note=f"Auto-approved by workflow {rule.name}",
                    ))
    return needs_review, auto_approved


def find_evidence(canonical: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    block_ids = set(hint.get("block_ids", []))
    quote = str(hint.get("quote", "")).strip().lower()
    page_no = hint.get("page")
    candidates = [block for page in canonical.get("pages", []) if not page_no or page["page_number"] == page_no for block in page.get("blocks", [])]
    matched = [block for block in candidates if block["id"] in block_ids]
    strength = 1.0 if matched else 0.0
    if not matched and quote:
        matched = [block for block in candidates if quote in block.get("text", "").lower() or block.get("text", "").lower() in quote]
        strength = 0.8 if matched else 0.5 if page_no else 0.0
    bbox = matched[0].get("bbox") if len(matched) == 1 else None
    return {"page_number": page_no or (int(matched[0]["id"].split("_")[0][1:]) if matched else None),
            "block_ids": [block["id"] for block in matched], "bbox": bbox,
            "source_text": hint.get("quote") or (matched[0].get("text") if matched else None),
            "evidence_strength": strength, "parser_confidence": matched[0].get("confidence") if matched else None,
            "model_self_confidence": hint.get("self_confidence")}


async def process_document(document_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        document = await db.get(Document, document_id)
        if not document or document.deleted_at:
            return
        job = await db.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id).order_by(ProcessingJob.created_at.desc()))
        if job and job.status == "succeeded":
            return
        try:
            if job:
                job.status, job.started_at, job.finished_at = "running", datetime.now(timezone.utc), None
                job.error_code, job.error_message_safe, job.attempt = None, None, job.attempt + 1
            document.error_code, document.error_message_safe = None, None
            await transition(db, document, "parsing", "Reading document structure")
            await db.commit()
            raw = await get_bytes(document.object_key)
            version = await db.get(ProcessorVersion, document.selected_processor_version_id) if document.selected_processor_version_id else None
            if document.selected_processor_version_id and (not version or version.state != "published"):
                raise ValueError("Published processor version not found")
            prepared = prepare_document(raw, document.mime_type, document.original_filename, mode=document.processing_mode,
                                        visual_reader=document.visual_reader,
                                        schema=version.schema_json if version else None, instructions=version.instructions if version else "",
                                        for_extraction=version is not None)
            canonical = prepared.canonical
            if canonical["page_count"] > settings.max_document_pages:
                raise ValueError("Document exceeds configured page limit")
            parse_run = ParseRun(document_id=document.id, parser_name=canonical["metadata"]["parser"], status="succeeded", canonical_json=canonical,
                                 metadata_json=canonical["metadata"], finished_at=datetime.now(timezone.utc))
            db.add(parse_run)
            await db.flush()
            document.page_count = canonical["page_count"]
            document.processing_route = canonical["metadata"]
            await transition(db, document, "parsed", f"Document prepared using {canonical['metadata']['route']} processing")
            db.add(UsageEvent(workspace_id=document.workspace_id, document_id=document.id, event_type="pages_parsed", quantity=document.page_count, unit="pages", metadata_json={}))
            if not document.selected_processor_version_id:
                await transition(db, document, "review_required", "Choose a processor to extract structured data")
                if job: job.status, job.finished_at = "succeeded", datetime.now(timezone.utc)
                await db.commit()
                await emit(document.workspace_id, "document.review_required", {"event": "document.review_required", "document_id": str(document.id), "workspace_id": str(document.workspace_id), "status": document.status})
                return
            await transition(db, document, "extracting", "Extracting structured data")
            await db.commit()
            provider = extraction_provider()
            input_hash = hashlib.sha256((document.sha256 + str(version.id) + document.processing_mode + document.visual_reader + json.dumps(version.schema_json, sort_keys=True)).encode()).hexdigest()
            provider_context = {**canonical, "model_text": prepared.model_text, "visual_pages": prepared.visual_pages}
            result = await provider.extract(schema=version.schema_json, instructions=version.instructions, document_context=provider_context, config=version.extraction_config)
            errors = list(Draft202012Validator(version.schema_json).iter_errors(result.data))
            run = ExtractionRun(document_id=document.id, processor_version_id=version.id, parse_run_id=parse_run.id,
                                provider=settings.extraction_provider, model=result.model, status="succeeded", raw_data=result.data,
                                provider_metadata=result.metadata, input_hash=input_hash, latency_ms=result.latency_ms,
                                input_tokens=result.metadata.get("input_tokens"), output_tokens=result.metadata.get("output_tokens"), finished_at=datetime.now(timezone.utc))
            db.add(run)
            await db.flush()
            evidence_by_path = {item["path"]: find_evidence(canonical, item) for item in result.field_evidence}
            schema_error_paths = {"$." + ".".join(str(item) for item in err.path) for err in errors}
            for path, value in flatten_leaves(result.data):
                evidence = evidence_by_path.get(path)
                validation_score = 0.3 if any(path.startswith(item) for item in schema_error_paths) else 1.0
                score = calculate_confidence(evidence_score=evidence["evidence_strength"] if evidence else 0,
                                             parser_score=evidence.get("parser_confidence") if evidence else None,
                                             model_score=evidence.get("model_self_confidence") if evidence else None,
                                             validation_score=validation_score, consistency_score=None)
                field = ExtractionField(extraction_run_id=run.id, json_path=path, field_label=path.rsplit(".", 1)[-1].replace("_", " ").title(),
                                        value_json=value, normalized_value_text=None if value is None else str(value), value_type=type(value).__name__,
                                        confidence=score, confidence_level=confidence_level(score), validation_state="failed" if validation_score < 1 else "passed")
                db.add(field)
                await db.flush()
                if evidence:
                    db.add(FieldEvidence(extraction_field_id=field.id, **evidence))
            for index, error in enumerate(errors):
                db.add(ValidationResult(extraction_run_id=run.id, rule_key=f"schema_{index}", scope="field", severity="error", passed=False, message=error.message, metadata_json={"path": list(error.path)}))
            rule_failed = False
            for index, rule in enumerate(version.validation_config or []):
                try:
                    passed = bool(evaluate(rule.get("expression", rule), result.data))
                    message = rule.get("message", "Validation rule passed" if passed else "Validation rule failed")
                except Exception:
                    passed, message = False, "Validation rule could not be evaluated"
                rule_failed = rule_failed or not passed
                db.add(ValidationResult(extraction_run_id=run.id, rule_key=rule.get("key", f"rule_{index}"), scope="document", severity=rule.get("severity", "error"), passed=passed, message=message, metadata_json={}))
            threshold = float(version.review_config.get("threshold", 0.7))
            always_review = bool(version.review_config.get("always_review", True))
            low = await db.scalar(select(ExtractionField.id).where(ExtractionField.extraction_run_id == run.id, ExtractionField.confidence < threshold).limit(1))
            needs_review = always_review or bool(errors) or rule_failed or low is not None
            min_confidence = await db.scalar(select(func.min(ExtractionField.confidence)).where(ExtractionField.extraction_run_id == run.id)) or 0.0
            needs_review, _ = await apply_workflows(
                db, document, run, version, needs_review=needs_review,
                validation_failed=bool(errors) or rule_failed,
                min_confidence=float(min_confidence),
            )
            await transition(db, document, "review_required" if needs_review else "completed", "Extraction ready for review" if needs_review else "Extraction completed")
            db.add(UsageEvent(workspace_id=document.workspace_id, document_id=document.id, event_type="document_processed", quantity=1, unit="documents", metadata_json={"provider": settings.extraction_provider}))
            if job:
                job.status, job.finished_at = "succeeded", datetime.now(timezone.utc)
                job.error_code, job.error_message_safe = None, None
            await db.commit()
            event_type = "document.review_required" if needs_review else "document.processing_completed"
            await emit(document.workspace_id, event_type, {"event": event_type, "document_id": str(document.id), "workspace_id": str(document.workspace_id), "status": document.status})
        except Exception as exc:
            await db.rollback()
            document = await db.get(Document, document_id)
            if document:
                code = str(exc) if str(exc) in {"PROVIDER_NOT_CONFIGURED"} else "PARSER_ERROR" if isinstance(exc, (ValueError, RuntimeError)) else "INTERNAL_PROCESSING_ERROR"
                document.error_code, document.error_message_safe = code, "AI extraction is not configured for this environment." if code == "PROVIDER_NOT_CONFIGURED" else "Document processing failed. You can retry."
                await transition(db, document, "failed", document.error_message_safe)
                job = await db.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id).order_by(ProcessingJob.created_at.desc()))
                if job: job.status, job.error_code, job.error_message_safe, job.finished_at = "failed", code, document.error_message_safe, datetime.now(timezone.utc)
                await db.commit()
                await emit(document.workspace_id, "document.processing_failed", {"event": "document.processing_failed", "document_id": str(document.id), "workspace_id": str(document.workspace_id), "error_code": code})
