import csv
import hashlib
import io
import json
import math
import secrets
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Cookie,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.dependencies import DB, Auth, WorkspaceAuth, require_admin, require_write
from app.models import (
    ApiKey,
    Document,
    DocumentApproval,
    DocumentStatusEvent,
    ExtractionField,
    ExtractionRun,
    FieldEvidence,
    ParseRun,
    ProcessingJob,
    Processor,
    ProcessorTemplate,
    ProcessorVersion,
    RefreshSession,
    ReviewOverride,
    Role,
    User,
    ValidationResult,
    Webhook,
    WebhookDelivery,
    WorkflowRule,
    Workspace,
    WorkspaceMember,
    now,
)
from app.schemas import (
    ApiKeyIn,
    ApprovalIn,
    LoginIn,
    ProcessIn,
    ProcessorCreate,
    ProcessorPatch,
    RegisterIn,
    ReviewFieldIn,
    SchemaAssistIn,
    TokenOut,
    VersionCreate,
    VersionPatch,
    WebhookIn,
    WebhookPatch,
    WorkflowIn,
    WorkflowPatch,
    WorkspaceCreate,
)
from app.security import (
    create_access_token,
    hash_password,
    opaque_token,
    token_hash,
    validate_webhook_url,
    verify_password,
)
from app.services.common import audit, slugify, transition
from app.services.schema_tools import apply_overrides, validate_processor_schema
from app.services.storage import delete_key, put_bytes, signed_get_url
from app.services.webhooks import emit
from app.worker import process_document_task

router = APIRouter(prefix="/api/v1")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "tif", "webp", "docx", "xlsx", "pptx", "html", "htm", "csv", "md", "txt"}
ALLOWED_MIMES = {"application/pdf", "image/png", "image/jpeg", "image/tiff", "image/webp", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "text/html", "text/csv", "text/markdown", "text/plain"}


def serialize(model: Any, *exclude: str) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns if column.name not in exclude}


def page(items: list[Any], total: int, page_no: int, size: int) -> dict[str, Any]:
    return {"items": items, "page": page_no, "page_size": size, "total": total, "pages": math.ceil(total / size) if total else 0}


async def issue_session(db: AsyncSession, user: User, request: Request, response: Response, family_id: uuid.UUID | None = None) -> str:
    refresh = opaque_token("hdl_refresh_")
    session = RefreshSession(user_id=user.id, token_hash=token_hash(refresh), family_id=family_id or uuid.uuid4(),
                             expires_at=now() + timedelta(days=settings.refresh_token_days), user_agent=request.headers.get("user-agent", "")[:500])
    db.add(session)
    await db.commit()
    response.set_cookie("handl_refresh", refresh, httponly=True, secure=settings.secure_cookies, samesite="lax",
                        max_age=settings.refresh_token_days * 86400, path="/api/v1/auth")
    return create_access_token(str(user.id))


@router.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(payload: RegisterIn, request: Request, response: Response, db: DB) -> TokenOut:
    email = payload.email.lower().strip()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with that email already exists")
    user = User(email=email, password_hash=hash_password(payload.password), display_name=payload.display_name.strip())
    db.add(user); await db.flush()
    workspace = Workspace(name=payload.workspace_name.strip(), slug=slugify(payload.workspace_name), created_by_user_id=user.id)
    db.add(workspace); await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=Role.owner))
    await audit(db, workspace_id=workspace.id, action="workspace.created", target_type="workspace", target_id=workspace.id, user_id=user.id)
    await db.commit()
    return TokenOut(access_token=await issue_session(db, user, request, response))


@router.post("/auth/login", response_model=TokenOut)
async def login(payload: LoginIn, request: Request, response: Response, db: DB) -> TokenOut:
    user = await db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=await issue_session(db, user, request, response))


@router.post("/auth/refresh", response_model=TokenOut)
async def refresh(request: Request, response: Response, db: DB, handl_refresh: Annotated[str | None, Cookie()] = None) -> TokenOut:
    if not handl_refresh:
        raise HTTPException(401, "Refresh session required")
    session = await db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(handl_refresh)))
    if not session or session.revoked_at or session.expires_at <= now():
        raise HTTPException(401, "Refresh session expired")
    session.revoked_at = now()
    user = await db.get(User, session.user_id)
    token = await issue_session(db, user, request, response, session.family_id)
    replacement = await db.scalar(select(RefreshSession).where(RefreshSession.family_id == session.family_id).order_by(desc(RefreshSession.created_at)))
    session.replaced_by_id = replacement.id
    await db.commit()
    return TokenOut(access_token=token)


@router.post("/auth/logout", status_code=204)
async def logout(response: Response, db: DB, handl_refresh: Annotated[str | None, Cookie()] = None) -> None:
    if handl_refresh:
        session = await db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(handl_refresh)))
        if session: session.revoked_at = now(); await db.commit()
    response.delete_cookie("handl_refresh", path="/api/v1/auth")


@router.get("/me")
async def me(principal: Auth, db: DB) -> dict[str, Any]:
    if not principal.user: raise HTTPException(403, "User session required")
    rows = (await db.execute(select(Workspace, WorkspaceMember.role).join(WorkspaceMember).where(WorkspaceMember.user_id == principal.user.id))).all()
    return {"id": principal.user.id, "email": principal.user.email, "display_name": principal.user.display_name,
            "workspaces": [{"id": ws.id, "name": ws.name, "slug": ws.slug, "role": role.value} for ws, role in rows]}


@router.get("/workspaces")
async def workspaces(principal: Auth, db: DB) -> list[dict[str, Any]]:
    if not principal.user: return [serialize(await db.get(Workspace, principal.workspace_id))]
    rows = (await db.execute(select(Workspace, WorkspaceMember.role).join(WorkspaceMember).where(WorkspaceMember.user_id == principal.user.id))).all()
    return [{"id": ws.id, "name": ws.name, "slug": ws.slug, "role": role.value} for ws, role in rows]


@router.post("/workspaces", status_code=201)
async def create_workspace(payload: WorkspaceCreate, principal: Auth, db: DB) -> dict[str, Any]:
    if not principal.user: raise HTTPException(403, "User session required")
    item = Workspace(name=payload.name, slug=slugify(payload.name), created_by_user_id=principal.user.id)
    db.add(item); await db.flush(); db.add(WorkspaceMember(workspace_id=item.id, user_id=principal.user.id, role=Role.owner)); await db.commit()
    return serialize(item)


@router.get("/processor-templates")
async def templates(principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    return [serialize(item) for item in (await db.scalars(select(ProcessorTemplate).where(ProcessorTemplate.is_active))).all()]


@router.get("/processors")
async def list_processors(principal: WorkspaceAuth, db: DB, status_filter: str | None = Query(None, alias="status"), search: str | None = None, page_no: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    filters = [Processor.workspace_id == principal.workspace_id, Processor.archived_at.is_(None)]
    if status_filter: filters.append(Processor.status == status_filter)
    if search: filters.append(Processor.name.ilike(f"%{search}%"))
    total = await db.scalar(select(func.count()).select_from(Processor).where(*filters)) or 0
    items = (await db.scalars(select(Processor).where(*filters).order_by(desc(Processor.updated_at)).offset((page_no-1)*page_size).limit(page_size))).all()
    return page([serialize(item) for item in items], total, page_no, page_size)


@router.post("/processors", status_code=201)
async def create_processor(payload: ProcessorCreate, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal)
    template = await db.scalar(select(ProcessorTemplate).where(ProcessorTemplate.key == payload.template_key, ProcessorTemplate.is_active)) if payload.template_key else None
    schema = payload.schema_json or (template.schema_json if template else {"type": "object", "additionalProperties": False, "properties": {}})
    validate_processor_schema(schema)
    user_id = principal.user.id if principal.user else principal.api_key.created_by_user_id
    item = Processor(workspace_id=principal.workspace_id, name=payload.name, description=payload.description or (template.description if template else ""), created_by_user_id=user_id)
    db.add(item); await db.flush()
    version = ProcessorVersion(processor_id=item.id, version_number=1, state="draft", schema_json=schema,
                               instructions=payload.instructions or (template.instructions if template else ""), validation_config=template.validation_config if template else [], review_config=template.review_config if template else {"threshold": .7, "always_review": True}, created_by_user_id=user_id)
    db.add(version); await audit(db, workspace_id=principal.workspace_id, action="processor.created", target_type="processor", target_id=item.id, user_id=principal.user.id if principal.user else None, api_key_id=principal.api_key.id if principal.api_key else None)
    await db.commit(); await db.refresh(item)
    result = serialize(item); result["draft_version_id"] = version.id; return result


async def scoped_processor(db: AsyncSession, workspace_id: uuid.UUID, processor_id: uuid.UUID) -> Processor:
    item = await db.scalar(select(Processor).options(selectinload(Processor.versions)).where(Processor.id == processor_id, Processor.workspace_id == workspace_id, Processor.archived_at.is_(None)))
    if not item: raise HTTPException(404, "Processor not found")
    return item


@router.get("/processors/{processor_id}")
async def get_processor(processor_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_processor(db, principal.workspace_id, processor_id)
    result = serialize(item); result["versions"] = [serialize(v) for v in sorted(item.versions, key=lambda v: v.version_number, reverse=True)]; return result


@router.patch("/processors/{processor_id}")
async def patch_processor(processor_id: uuid.UUID, payload: ProcessorPatch, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_processor(db, principal.workspace_id, processor_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await db.commit(); return serialize(item)


@router.post("/processors/{processor_id}/duplicate", status_code=201)
async def duplicate_processor(processor_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    source = await scoped_processor(db, principal.workspace_id, processor_id); latest = sorted(source.versions, key=lambda v: v.version_number)[-1]
    return await create_processor(ProcessorCreate(name=f"{source.name} copy", description=source.description, schema_json=latest.schema_json, instructions=latest.instructions), principal, db)


@router.post("/processors/{processor_id}/archive", status_code=204)
async def archive_processor(processor_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> None:
    require_write(principal); item = await scoped_processor(db, principal.workspace_id, processor_id); item.status="archived"; item.archived_at=now(); await db.commit()


@router.get("/processors/{processor_id}/versions")
async def versions(processor_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    item = await scoped_processor(db, principal.workspace_id, processor_id); return [serialize(v) for v in sorted(item.versions, key=lambda v: v.version_number, reverse=True)]


@router.post("/processors/{processor_id}/versions", status_code=201)
async def create_version(processor_id: uuid.UUID, payload: VersionCreate, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_processor(db, principal.workspace_id, processor_id)
    if any(v.state == "draft" for v in item.versions): raise HTTPException(409, "A draft version already exists")
    latest = sorted(item.versions, key=lambda v: v.version_number)[-1]; user_id = principal.user.id if principal.user else principal.api_key.created_by_user_id
    values = payload.model_dump(exclude_none=True)
    version = ProcessorVersion(processor_id=item.id, version_number=latest.version_number+1, state="draft", schema_json=values.get("schema_json", latest.schema_json), instructions=values.get("instructions", latest.instructions), validation_config=values.get("validation_config", latest.validation_config), review_config=values.get("review_config", latest.review_config), extraction_config=values.get("extraction_config", latest.extraction_config), created_by_user_id=user_id)
    validate_processor_schema(version.schema_json); db.add(version); await db.commit(); return serialize(version)


@router.patch("/processors/{processor_id}/versions/{version_id}")
async def patch_version(processor_id: uuid.UUID, version_id: uuid.UUID, payload: VersionPatch, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); await scoped_processor(db, principal.workspace_id, processor_id)
    version = await db.scalar(select(ProcessorVersion).where(ProcessorVersion.id == version_id, ProcessorVersion.processor_id == processor_id))
    if not version: raise HTTPException(404, "Version not found")
    if version.state != "draft": raise HTTPException(409, "Published versions are immutable")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(version, key, value)
    validate_processor_schema(version.schema_json); await db.commit(); return serialize(version)


@router.post("/processors/{processor_id}/versions/{version_id}/publish")
async def publish_version(processor_id: uuid.UUID, version_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_processor(db, principal.workspace_id, processor_id)
    version = await db.scalar(select(ProcessorVersion).where(ProcessorVersion.id == version_id, ProcessorVersion.processor_id == processor_id))
    if not version: raise HTTPException(404, "Version not found")
    if version.state != "draft": raise HTTPException(409, "Version is already published")
    validate_processor_schema(version.schema_json)
    if not version.schema_json.get("properties"):
        raise HTTPException(422, "Add at least one schema field before publishing")
    version.state="published"; version.published_at=now(); item.latest_version_id=version.id; item.status="active"
    await audit(db, workspace_id=principal.workspace_id, action="processor.published", target_type="processor_version", target_id=version.id, user_id=principal.user.id if principal.user else None)
    await db.commit(); return serialize(version)


@router.post("/processors/schema-assist")
async def schema_assist(payload: SchemaAssistIn, principal: WorkspaceAuth) -> dict[str, Any]:
    words = [part.strip().lower().replace(" ", "_") for part in payload.description.replace(" and ", ",").split(",") if part.strip()][:20]
    properties = {word: {"type": ["string", "null"], "description": f"Extract {word.replace('_', ' ')} exactly as shown."} for word in words}
    return {"schema": {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}, "instructions": payload.description, "validation_suggestions": [], "provider": "deterministic"}


async def scoped_document(db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    item = await db.scalar(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id, Document.deleted_at.is_(None)))
    if not item: raise HTTPException(404, "Document not found")
    return item


async def resolve_version(db: AsyncSession, principal: Any, processor_id: uuid.UUID, version_id: uuid.UUID | None = None) -> ProcessorVersion:
    processor = await scoped_processor(db, principal.workspace_id, processor_id)
    target = version_id or processor.latest_version_id
    version = await db.scalar(select(ProcessorVersion).where(ProcessorVersion.id == target, ProcessorVersion.processor_id == processor.id, ProcessorVersion.state == "published")) if target else None
    if not version: raise HTTPException(409, "Publish this processor before uploading documents")
    return version


def enqueue(document: Document, job: ProcessingJob) -> None:
    task = process_document_task.delay(str(document.id)); job.celery_task_id = task.id


@router.post("/documents/upload", status_code=202)
async def upload_document(principal: WorkspaceAuth, db: DB, file: Annotated[UploadFile, File()], processor_id: uuid.UUID | None = None,
                          processing_mode: Literal["smart", "native", "visual", "docling"] = "smart",
                          visual_reader: Literal["ocr", "vision"] = "vision") -> dict[str, Any]:
    require_write(principal)
    filename = (file.filename or "document").replace("\\", "/").split("/")[-1][:500]
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = (file.content_type or "application/octet-stream").split(";", 1)[0]
    if extension not in ALLOWED_EXTENSIONS or mime not in ALLOWED_MIMES:
        raise HTTPException(415, "This file type isn't supported")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes: raise HTTPException(413, "File exceeds the configured upload limit")
    if not data: raise HTTPException(400, "File is empty")
    version = await resolve_version(db, principal, processor_id) if processor_id else None
    document_id = uuid.uuid4(); object_key = f"workspaces/{principal.workspace_id}/documents/{document_id}/original"
    await put_bytes(object_key, data, mime)
    user_id = principal.user.id if principal.user else None
    document = Document(id=document_id, workspace_id=principal.workspace_id, original_filename=filename, mime_type=mime,
                        file_size=len(data), sha256=hashlib.sha256(data).hexdigest(), object_key=object_key,
                        selected_processor_id=processor_id, selected_processor_version_id=version.id if version else None,
                        uploaded_by_user_id=user_id, source="api" if principal.api_key else "ui", processing_mode=processing_mode,
                        visual_reader=visual_reader)
    db.add(document); await db.flush(); await transition(db, document, "queued", "Document queued for processing")
    job = ProcessingJob(workspace_id=principal.workspace_id, document_id=document.id, job_type="parse", status="queued", idempotency_key=f"{document.id}:{version.id if version else 'none'}:process:1")
    db.add(job); await audit(db, workspace_id=principal.workspace_id, action="document.uploaded", target_type="document", target_id=document.id, user_id=user_id, api_key_id=principal.api_key.id if principal.api_key else None, metadata={"size": len(data), "mime_type": mime, "processing_mode": processing_mode, "visual_reader": visual_reader})
    await db.commit()
    try: enqueue(document, job); await db.commit()
    except Exception: document.error_message_safe = "Document is queued; the worker is temporarily unavailable."; await db.commit()
    return {"id": document.id, "status": document.status, "filename": filename}


@router.get("/documents")
async def list_documents(principal: WorkspaceAuth, db: DB, status_filter: str | None = Query(None, alias="status"), processor_id: uuid.UUID | None = None,
                         review_required: bool | None = None, search: str | None = None, page_no: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    filters = [Document.workspace_id == principal.workspace_id, Document.deleted_at.is_(None)]
    if status_filter: filters.append(Document.status == status_filter)
    if processor_id: filters.append(Document.selected_processor_id == processor_id)
    if review_required is not None: filters.append(Document.status == "review_required" if review_required else Document.status != "review_required")
    if search: filters.append(Document.original_filename.ilike(f"%{search}%"))
    total = await db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    items = (await db.scalars(select(Document).where(*filters).order_by(desc(Document.created_at)).offset((page_no-1)*page_size).limit(page_size))).all()
    return page([serialize(item, "object_key") for item in items], total, page_no, page_size)


@router.get("/documents/review-queue")
async def review_queue(principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    items = (await db.scalars(select(Document).where(Document.workspace_id == principal.workspace_id, Document.status == "review_required", Document.deleted_at.is_(None)).order_by(Document.created_at))).all()
    return [serialize(item, "object_key") for item in items]


@router.get("/documents/{document_id}")
async def get_document(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id)
    events = (await db.scalars(select(DocumentStatusEvent).where(DocumentStatusEvent.document_id == item.id).order_by(DocumentStatusEvent.created_at))).all()
    latest = await db.scalar(select(ExtractionRun).where(ExtractionRun.document_id == item.id).order_by(desc(ExtractionRun.created_at)))
    result = serialize(item, "object_key"); result["events"] = [serialize(event) for event in events]; result["latest_extraction_id"] = latest.id if latest else None; result["original_url"] = signed_get_url(item.object_key); return result


@router.get("/documents/{document_id}/status")
async def document_status(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id); return {"id": item.id, "status": item.status, "error_code": item.error_code, "error_message": item.error_message_safe, "updated_at": item.updated_at}


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> None:
    require_write(principal); item = await scoped_document(db, principal.workspace_id, document_id); item.deleted_at=now()
    await audit(db, workspace_id=principal.workspace_id, action="document.deleted", target_type="document", target_id=item.id, user_id=principal.user.id if principal.user else None); await db.commit()
    try: await delete_key(item.object_key)
    except Exception: pass


@router.post("/documents/{document_id}/process", status_code=202)
async def reprocess(document_id: uuid.UUID, payload: ProcessIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_document(db, principal.workspace_id, document_id); version = await resolve_version(db, principal, payload.processor_id, payload.processor_version_id)
    item.selected_processor_id, item.selected_processor_version_id, item.error_code, item.error_message_safe = payload.processor_id, version.id, None, None
    if payload.processing_mode is not None: item.processing_mode = payload.processing_mode
    if payload.visual_reader is not None: item.visual_reader = payload.visual_reader
    await transition(db, item, "queued", "Reprocessing requested")
    job = ProcessingJob(workspace_id=principal.workspace_id, document_id=item.id, job_type="parse", status="queued", idempotency_key=f"{item.id}:{version.id}:process:{uuid.uuid4()}")
    db.add(job); await db.commit(); enqueue(item, job); await db.commit(); return {"id": item.id, "status": item.status}


@router.post("/documents/{document_id}/cancel")
async def cancel_document(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_document(db, principal.workspace_id, document_id); await transition(db, item, "cancelled", "Cancelled by user"); await db.commit(); return {"status": "cancelled"}


@router.get("/documents/{document_id}/pages")
async def document_pages(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id)
    run = await db.scalar(select(ParseRun).where(ParseRun.document_id == item.id, ParseRun.status == "succeeded").order_by(desc(ParseRun.created_at)))
    if not run: return {"pages": [], "original_url": signed_get_url(item.object_key)}
    return {"pages": [{"page_number": p["page_number"], "width": p["width"], "height": p["height"], "text": p["text"]} for p in run.canonical_json.get("pages", [])], "original_url": signed_get_url(item.object_key), "mime_type": item.mime_type}


@router.get("/documents/{document_id}/pages/{page_number}")
async def document_page(document_id: uuid.UUID, page_number: int, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id); run = await db.scalar(select(ParseRun).where(ParseRun.document_id == item.id).order_by(desc(ParseRun.created_at)))
    target = next((p for p in (run.canonical_json.get("pages", []) if run else []) if p["page_number"] == page_number), None)
    if not target: raise HTTPException(404, "Page not found")
    return target


@router.get("/documents/{document_id}/parsed-text")
async def parsed_text(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id); run = await db.scalar(select(ParseRun).where(ParseRun.document_id == item.id).order_by(desc(ParseRun.created_at)))
    if not run: raise HTTPException(404, "Parsed content not available")
    return {"text": run.canonical_json.get("text", ""), "markdown": run.canonical_json.get("markdown")}


async def extraction_payload(db: AsyncSession, run: ExtractionRun) -> dict[str, Any]:
    fields = (await db.scalars(select(ExtractionField).where(ExtractionField.extraction_run_id == run.id).order_by(ExtractionField.json_path))).all()
    evidence_rows = (await db.execute(select(FieldEvidence, ExtractionField.json_path).join(ExtractionField).where(ExtractionField.extraction_run_id == run.id))).all()
    evidence = {}
    for row, path in evidence_rows: evidence.setdefault(path, []).append(serialize(row))
    overrides = (await db.scalars(select(ReviewOverride).where(ReviewOverride.extraction_run_id == run.id).order_by(ReviewOverride.created_at))).all()
    validations = (await db.scalars(select(ValidationResult).where(ValidationResult.extraction_run_id == run.id))).all()
    effective = apply_overrides(run.raw_data, overrides)
    return {"id": run.id, "document_id": run.document_id, "provider": run.provider, "model": run.model, "status": run.status,
            "data": run.raw_data, "effective_data": effective,
            "fields": [{**serialize(field), "effective_value": next((o.override_value for o in reversed(overrides) if o.json_path == field.json_path and o.action == "correct"), field.value_json), "evidence": evidence.get(field.json_path, [])} for field in fields],
            "validations": [serialize(item) for item in validations],
            "validation_summary": {"failed": sum(1 for item in validations if not item.passed), "passed": sum(1 for item in validations if item.passed)},
            "review_summary": {"reviewed": len({item.json_path for item in overrides if item.action != "reset"}), "total": len(fields)}}


@router.get("/documents/{document_id}/extractions")
async def extractions(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    item = await scoped_document(db, principal.workspace_id, document_id); runs = (await db.scalars(select(ExtractionRun).where(ExtractionRun.document_id == item.id).order_by(desc(ExtractionRun.created_at)))).all(); return [serialize(run) for run in runs]


@router.get("/documents/{document_id}/extractions/{run_id}")
async def extraction(document_id: uuid.UUID, run_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id); run = await db.scalar(select(ExtractionRun).where(ExtractionRun.id == run_id, ExtractionRun.document_id == item.id))
    if not run: raise HTTPException(404, "Extraction not found")
    return await extraction_payload(db, run)


@router.post("/documents/{document_id}/extractions/{run_id}/retry", status_code=202)
async def retry_extraction(document_id: uuid.UUID, run_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    item = await scoped_document(db, principal.workspace_id, document_id); run = await db.scalar(select(ExtractionRun).where(ExtractionRun.id == run_id, ExtractionRun.document_id == item.id))
    if not run: raise HTTPException(404, "Extraction not found")
    processor_id = await db.scalar(select(ProcessorVersion.processor_id).where(ProcessorVersion.id == run.processor_version_id))
    return await reprocess(document_id, ProcessIn(processor_id=processor_id, processor_version_id=run.processor_version_id), principal, db)


@router.post("/documents/{document_id}/review/fields")
async def review_field(document_id: uuid.UUID, payload: ReviewFieldIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_document(db, principal.workspace_id, document_id)
    run = await db.scalar(select(ExtractionRun).where(ExtractionRun.id == payload.extraction_run_id, ExtractionRun.document_id == item.id))
    if not run: raise HTTPException(404, "Extraction not found")
    field = await db.scalar(select(ExtractionField).where(ExtractionField.extraction_run_id == run.id, ExtractionField.json_path == payload.json_path))
    if not field: raise HTTPException(404, "Field not found")
    if payload.action == "correct" and "value" not in payload.model_fields_set: raise HTTPException(422, "Correct action requires a value")
    override = ReviewOverride(document_id=item.id, extraction_run_id=run.id, json_path=payload.json_path, original_value=field.value_json,
                              override_value=payload.value, action=payload.action, note=payload.note, reviewer_user_id=principal.user.id if principal.user else principal.api_key.created_by_user_id)
    db.add(override); field.review_state = {"correct": "corrected", "approve": "approved", "reject": "rejected", "reset": "pending"}[payload.action]
    await audit(db, workspace_id=principal.workspace_id, action=f"review.{payload.action}", target_type="extraction_field", target_id=field.id, user_id=principal.user.id if principal.user else None, metadata={"path": payload.json_path})
    await db.commit(); return serialize(override)


@router.post("/documents/{document_id}/review/approve")
async def approve_document(document_id: uuid.UUID, payload: ApprovalIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item = await scoped_document(db, principal.workspace_id, document_id)
    run = await db.scalar(select(ExtractionRun).where(ExtractionRun.id == payload.extraction_run_id, ExtractionRun.document_id == item.id))
    if not run: raise HTTPException(404, "Extraction not found")
    approval = DocumentApproval(document_id=item.id, extraction_run_id=run.id, approved_by_user_id=principal.user.id if principal.user else principal.api_key.created_by_user_id, note=payload.note)
    db.add(approval); await transition(db, item, "completed", "Approved by reviewer"); await audit(db, workspace_id=principal.workspace_id, action="document.approved", target_type="document", target_id=item.id, user_id=principal.user.id if principal.user else None); await db.commit()
    await emit(principal.workspace_id, "document.approved", {"event": "document.approved", "document_id": str(item.id), "workspace_id": str(principal.workspace_id)})
    return serialize(approval)


async def effective_for_document(db: AsyncSession, item: Document) -> tuple[ExtractionRun, dict[str, Any]]:
    run = await db.scalar(select(ExtractionRun).where(ExtractionRun.document_id == item.id, ExtractionRun.status == "succeeded").order_by(desc(ExtractionRun.created_at)))
    if not run: raise HTTPException(404, "Extraction not available")
    overrides = (await db.scalars(select(ReviewOverride).where(ReviewOverride.extraction_run_id == run.id).order_by(ReviewOverride.created_at))).all()
    return run, apply_overrides(run.raw_data, overrides)


@router.get("/documents/{document_id}/export/json")
async def export_json(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> JSONResponse:
    item = await scoped_document(db, principal.workspace_id, document_id); run, data = await effective_for_document(db, item)
    return JSONResponse(data, headers={
        "Content-Disposition": f'attachment; filename="{item.id}-{run.id}.json"',
        "Cache-Control": "no-store, max-age=0",
    })


@router.get("/documents/{document_id}/export/csv")
async def export_csv(document_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> StreamingResponse:
    item = await scoped_document(db, principal.workspace_id, document_id); run, data = await effective_for_document(db, item)
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["field", "value"])
    def flatten(value: Any, path: str = ""):
        if isinstance(value, dict):
            for key, child in value.items(): yield from flatten(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list): yield path, json.dumps(value, ensure_ascii=False)
        else: yield path, value
    writer.writerows(flatten(data)); return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="{item.id}-{run.id}.csv"',
        "Cache-Control": "no-store, max-age=0",
    })


@router.get("/api-keys")
async def api_keys(principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    require_admin(principal); items = (await db.scalars(select(ApiKey).where(ApiKey.workspace_id == principal.workspace_id).order_by(desc(ApiKey.created_at)))).all(); return [serialize(item, "key_hash") for item in items]


@router.post("/api-keys", status_code=201)
async def create_api_key(payload: ApiKeyIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_admin(principal); plaintext = opaque_token("hdl_live_"); user_id = principal.user.id if principal.user else principal.api_key.created_by_user_id
    item = ApiKey(workspace_id=principal.workspace_id, name=payload.name, key_prefix=plaintext[:18], key_hash=token_hash(plaintext), expires_at=payload.expires_at, created_by_user_id=user_id)
    db.add(item); await db.commit(); result=serialize(item, "key_hash"); result["key"] = plaintext; return result


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> None:
    require_admin(principal); item = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == principal.workspace_id))
    if not item: raise HTTPException(404, "API key not found")
    item.revoked_at=now(); await db.commit()


@router.get("/webhooks")
async def webhooks(principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    require_admin(principal); return [serialize(item, "secret_encrypted_or_managed") for item in (await db.scalars(select(Webhook).where(Webhook.workspace_id == principal.workspace_id))).all()]


@router.post("/webhooks", status_code=201)
async def create_webhook(payload: WebhookIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_admin(principal)
    try: validate_webhook_url(str(payload.url))
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    secret = secrets.token_urlsafe(32); user_id=principal.user.id if principal.user else principal.api_key.created_by_user_id
    item=Webhook(workspace_id=principal.workspace_id, name=payload.name, url=str(payload.url), secret_encrypted_or_managed=secret.encode(), events=payload.events, enabled=payload.enabled, created_by_user_id=user_id)
    db.add(item); await db.commit(); result=serialize(item, "secret_encrypted_or_managed"); result["secret"] = secret; return result


@router.patch("/webhooks/{webhook_id}")
async def patch_webhook(webhook_id: uuid.UUID, payload: WebhookPatch, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_admin(principal); item=await db.scalar(select(Webhook).where(Webhook.id==webhook_id, Webhook.workspace_id==principal.workspace_id))
    if not item: raise HTTPException(404, "Webhook not found")
    values=payload.model_dump(exclude_unset=True); 
    if "url" in values: validate_webhook_url(str(values["url"])); values["url"]=str(values["url"])
    for key,value in values.items(): setattr(item,key,value)
    await db.commit(); return serialize(item,"secret_encrypted_or_managed")


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> None:
    require_admin(principal); item=await db.scalar(select(Webhook).where(Webhook.id==webhook_id, Webhook.workspace_id==principal.workspace_id))
    if not item: raise HTTPException(404,"Webhook not found")
    await db.delete(item); await db.commit()


@router.get("/webhooks/{webhook_id}/deliveries")
async def webhook_deliveries(webhook_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    require_admin(principal); hook=await db.scalar(select(Webhook).where(Webhook.id==webhook_id, Webhook.workspace_id==principal.workspace_id))
    if not hook: raise HTTPException(404,"Webhook not found")
    return [serialize(item) for item in (await db.scalars(select(WebhookDelivery).where(WebhookDelivery.webhook_id==hook.id).order_by(desc(WebhookDelivery.created_at)))).all()]


@router.post("/webhooks/{webhook_id}/test", status_code=202)
async def test_webhook(webhook_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_admin(principal); hook=await db.scalar(select(Webhook).where(Webhook.id==webhook_id, Webhook.workspace_id==principal.workspace_id))
    if not hook: raise HTTPException(404,"Webhook not found")
    delivery=WebhookDelivery(webhook_id=hook.id,event_type="webhook.test",payload={"event":"webhook.test","created_at":now().isoformat()},status="pending"); db.add(delivery); await db.commit(); return serialize(delivery)


@router.get("/workflow-rules")
async def workflow_rules(principal: WorkspaceAuth, db: DB) -> list[dict[str, Any]]:
    return [serialize(item) for item in (await db.scalars(select(WorkflowRule).where(WorkflowRule.workspace_id == principal.workspace_id).order_by(desc(WorkflowRule.updated_at)))).all()]


@router.post("/workflow-rules", status_code=201)
async def create_workflow(payload: WorkflowIn, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item=WorkflowRule(workspace_id=principal.workspace_id, **payload.model_dump()); db.add(item); await db.commit(); return serialize(item)


@router.patch("/workflow-rules/{rule_id}")
async def patch_workflow(rule_id: uuid.UUID, payload: WorkflowPatch, principal: WorkspaceAuth, db: DB) -> dict[str, Any]:
    require_write(principal); item=await db.scalar(select(WorkflowRule).where(WorkflowRule.id==rule_id, WorkflowRule.workspace_id==principal.workspace_id))
    if not item: raise HTTPException(404,"Workflow rule not found")
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    await db.commit(); return serialize(item)


@router.delete("/workflow-rules/{rule_id}", status_code=204)
async def delete_workflow(rule_id: uuid.UUID, principal: WorkspaceAuth, db: DB) -> None:
    require_write(principal); item=await db.scalar(select(WorkflowRule).where(WorkflowRule.id==rule_id, WorkflowRule.workspace_id==principal.workspace_id))
    if not item: raise HTTPException(404,"Workflow rule not found")
    await db.delete(item); await db.commit()


@router.get("/dashboard/summary")
async def dashboard(principal: WorkspaceAuth, db: DB, range_value: str = Query("30d", alias="range")) -> dict[str, Any]:
    days = 7 if range_value == "7d" else 30; since=now()-timedelta(days=days)
    rows=(await db.execute(select(Document.status,func.count()).where(Document.workspace_id==principal.workspace_id,Document.deleted_at.is_(None),Document.created_at>=since).group_by(Document.status))).all()
    counts={key:value for key,value in rows}; total=sum(counts.values()); success=counts.get("completed",0)
    pages=await db.scalar(select(func.coalesce(func.sum(Document.page_count),0)).where(Document.workspace_id==principal.workspace_id,Document.created_at>=since)) or 0
    avg_ms=await db.scalar(select(func.avg(ExtractionRun.latency_ms)).join(Document,Document.id==ExtractionRun.document_id).where(Document.workspace_id==principal.workspace_id,ExtractionRun.created_at>=since)) or 0
    recent=(await db.scalars(select(Document).where(Document.workspace_id==principal.workspace_id,Document.deleted_at.is_(None)).order_by(desc(Document.created_at)).limit(8))).all()
    return {"range":range_value,"documents_processed":total,"review_queue":counts.get("review_required",0),"success_rate":round(success/total*100,1) if total else 0,
            "average_processing_ms":round(float(avg_ms)),"pages_processed":int(pages),"failure_count":counts.get("failed",0),"status_counts":counts,"recent_documents":[serialize(item,"object_key") for item in recent]}
