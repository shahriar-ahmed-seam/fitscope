"""FitScope API entrypoint."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db
from .config import settings
from .routers import analyze, meta, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("fitscope")

DESCRIPTION = """
Resume ↔ job-description fit intelligence.

Two independent scores per run:

* **Semantic fit** — every JD requirement is matched against your resume with
  embedding retrieval plus a cross-encoder reranker, then labelled
  `covered` / `partial` / `missing` **with the exact resume line used as evidence**.
* **ATS readiness** — deterministic, rule-based document mechanics
  (parseability, contact block, headings, dates, quantification, keyword coverage).

The public demo is unauthenticated and IP rate limited. Send `X-API-Key` to bypass
the cap when self-hosting. `GET /api/v1/scoring` returns the exact weights used.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await db.connect()
    except Exception as exc:
        log.error("database unavailable, running stateless: %s", exc)
    yield
    await db.disconnect()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={"name": "Shahriar Ahmed Seam", "url": "https://github.com/shahriar-ahmed-seam"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.0f}ms"
    if request.url.path.startswith("/api/"):
        log.info("%s %s -> %s in %.0fms", request.method, request.url.path,
                 response.status_code, elapsed_ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal error while processing the request."},
    )


app.include_router(meta.router)
app.include_router(analyze.router)
app.include_router(reports.router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
