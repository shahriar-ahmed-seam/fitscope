"""Health, capability and usage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from .. import db
from ..config import settings
from ..ratelimit import remaining
from ..services import llm, retrieval

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    """Liveness plus which capabilities are actually wired up."""
    database_ok = False
    if db.enabled():
        try:
            await db.fetch_one("SELECT 1 AS ok")
            database_ok = True
        except Exception:
            database_ok = False
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "capabilities": {
            "llm": llm.configured(),
            "embeddings": retrieval.configured(),
            "coverage_judge": settings.judge_enabled and llm.configured(),
            "reranker": retrieval.rerank_available(),
            "database": database_ok,
            "shareable_reports": database_ok,
        },
        "models": {
            "llm": settings.deepseek_model if llm.configured() else None,
            "embeddings": settings.voyage_embed_model if retrieval.configured() else "lexical-idf",
            "reranker": settings.voyage_rerank_model if retrieval.rerank_available() else None,
        },
    }


@router.get("/api/v1/quota")
async def quota(request: Request) -> dict:
    left = await remaining(request)
    return {
        "limit": settings.rate_limit_per_day,
        "remaining": left,
        "unlimited": left is None,
    }


@router.get("/api/v1/scoring")
async def scoring() -> dict:
    """The exact weights and thresholds behind the scores (kept honest and public)."""
    return {
        "overall": {
            "semantic_fit_weight": settings.semantic_weight,
            "ats_readiness_weight": settings.ats_weight,
        },
        "requirement_weights": settings.weights,
        "coverage_values": {"covered": 1.0, "partial": 0.5, "missing": 0.0},
        "coverage_decided_by": (
            "llm-judge grounded on retrieved candidate lines"
            if settings.judge_enabled
            else "similarity thresholds"
        ),
        "fallback_thresholds": {
            "covered_at_or_above": settings.covered_threshold,
            "partial_at_or_above": settings.partial_threshold,
        },
        "candidates_per_requirement": settings.judge_candidates_per_requirement,
    }


@router.get("/api/v1/metrics")
async def metrics() -> dict:
    """Aggregate provider usage and latency, for the cost/observability panel."""
    if not db.enabled():
        return {"available": False}
    totals = await db.fetch_all(
        """
        SELECT provider, model, operation,
               count(*) AS calls,
               coalesce(sum(total_tokens), 0) AS tokens,
               coalesce(sum(cached_tokens), 0) AS cached_tokens,
               coalesce(round(avg(latency_ms)), 0) AS avg_latency_ms
        FROM usage_events
        WHERE created_at > now() - interval '30 days'
        GROUP BY provider, model, operation
        ORDER BY calls DESC
        """
    )
    runs = await db.fetch_one(
        """
        SELECT count(*) AS analyses,
               coalesce(round(avg(duration_ms)), 0) AS avg_duration_ms,
               coalesce(percentile_disc(0.95) WITHIN GROUP (ORDER BY duration_ms), 0) AS p95_duration_ms,
               coalesce(round(avg(overall_score)::numeric, 1), 0) AS avg_overall_score
        FROM analyses
        WHERE created_at > now() - interval '30 days'
        """
    )
    return {
        "available": True,
        "window_days": 30,
        "runs": {k: (float(v) if v is not None else 0) for k, v in (runs or {}).items()},
        "providers": [
            {k: (float(v) if isinstance(v, int | float) else v) for k, v in row.items()}
            for row in totals
        ],
    }
