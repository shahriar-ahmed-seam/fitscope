"""Public request/response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Coverage = Literal["covered", "partial", "missing"]
Category = Literal["must_have", "nice_to_have", "responsibility"]


class ResumeBullet(BaseModel):
    id: str
    text: str
    section: str
    has_metric: bool = False
    word_count: int = 0
    action_verb: str | None = None


class ParsedResume(BaseModel):
    raw_text: str
    char_count: int
    word_count: int
    bullets: list[ResumeBullet] = []
    sections: dict[str, list[str]] = {}
    emails: list[str] = []
    phones: list[str] = []
    links: list[str] = []
    skills: list[str] = []
    years_experience: float | None = None
    source_kind: Literal["pdf", "docx", "text"] = "text"
    pages: int | None = None
    parse_warnings: list[str] = []


class Requirement(BaseModel):
    id: str
    text: str
    category: Category = "must_have"
    keywords: list[str] = []


class JobSpec(BaseModel):
    role_title: str | None = None
    company: str | None = None
    seniority: str | None = None
    years_required: float | None = None
    location: str | None = None
    requirements: list[Requirement] = []
    hard_skills: list[str] = []
    soft_skills: list[str] = []
    extraction_mode: Literal["llm", "heuristic"] = "llm"


class Evidence(BaseModel):
    requirement: Requirement
    coverage: Coverage
    score: float = Field(description="Retrieval relevance of the best line, 0-1")
    decided_by: Literal["judge", "reranker", "lexical"] = "judge"
    confidence: float | None = None
    justification: str | None = None
    best_bullet_id: str | None = None
    best_bullet_text: str | None = None
    best_bullet_section: str | None = None
    supporting_bullet_ids: list[str] = []
    keyword_hits: list[str] = []
    keyword_misses: list[str] = []


class AtsCheck(BaseModel):
    id: str
    label: str
    status: Literal["pass", "warn", "fail"]
    points: float
    max_points: float
    detail: str
    fix: str | None = None


class AtsResult(BaseModel):
    score: float
    checks: list[AtsCheck] = []
    keyword_coverage: float = 0.0
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []


class BulletRewrite(BaseModel):
    bullet_id: str | None = None
    original: str
    rewritten: str
    reason: str
    targets: list[str] = []


class Suggestions(BaseModel):
    tailored_summary: str | None = None
    rewrites: list[BulletRewrite] = []
    add_these: list[str] = []
    quick_wins: list[str] = []
    mode: Literal["llm", "heuristic"] = "llm"


class ScoreBreakdown(BaseModel):
    overall: float
    semantic_fit: float
    ats_readiness: float
    must_have_coverage: float
    nice_to_have_coverage: float
    responsibility_coverage: float
    covered: int = 0
    partial: int = 0
    missing: int = 0
    verdict: str = ""
    verdict_detail: str = ""


class AnalysisReport(BaseModel):
    public_id: str | None = None
    share_url: str | None = None
    created_at: str | None = None
    duration_ms: int = 0
    job: JobSpec
    scores: ScoreBreakdown
    evidence: list[Evidence] = []
    ats: AtsResult
    suggestions: Suggestions
    resume_stats: dict[str, object] = {}
    pipeline: dict[str, object] = {}


class AnalyzeTextRequest(BaseModel):
    resume_text: str = Field(min_length=80)
    job_description: str = Field(min_length=60)
    role_title: str | None = None
    company: str | None = None
    fast_mode: bool = Field(
        default=False, description="Skip LLM rewrite suggestions for a faster response"
    )
    save: bool = True


class ReportSummary(BaseModel):
    public_id: str
    role_title: str | None
    company: str | None
    overall_score: float | None
    semantic_score: float | None
    ats_score: float | None
    verdict: str | None
    created_at: str


class SimilarRole(BaseModel):
    public_id: str
    role_title: str | None
    similarity: float
    overall_score: float | None
