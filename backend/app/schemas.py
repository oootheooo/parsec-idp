import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=1, max_length=160)
    workspace_name: str = Field(min_length=1, max_length=160)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WorkspaceOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str | None = None


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    workspaces: list[WorkspaceOut]


class ProcessorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    template_key: str | None = None
    schema_json: dict[str, Any] | None = None  # type: ignore[assignment]
    instructions: str = ""


class ProcessorPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None


class VersionCreate(BaseModel):
    schema_json: dict[str, Any] | None = None  # type: ignore[assignment]
    instructions: str | None = None
    validation_config: list[dict[str, Any]] | None = None
    review_config: dict[str, Any] | None = None
    extraction_config: dict[str, Any] | None = None


class VersionPatch(VersionCreate):
    pass


class SchemaAssistIn(BaseModel):
    description: str = Field(min_length=3, max_length=4000)
    sample_context: str | None = Field(default=None, max_length=5000)


class ReviewFieldIn(BaseModel):
    extraction_run_id: uuid.UUID
    json_path: str
    action: Literal["approve", "reject", "correct", "reset"]
    value: Any = None
    note: str | None = Field(default=None, max_length=1000)


class ApprovalIn(BaseModel):
    extraction_run_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class ProcessIn(BaseModel):
    processor_id: uuid.UUID
    processor_version_id: uuid.UUID | None = None
    processing_mode: Literal["smart", "native", "visual", "docling"] | None = None
    visual_reader: Literal["ocr", "vision"] | None = None


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    expires_at: datetime | None = None


class WebhookIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    events: list[str]
    enabled: bool = True


class WebhookPatch(BaseModel):
    name: str | None = None
    url: HttpUrl | None = None
    events: list[str] | None = None
    enabled: bool | None = None


class WorkflowIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    processor_id: uuid.UUID | None = None
    trigger: Literal["extraction_completed", "document_approved"]
    conditions: dict[str, Any] = {}
    actions: list[dict[str, Any]] = []


class WorkflowPatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    processor_id: uuid.UUID | None = None
    trigger: Literal["extraction_completed", "document_approved"] | None = None
    conditions: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None
