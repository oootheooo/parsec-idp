import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ApiKey, Role, User, WorkspaceMember
from app.security import decode_access_token, token_hash

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User | None
    api_key: ApiKey | None
    workspace_id: uuid.UUID | None = None
    role: Role | None = None


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Principal:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    if token.startswith("hdl_live_"):
        key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == token_hash(token)))
        if not key or key.revoked_at or (key.expires_at and key.expires_at <= datetime.now(timezone.utc)):
            raise HTTPException(status_code=401, detail="Invalid API key")
        key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return Principal(user=None, api_key=key, workspace_id=key.workspace_id, role=Role.admin)
    try:
        user_id = uuid.UUID(decode_access_token(token))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return Principal(user=user, api_key=None)


async def workspace_context(
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> Principal:
    if principal.api_key:
        return principal
    if not x_workspace_id:
        raise HTTPException(status_code=400, detail="X-Workspace-ID header is required")
    try:
        workspace_id = uuid.UUID(x_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid workspace ID") from exc
    assert principal.user is not None
    membership = await db.get(WorkspaceMember, (workspace_id, principal.user.id))
    if not membership:
        raise HTTPException(status_code=404, detail="Workspace not found")
    principal.workspace_id = workspace_id
    principal.role = membership.role
    return principal


def require_write(principal: Principal) -> None:
    if principal.role == Role.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only role")


def require_admin(principal: Principal) -> None:
    if principal.role not in {Role.owner, Role.admin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

DB = Annotated[AsyncSession, Depends(get_db)]
Auth = Annotated[Principal, Depends(get_principal)]
WorkspaceAuth = Annotated[Principal, Depends(workspace_context)]
