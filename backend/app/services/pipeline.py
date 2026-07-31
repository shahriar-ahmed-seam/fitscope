"""Analysis orchestration: parsed resume + raw JD -> AnalysisReport."""

from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import datetime, timezone

from .. import db
from ..config import settings
from ..schemas import AnalysisReport, ParsedResume
from . import ats as ats_service
from . import jd as jd_service
from . import matching, retrieval, suggest

log = logging.getLogger("fitscope.pipeline")


def _public_id() -> str:
    return secrets.token_urlsafe(9).replace("-", "a").replace("_", "b")


async def analyze(
    resume: ParsedResume,
    jd_text: str,
    role_title: str | None = None,
    company: str | None = None,
    fast_mode: bool = False,
    save: bool = True,
    client_hash: str | None = None,
) -> AnalysisReport:
    started = time.perf_counter()

    job = await jd_service.build_job_spec(jd_text, role_title, company)
    evidence, pipeline_stats = await matching.match_requirements(resume, job)
    ats_result = ats_service.evaluate(resume, job)
    scores = matching.score_fit(evidence, ats_result.score)

    suggestions = (
        suggest._heuristic(resume, evidence, job)
        if fast_mode
        else await suggest.build_suggestions(resume, evidence, job)
    )

    duration_ms = int((time.perf_counter() - started) * 1000)
    report = AnalysisReport(
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        duration_ms=duration_ms,
        job=job,
        scores=scores,
        evidence=evidence,
        ats=ats_result,
        suggestions=suggestions,
        resume_stats={
            "word_count": resume.word_count,
            "char_count": resume.char_count,
            "bullet_count": len(resume.bullets),
            "bullets_with_metrics": sum(1 for b in resume.bullets if b.has_metric),
            "sections": sorted(resume.sections),
            "skills_detected": resume.skills,
            "years_experience": resume.years_experience,
            "source_kind": resume.source_kind,
            "pages": resume.pages,
            "parse_warnings": resume.parse_warnings,
            "emails": len(resume.emails),
            "links": len(resume.links),
        },
        pipeline={
            **pipeline_stats,
            "jd_extraction": job.extraction_mode,
            "suggestions": suggestions.mode,
            "weights": {
                "semantic": settings.semantic_weight,
                "ats": settings.ats_weight,
                "must_have": settings.weight_must_have,
                "responsibility": settings.weight_responsibility,
                "nice_to_have": settings.weight_nice_to_have,
            },
            "thresholds": {
                "covered": settings.covered_threshold,
                "partial": settings.partial_threshold,
            },
        },
    )

    if save and db.enabled():
        try:
            await _persist(report, resume, jd_text, client_hash)
        except Exception as exc:
            log.error("failed to persist report: %s", exc)

    return report


async def _persist(
    report: AnalysisReport, resume: ParsedResume, jd_text: str, client_hash: str | None
) -> None:
    public_id = _public_id()
    report.public_id = public_id
    report.share_url = f"{settings.public_base_url.rstrip('/')}/r/{public_id}"

    row = await db.fetch_one(
        """
        INSERT INTO analyses (public_id, role_title, company, overall_score, semantic_score,
            ats_score, verdict, report, resume_chars, jd_chars, duration_ms, client_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            public_id,
            report.job.role_title,
            report.job.company,
            report.scores.overall,
            report.scores.semantic_fit,
            report.scores.ats_readiness,
            report.scores.verdict,
            report.model_dump_json(),
            resume.char_count,
            len(jd_text),
            report.duration_ms,
            client_hash,
        ),
    )
    if not row:
        return

    # Index the JD so the archive can surface similar roles.
    summary_parts = [report.job.role_title or "", *[r.text for r in report.job.requirements[:8]]]
    summary = " | ".join(p for p in summary_parts if p)[:1200]
    # Only index when embeddings come free from cache or spare quota; a throttled
    # call here would slow the user's response for no user-visible benefit.
    vectors = await retrieval.embed([summary], "document") if summary else None
    if vectors:
        await db.execute(
            """
            INSERT INTO jd_index (analysis_id, role_title, summary, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (row["id"], report.job.role_title, summary, json.dumps(vectors[0])),
        )


async def load_report(public_id: str) -> AnalysisReport | None:
    row = await db.fetch_one(
        "SELECT public_id, report, created_at FROM analyses WHERE public_id = %s", (public_id,)
    )
    if not row:
        return None
    payload = row["report"]
    data = json.loads(payload) if isinstance(payload, str) else payload
    report = AnalysisReport.model_validate(data)
    report.public_id = row["public_id"]
    report.share_url = f"{settings.public_base_url.rstrip('/')}/r/{row['public_id']}"
    if row.get("created_at") and not report.created_at:
        report.created_at = row["created_at"].isoformat()
    return report


async def similar_roles(public_id: str, limit: int = 5) -> list[dict]:
    """Nearest JDs by embedding, excluding the report itself."""
    rows = await db.fetch_all(
        """
        WITH target AS (
            SELECT j.embedding
            FROM jd_index j
            JOIN analyses a ON a.id = j.analysis_id
            WHERE a.public_id = %s
            LIMIT 1
        )
        SELECT a.public_id, j.role_title, a.overall_score,
               1 - (j.embedding <=> (SELECT embedding FROM target)) AS similarity
        FROM jd_index j
        JOIN analyses a ON a.id = j.analysis_id
        WHERE a.public_id <> %s AND (SELECT embedding FROM target) IS NOT NULL
        ORDER BY j.embedding <=> (SELECT embedding FROM target)
        LIMIT %s
        """,
        (public_id, public_id, limit),
    )
    return [
        {
            "public_id": r["public_id"],
            "role_title": r["role_title"],
            "similarity": round(float(r["similarity"] or 0), 4),
            "overall_score": r["overall_score"],
        }
        for r in rows
    ]
