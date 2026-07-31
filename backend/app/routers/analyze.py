"""Analysis endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ..config import settings
from ..ratelimit import enforce
from ..schemas import AnalysisReport, AnalyzeTextRequest, ParsedResume
from ..services import pipeline
from ..services.parsing import parse_resume_bytes, parse_resume_text

log = logging.getLogger("fitscope.api")

router = APIRouter(prefix="/api/v1", tags=["analysis"])

ALLOWED_SUFFIXES = (".pdf", ".docx", ".doc", ".txt", ".md")


def _validate_jd(jd: str) -> str:
    jd = (jd or "").strip()
    if len(jd) < 60:
        raise HTTPException(422, "Job description is too short to analyse (need 60+ characters).")
    return jd[: settings.max_jd_chars]


def _guard_resume(resume: ParsedResume) -> None:
    if resume.char_count < 200:
        raise HTTPException(
            422,
            "Could not read enough text from the resume. If it is a scanned PDF, "
            "export a text-based version — most ATS parsers fail on scans too.",
        )


@router.post("/analyze", response_model=AnalysisReport)
async def analyze_text(request: Request, payload: AnalyzeTextRequest) -> AnalysisReport:
    """Analyse a pasted resume against a pasted job description."""
    client = await enforce(request)
    resume = parse_resume_text(payload.resume_text)
    _guard_resume(resume)
    return await pipeline.analyze(
        resume,
        _validate_jd(payload.job_description),
        role_title=payload.role_title,
        company=payload.company,
        fast_mode=payload.fast_mode,
        save=payload.save,
        client_hash=client,
    )


@router.post("/analyze/upload", response_model=AnalysisReport)
async def analyze_upload(
    request: Request,
    resume: UploadFile = File(..., description="PDF, DOCX or TXT resume"),
    job_description: str = Form(...),
    role_title: str | None = Form(None),
    company: str | None = Form(None),
    fast_mode: bool = Form(False),
    save: bool = Form(True),
) -> AnalysisReport:
    """Analyse an uploaded resume file against a job description."""
    client = await enforce(request)

    filename = resume.filename or "resume"
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(415, f"Unsupported file type. Use one of: {', '.join(ALLOWED_SUFFIXES)}")

    data = await resume.read()
    if not data:
        raise HTTPException(422, "Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            413, f"File is larger than {settings.max_upload_bytes // 1_000_000} MB."
        )

    try:
        parsed = parse_resume_bytes(data, filename)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("resume parsing failed")
        raise HTTPException(422, f"Could not parse the resume file: {exc}") from exc

    _guard_resume(parsed)
    return await pipeline.analyze(
        parsed,
        _validate_jd(job_description),
        role_title=role_title,
        company=company,
        fast_mode=fast_mode,
        save=save,
        client_hash=client,
    )


@router.post("/parse", response_model=ParsedResume)
async def parse_only(
    resume: UploadFile = File(...),
) -> ParsedResume:
    """Structure a resume without scoring it. Useful for debugging extraction."""
    data = await resume.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "File too large.")
    try:
        return parse_resume_bytes(data, resume.filename or "resume")
    except Exception as exc:
        raise HTTPException(422, f"Could not parse the resume file: {exc}") from exc
