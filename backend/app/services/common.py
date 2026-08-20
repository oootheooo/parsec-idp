import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, Document, DocumentStatusEvent


def slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"
    return f"{base}-{uuid.uuid4().hex[:6]}"


async def audit(
    db: AsyncSession,
    *, workspace_id: uuid.UUID, action: str, target_type: str,
    target_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None, metadata: dict[str, Any] | None = None,
) -> None:
    db.add(AuditEvent(workspace_id=workspace_id, actor_user_id=user_id, actor_api_key_id=api_key_id,
                      action=action, target_type=target_type, target_id=target_id, metadata_json=metadata or {}))


async def transition(db: AsyncSession, document: Document, to_status: str, message: str | None = None) -> None:
    previous = document.status
    document.status = to_status
    db.add(DocumentStatusEvent(document_id=document.id, from_status=previous, to_status=to_status, message=message, metadata_json={}))

