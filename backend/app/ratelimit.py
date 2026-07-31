"""IP-based rate limiting for the public demo.

The endpoints are intentionally unauthenticated so the demo is one click, which
means the LLM-backed routes need a hard cap. Requests carrying a valid
X-API-Key bypass the cap. Counters live in Postgres when available (so they
survive Render's free-tier restarts) with an in-process fallback.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from . import db
from .config import settings
from .services.textkit import sha

WINDOW_SECONDS = 24 * 3600
_local: dict[str, deque[float]] = defaultdict(deque)


def client_hash(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return sha("fitscope-client", ip)[:32]


def _has_api_key(request: Request) -> bool:
    key = request.headers.get("x-api-key", "").strip()
    return bool(key) and key in settings.api_key_set


async def enforce(request: Request) -> str:
    """Consume one unit of quota. Returns the client hash for audit columns."""
    digest = client_hash(request)
    if _has_api_key(request) or settings.rate_limit_per_day <= 0:
        return digest

    if db.enabled():
        row = await db.fetch_one(
            """
            SELECT count(*) AS used FROM rate_limit_events
            WHERE client_hash = %s AND created_at > now() - interval '24 hours'
            """,
            (digest,),
        )
        used = int((row or {}).get("used", 0) or 0)
        if used >= settings.rate_limit_per_day:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily demo limit of {settings.rate_limit_per_day} analyses reached. "
                    "Self-host or use an API key for unlimited runs."
                ),
                headers={"Retry-After": "3600"},
            )
        await db.execute("INSERT INTO rate_limit_events (client_hash) VALUES (%s)", (digest,))
        return digest

    now = time.time()
    bucket = _local[digest]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily demo limit of {settings.rate_limit_per_day} analyses reached.",
            headers={"Retry-After": "3600"},
        )
    bucket.append(now)
    return digest


async def remaining(request: Request) -> int | None:
    if _has_api_key(request) or settings.rate_limit_per_day <= 0:
        return None
    digest = client_hash(request)
    if db.enabled():
        row = await db.fetch_one(
            """
            SELECT count(*) AS used FROM rate_limit_events
            WHERE client_hash = %s AND created_at > now() - interval '24 hours'
            """,
            (digest,),
        )
        used = int((row or {}).get("used", 0) or 0)
    else:
        now = time.time()
        used = sum(1 for t in _local.get(digest, ()) if now - t <= WINDOW_SECONDS)
    return max(0, settings.rate_limit_per_day - used)
