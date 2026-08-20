import json
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Webhook, WebhookDelivery
from app.security import validate_webhook_url, webhook_signature


async def create_deliveries(workspace_id: uuid.UUID, event_type: str, payload: dict) -> list[uuid.UUID]:
    async with SessionLocal() as db:
        hooks = (await db.scalars(select(Webhook).where(Webhook.workspace_id == workspace_id, Webhook.enabled))).all()
        ids = []
        for hook in hooks:
            if event_type in hook.events:
                item = WebhookDelivery(webhook_id=hook.id, event_type=event_type, payload=payload, status="pending")
                db.add(item); await db.flush(); ids.append(item.id)
        await db.commit()
        return ids


async def emit(workspace_id: uuid.UUID, event_type: str, payload: dict) -> None:
    ids = await create_deliveries(workspace_id, event_type, payload)
    if ids:
        from app.worker import deliver_webhook_task
        for delivery_id in ids:
            deliver_webhook_task.delay(str(delivery_id))


async def deliver(delivery_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        delivery = await db.get(WebhookDelivery, delivery_id)
        if not delivery: return
        hook = await db.get(Webhook, delivery.webhook_id)
        if not hook or not hook.enabled: delivery.status = "cancelled"; await db.commit(); return
        body = json.dumps(delivery.payload, separators=(",", ":"), default=str).encode()
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        secret = hook.secret_encrypted_or_managed.decode()
        headers = {"Content-Type": "application/json", "X-Handl-Event": delivery.event_type,
                   "X-Handl-Delivery-ID": str(delivery.id), "X-Handl-Timestamp": timestamp,
                   "X-Handl-Signature": webhook_signature(secret, timestamp, body)}
        try:
            validate_webhook_url(hook.url)
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                response = await client.post(hook.url, content=body, headers=headers)
            delivery.attempt += 1; delivery.response_status = response.status_code; delivery.response_excerpt = response.text[:500]
            if 200 <= response.status_code < 300: delivery.status = "delivered"; delivery.delivered_at = datetime.now(timezone.utc)
            else: delivery.status = "retrying" if response.status_code >= 500 else "failed"
        except Exception:
            delivery.attempt += 1; delivery.status = "retrying"; delivery.response_excerpt = "Delivery failed safely"
        await db.commit()
