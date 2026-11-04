import asyncio
from collections.abc import Coroutine
from typing import Any

from celery import Celery
from celery.signals import worker_process_shutdown

from app.config import settings
from app.db import engine
from app.services.processing import process_document
from app.services.webhooks import deliver

celery_app = Celery("parsec", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_serializer="json", accept_content=["json"], result_serializer="json",
                       task_always_eager=settings.celery_task_always_eager, task_routes={"app.worker.process_document_task": {"queue": "document_parse"}})

_worker_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    """Run all async work on one process-local loop so pooled DB connections stay valid."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    _worker_loop.run_until_complete(coro)


@worker_process_shutdown.connect
def close_worker_loop(**_: Any) -> None:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        return
    _worker_loop.run_until_complete(engine.dispose())
    _worker_loop.close()
    _worker_loop = None


@celery_app.task(name="app.worker.process_document_task", bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def process_document_task(self, document_id: str) -> None:
    run_async(process_document(__import__("uuid").UUID(document_id)))


@celery_app.task(name="app.worker.deliver_webhook_task", bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=5)
def deliver_webhook_task(self, delivery_id: str) -> None:
    run_async(deliver(__import__("uuid").UUID(delivery_id)))
