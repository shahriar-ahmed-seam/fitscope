"""Postgres (Neon) access layer.

Everything degrades gracefully: if DATABASE_URL is unset the API still serves
analyses, it just cannot persist shareable reports or cache provider calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterable
from typing import Any

from psycopg import AsyncConnection, OperationalError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import settings

log = logging.getLogger("fitscope.db")

_pool: AsyncConnectionPool | None = None

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS analyses (
    id              BIGSERIAL PRIMARY KEY,
    public_id       TEXT UNIQUE NOT NULL,
    role_title      TEXT,
    company         TEXT,
    overall_score   REAL,
    semantic_score  REAL,
    ats_score       REAL,
    verdict         TEXT,
    report          JSONB NOT NULL,
    resume_chars    INTEGER,
    jd_chars        INTEGER,
    duration_ms     INTEGER,
    client_hash     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analyses_created_idx ON analyses (created_at DESC);

CREATE TABLE IF NOT EXISTS jd_index (
    id          BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT REFERENCES analyses (id) ON DELETE CASCADE,
    role_title  TEXT,
    summary     TEXT,
    embedding   VECTOR(%(dim)s),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS provider_cache (
    cache_key  TEXT PRIMARY KEY,
    provider   TEXT NOT NULL,
    payload    JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_events (
    id                BIGSERIAL PRIMARY KEY,
    provider          TEXT NOT NULL,
    model             TEXT,
    operation         TEXT,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    cached_tokens     INTEGER DEFAULT 0,
    latency_ms        INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS usage_created_idx ON usage_events (created_at DESC);

CREATE TABLE IF NOT EXISTS rate_limit_events (
    id          BIGSERIAL PRIMARY KEY,
    client_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rate_limit_lookup_idx
    ON rate_limit_events (client_hash, created_at DESC);
"""


def _normalise_dsn(dsn: str) -> str:
    dsn = dsn.strip()
    if dsn.startswith("postgresql+"):  # tolerate SQLAlchemy-style URLs
        dsn = "postgresql://" + dsn.split("://", 1)[1]
    if dsn and "sslmode=" not in dsn and "localhost" not in dsn and "127.0.0.1" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    return dsn


def enabled() -> bool:
    return bool(settings.database_url.strip())


async def connect() -> None:
    """Open the pool and make sure the schema exists."""
    global _pool
    if not enabled() or _pool is not None:
        return
    # Neon suspends idle compute and drops connections, so pooled connections are
    # health-checked before use and retired well before the server closes them.
    _pool = AsyncConnectionPool(
        _normalise_dsn(settings.database_url),
        min_size=0,
        max_size=4,
        open=False,
        timeout=20,
        max_idle=45.0,
        max_lifetime=240.0,
        reconnect_timeout=20.0,
        check=AsyncConnectionPool.check_connection,
        kwargs={"row_factory": dict_row, "connect_timeout": 15},
    )
    await _pool.open(wait=True, timeout=30)
    async with _pool.connection() as conn:
        await conn.execute(SCHEMA % {"dim": settings.voyage_embed_dim})
    log.info("database ready")


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


class _NullCtx:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc: object) -> None:
        return None


def connection():
    """Async context manager yielding a connection, or None when disabled."""
    if _pool is None:
        return _NullCtx()
    return _pool.connection()


async def _run(sql: str, params: Iterable[Any] | None, fetch: bool) -> list[dict]:
    """Execute a statement, retrying once when a pooled connection was dropped."""
    if _pool is None:
        return []
    last: Exception | None = None
    for attempt in range(2):
        try:
            async with _pool.connection() as conn:
                cur = await conn.execute(sql, params)
                return list(await cur.fetchall()) if fetch else []
        except OperationalError as exc:
            last = exc
            log.warning("database connection dropped (attempt %s): %s", attempt + 1, exc)
            await asyncio.sleep(0.4)
    raise last if last else RuntimeError("database call failed")


async def fetch_all(sql: str, params: Iterable[Any] | None = None) -> list[dict]:
    return await _run(sql, params, fetch=True)


async def fetch_one(sql: str, params: Iterable[Any] | None = None) -> dict | None:
    rows = await fetch_all(sql, params)
    return rows[0] if rows else None


async def execute(sql: str, params: Iterable[Any] | None = None) -> None:
    await _run(sql, params, fetch=False)


async def cache_get(key: str) -> Any | None:
    row = await fetch_one("SELECT payload FROM provider_cache WHERE cache_key = %s", (key,))
    if not row:
        return None
    payload = row["payload"]
    return json.loads(payload) if isinstance(payload, str) else payload


async def cache_put(key: str, provider: str, payload: Any) -> None:
    await execute(
        """
        INSERT INTO provider_cache (cache_key, provider, payload)
        VALUES (%s, %s, %s::jsonb)
        ON CONFLICT (cache_key) DO NOTHING
        """,
        (key, provider, json.dumps(payload)),
    )


async def log_usage(
    provider: str,
    model: str,
    operation: str,
    usage: dict[str, int] | None = None,
    latency_ms: int = 0,
) -> None:
    usage = usage or {}
    await execute(
        """
        INSERT INTO usage_events (provider, model, operation, prompt_tokens,
            completion_tokens, total_tokens, cached_tokens, latency_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            provider,
            model,
            operation,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
            usage.get("cached_tokens", 0),
            latency_ms,
        ),
    )


AsyncConnectionAlias = AsyncConnection
