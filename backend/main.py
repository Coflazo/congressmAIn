"""AI020 — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db
from routers import admin, chat, meetings, subscribers, webhook
from services.translate import check_libretranslate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    init_db()
    yield
    # Shutdown (nothing to clean up yet)


app = FastAPI(
    title="AI020 Meeting Summarizer",
    description="Turns Dutch government meeting transcripts into plain-language multilingual summaries.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(chat.router, prefix="/api/meetings", tags=["chat"])
app.include_router(subscribers.router, prefix="/api/subscribers", tags=["subscribers"])
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


def _structured_error(code: str, message: str, detail: object | None = None, status_code: int = 500) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "detail": detail}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    code = message.lower().replace(" ", "_")
    return _structured_error(code, message, detail=detail, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _structured_error("internal_error", "Internal server error", detail=str(exc), status_code=500)


# ── Health ─────────────────────────────────────────────────────────────────────
async def _health_response() -> JSONResponse:
    lt_ok = check_libretranslate()
    return JSONResponse(
        content={
            "status": "ok",
            "libretranslate": "reachable" if lt_ok else "unreachable",
        },
        status_code=200 if lt_ok else 503,
    )


@app.get("/health")
async def health() -> JSONResponse:
    return await _health_response()


@app.get("/api/health")
async def api_health() -> JSONResponse:
    return await _health_response()
