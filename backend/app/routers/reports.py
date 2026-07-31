"""Shareable report retrieval, export and archive listing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .. import db
from ..schemas import AnalysisReport, ReportSummary, SimilarRole
from ..services import pipeline
from ..services.report import to_markdown

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
async def list_reports(limit: int = Query(12, ge=1, le=50)) -> list[ReportSummary]:
    """Most recent public analyses. Powers the 'recent runs' strip."""
    rows = await db.fetch_all(
        """
        SELECT public_id, role_title, company, overall_score, semantic_score,
               ats_score, verdict, created_at
        FROM analyses
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [
        ReportSummary(
            public_id=r["public_id"],
            role_title=r["role_title"],
            company=r["company"],
            overall_score=r["overall_score"],
            semantic_score=r["semantic_score"],
            ats_score=r["ats_score"],
            verdict=r["verdict"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/{public_id}", response_model=AnalysisReport)
async def get_report(public_id: str) -> AnalysisReport:
    report = await pipeline.load_report(public_id)
    if report is None:
        raise HTTPException(404, "Report not found or no longer stored.")
    return report


@router.get("/{public_id}/markdown", response_class=PlainTextResponse)
async def get_report_markdown(public_id: str) -> PlainTextResponse:
    report = await pipeline.load_report(public_id)
    if report is None:
        raise HTTPException(404, "Report not found.")
    return PlainTextResponse(
        to_markdown(report),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fitscope-{public_id}.md"'},
    )


@router.get("/{public_id}/similar", response_model=list[SimilarRole])
async def get_similar(public_id: str, limit: int = Query(5, ge=1, le=20)) -> list[SimilarRole]:
    """Semantically closest job descriptions previously analysed (pgvector)."""
    rows = await pipeline.similar_roles(public_id, limit)
    return [SimilarRole(**row) for row in rows]
