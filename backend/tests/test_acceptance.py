import uuid

import pymupdf as fitz
import pytest

from app.db import SessionLocal
from app.models import ApiKey
from app.services import processing


def create_published_processor(client, headers):
    created = client.post("/api/v1/processors", headers=headers, json={
        "name": "Invoice", "description": "Invoice fields",
        "schema_json": {"type": "object", "additionalProperties": False,
                        "properties": {"invoice_number": {"type": ["string", "null"]},
                                       "total": {"type": ["number", "null"]}},
                        "required": ["invoice_number", "total"]},
        "instructions": "Extract invoice number and total",
    }).json()
    published = client.post(
        f"/api/v1/processors/{created['id']}/versions/{created['draft_version_id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    immutable = client.patch(
        f"/api/v1/processors/{created['id']}/versions/{created['draft_version_id']}",
        headers=headers, json={"instructions": "changed"},
    )
    assert immutable.status_code == 409
    return created


def test_register_login_processor_and_tenant_isolation(client, account):
    processor = create_published_processor(client, account["headers"])
    login = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "a-very-secure-password"})
    assert login.status_code == 200
    other = client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "another-secure-password",
        "display_name": "Other", "workspace_name": "Other Company"})
    token = other.json()["access_token"]
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).json()
    forbidden = client.get(f"/api/v1/processors/{processor['id']}", headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": me["workspaces"][0]["id"]})
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_pdf_pipeline_review_approval_export_and_api_key(client, account, monkeypatch):
    processor = create_published_processor(client, account["headers"])
    pdf = fitz.open(); page = pdf.new_page(); page.insert_text((72, 72), "Invoice Number INV-1042   Total 125.00"); pdf_bytes = pdf.tobytes()
    uploaded = client.post(f"/api/v1/documents/upload?processor_id={processor['id']}", headers=account["headers"],
                           files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")})
    assert uploaded.status_code == 202
    document_id = uploaded.json()["id"]
    async def fake_get_bytes(key): return pdf_bytes
    monkeypatch.setattr(processing, "get_bytes", fake_get_bytes)
    await processing.process_document(uuid.UUID(document_id))
    detail = client.get(f"/api/v1/documents/{document_id}", headers=account["headers"]).json()
    assert detail["status"] == "review_required"
    assert detail["page_count"] == 1
    extraction = client.get(f"/api/v1/documents/{document_id}/extractions/{detail['latest_extraction_id']}", headers=account["headers"]).json()
    assert any(field["json_path"] == "$.total" for field in extraction["fields"])
    corrected = client.post(f"/api/v1/documents/{document_id}/review/fields", headers=account["headers"], json={
        "extraction_run_id": extraction["id"], "json_path": "$.total", "action": "correct", "value": 125.0})
    assert corrected.status_code == 200
    after = client.get(f"/api/v1/documents/{document_id}/extractions/{extraction['id']}", headers=account["headers"]).json()
    assert after["data"]["total"] is None
    assert after["effective_data"]["total"] == 125.0
    approved = client.post(f"/api/v1/documents/{document_id}/review/approve", headers=account["headers"], json={"extraction_run_id": extraction["id"]})
    assert approved.status_code == 200
    exported = client.get(f"/api/v1/documents/{document_id}/export/json", headers=account["headers"])
    assert exported.json()["total"] == 125.0
    key_response = client.post("/api/v1/api-keys", headers=account["headers"], json={"name": "CI"})
    plaintext = key_response.json()["key"]
    async with SessionLocal() as db:
        stored = await db.get(ApiKey, uuid.UUID(key_response.json()["id"]))
        assert plaintext not in stored.key_hash
    api_headers = {"Authorization": f"Bearer {plaintext}"}
    assert client.get("/api/v1/documents", headers=api_headers).status_code == 200
    assert client.delete(f"/api/v1/api-keys/{key_response.json()['id']}", headers=account["headers"]).status_code == 204
    assert client.get("/api/v1/documents", headers=api_headers).status_code == 401
