"""FastAPI app for «Нейро-шеф Гурмикс».

Lifespan: setup logging, seed Claude token file (optional), create tables,
assert_schema_ready. Mounts all routers under /api/v1. CORS for dev
(localhost:5173). Serves the built SPA from ../frontend/dist if present.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.version import APP_VERSION

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Optional: seed Claude OAuth token from env (no-op if absent).
    try:
        from app.core.claude_token import init_token_file

        init_token_file()
    except Exception:  # noqa: BLE001
        logger.warning("Claude token init skipped", exc_info=True)

    # Register models + create tables, then fail-fast on a broken schema.
    from app.core.database import create_tables
    from app.core.migrations import assert_schema_ready

    create_tables()
    assert_schema_ready(expected=["usage_counters", "distributors", "query_logs"])

    # Прогреть RAG-индекс ассортимента (модуль 1). Lazy-фолбэк — не валим старт.
    try:
        from app.rag import index as rag_index

        logger.info("RAG ассортимент: %d документов", rag_index.warm())
    except Exception:  # noqa: BLE001
        logger.warning("RAG warm skipped", exc_info=True)

    logger.info("Гурмикс backend ready.")

    yield


app = FastAPI(
    title="Нейро-шеф Гурмикс API",
    description="Веб-чат-бот с 8 модулями-экспертами для компании «Гурмикс».",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (под /api/v1) ────────────────────────────────────────────────────
from app.api import chat as chat_router  # noqa: E402
from app.api import modules as modules_router  # noqa: E402
from app.api.admin import router as admin_router  # noqa: E402

app.include_router(modules_router.router, prefix="/api/v1")
app.include_router(chat_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/api/v1/version")
async def app_version() -> dict:
    return {"name": "Нейро-шеф Гурмикс", "version": APP_VERSION}


# ── Serve built SPA from ../frontend/dist if present ─────────────────────────
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "health", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
