import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import router
from app.config import settings
from app.db import SessionLocal

app = FastAPI(title="Parsec API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id=request.headers.get("X-Request-ID",str(uuid.uuid4())); started=time.monotonic()
    try: response=await call_next(request)
    except Exception:
        logging.exception("unhandled_request_error", extra={"request_id":request_id,"path":request.url.path})
        return JSONResponse(status_code=500,content={"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred","details":{},"request_id":request_id}})
    response.headers["X-Request-ID"]=request_id; response.headers["X-Response-Time-MS"]=str(round((time.monotonic()-started)*1000)); return response


@app.get("/health")
async def health(): return {"status":"ok","service":"parse-api"}


@app.get("/ready")
async def ready():
    try:
        async with SessionLocal() as db: await db.execute(text("SELECT 1"))
        return {"status":"ready","database":"ok"}
    except Exception: return JSONResponse(status_code=503,content={"status":"not_ready","database":"unavailable"})
