import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_handl.db"
os.environ["APP_ENV"] = "test"
os.environ["EXTRACTION_PROVIDER"] = "mock"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

import pytest
from fastapi.testclient import TestClient

from app import api as api_module
from app.db import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
async def clean_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
def client(monkeypatch):
    async def fake_put(*args, **kwargs):
        return None

    monkeypatch.setattr(api_module, "put_bytes", fake_put)
    monkeypatch.setattr(api_module, "enqueue", lambda *args: None)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def account(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "owner@example.com", "password": "a-very-secure-password",
        "display_name": "Owner", "workspace_name": "Acme Operations",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).json()
    workspace_id = me["workspaces"][0]["id"]
    return {"token": token, "workspace_id": workspace_id,
            "headers": {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}}

