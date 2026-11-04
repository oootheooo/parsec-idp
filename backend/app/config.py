from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: str = "development-secret-change-me-32-characters"
    frontend_url: str = "http://localhost:5173"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    database_url: str = "postgresql+asyncpg://parsec:parsec@localhost:5432/parsec"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_public_endpoint_url: str | None = None
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "parsec-documents"
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True
    jwt_secret: str = "development-jwt-change-me-32-characters"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    openai_api_key: str | None = None
    openai_extraction_model: str = "gpt-4.1-mini"
    openai_schema_model: str = "gpt-4.1-mini"
    openai_request_timeout_seconds: float = 120.0
    openai_max_retries: int = 0
    extraction_provider: Literal["mock", "openai"] = "mock"
    max_upload_bytes: int = 52_428_800
    max_document_pages: int = 200
    signed_url_ttl_seconds: int = 900
    webhook_master_key: str | None = None
    allow_private_webhook_urls: bool = True
    celery_task_always_eager: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
