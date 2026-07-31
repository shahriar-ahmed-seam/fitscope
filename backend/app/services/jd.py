"""Turn a raw job description into a structured JobSpec."""

from __future__ import annotations

import logging
import re

from ..config import settings
from ..schemas import JobSpec, Requirement
from . import llm, textkit
from .skills import canonicalise, extract_skills

log = logging.getLogger("fitscope.jd")

SYSTEM = (
    "You are an expert technical recruiter. You read a job description and return a strict, "
    "de-duplicated breakdown of what the employer will actually screen for. "
    "Never invent requirements that are not implied by the text."
)

USER_TEMPLATE = """Analyse the job description below.

Return JSON with exactly this shape:
{{
  "role_title": string | null,
  "company": string | null,
  "seniority": "intern" | "junior" | "mid" | "senior" | "lead" | "principal" | null,
  "years_required": number | null,
  "location": string | null,
  "requirements": [
    {{
      "text": "one atomic, screenable requirement in <= 18 words",
      "category": "must_have" | "nice_to_have" | "responsibility",
      "keywords": ["concrete tool/skill terms from the JD"]
    }}
  ],
  "hard_skills": ["technologies and tools named in the JD"],
  "soft_skills": ["non-technical expectations"]
}}

Rules:
- Produce between 8 and 18 requirements. Split compound sentences into atomic items.
- "must_have" = stated as required/essential. "nice_to_have" = preferred/bonus/plus.
  "responsibility" = day-to-day work the person will own.
- Keep the employer's own vocabulary in "keywords" (e.g. "Kubernetes", "pgvector").
- No duplicates, no boilerplate about benefits, equal opportunity, or application steps.

JOB DESCRIPTION:
---
{jd}
---"""

BULLET_LINE = re.compile(r"^\s*(?:[-–—•▪●◦*·]|\d{1,2}[.)])\s+")
NICE_HINT = re.compile(r"\b(nice to have|preferred|bonus|plus|desirable|advantage|ideally)\b", re.I)
MUST_HINT = re.compile(r"\b(required|must|essential|minimum|proven|strong|solid|at least)\b", re.I)
RESP_HINT = re.compile(
    r"\b(you will|responsib|own the|day.to.day|collaborate|build|design|maintain|deliver|drive)\b",
    re.I,
)
SECTION_NICE = re.compile(r"\b(nice[- ]to[- ]have|preferred|bonus|desirable)\b", re.I)
SECTION_RESP = re.compile(r"\b(responsibilit|what you.?ll do|the role|your mission|duties)\b", re.I)
SECTION_MUST = re.compile(r"\b(requirement|qualification|what we.?re looking for|must have|skills)\b", re.I)
NOISE = re.compile(
    r"\b(equal opportunity|salary|benefits?|apply now|about us|our mission is|perks|"
    r"health insurance|paid leave|visa|how to apply|we offer)\b",
    re.I,
)
TITLE_RE = re.compile(
    r"^(?:job\s*title|position|role|title)\s*[:\-]\s*(.+)$|^(?:hiring|we(?:'| a)re hiring)[:\-]?\s*(.+)$",
    re.I,
)
COMPANY_RE = re.compile(r"^(?:company|organi[sz]ation|employer)\s*[:\-]\s*(.+)$", re.I)


def _heuristic_spec(jd_text: str) -> JobSpec:
    """Regex-only extraction. Used when the LLM is unavailable."""
    lines = [ln.strip() for ln in jd_text.split("\n") if ln.strip()]
    role_title = None
    company = None
    current_bucket = "must_have"
    requirements: list[Requirement] = []

    for line in lines:
        if role_title is None:
            m = TITLE_RE.match(line)
            if m:
                role_title = (m.group(1) or m.group(2) or "").strip(" .:-") or None
        if company is None:
            m = COMPANY_RE.match(line)
            if m:
                company = m.group(1).strip(" .:-") or None

        if len(line.split()) <= 8 and not BULLET_LINE.match(line):
            if SECTION_NICE.search(line):
                current_bucket = "nice_to_have"
                continue
            if SECTION_RESP.search(line):
                current_bucket = "responsibility"
                continue
            if SECTION_MUST.search(line):
                current_bucket = "must_have"
                continue

        candidate = BULLET_LINE.sub("", line).strip(" .;")
        if len(candidate.split()) < 4 or len(candidate) < 20 or NOISE.search(candidate):
            continue
        if not (BULLET_LINE.match(line) or MUST_HINT.search(candidate) or RESP_HINT.search(candidate)):
            continue

        category = current_bucket
        if NICE_HINT.search(candidate):
            category = "nice_to_have"
        elif MUST_HINT.search(candidate) and current_bucket != "responsibility":
            category = "must_have"

        requirements.append(
            Requirement(
                id=f"r{len(requirements) + 1}",
                text=candidate[:260],
                category=category,  # type: ignore[arg-type]
                keywords=extract_skills(candidate)[:6],
            )
        )
        if len(requirements) >= 20:
            break

    if not role_title:
        for line in lines[:5]:
            words = line.split()
            if 2 <= len(words) <= 9 and not NOISE.search(line):
                role_title = line.strip(" .:-")
                break

    skills = extract_skills(jd_text)
    years = None
    claims = [float(x) for x in textkit.YEARS_CLAIM_RE.findall(jd_text)]
    if claims:
        years = min(c for c in claims if 0 < c <= 30) if any(0 < c <= 30 for c in claims) else None

    return JobSpec(
        role_title=role_title,
        company=company,
        years_required=years,
        requirements=requirements,
        hard_skills=skills[:25],
        extraction_mode="heuristic",
    )


def _dedupe(requirements: list[Requirement]) -> list[Requirement]:
    seen: set[str] = set()
    out: list[Requirement] = []
    for req in requirements:
        key = re.sub(r"[^a-z0-9]", "", req.text.lower())[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        req.id = f"r{len(out) + 1}"
        out.append(req)
    return out


async def build_job_spec(
    jd_text: str, role_title: str | None = None, company: str | None = None
) -> JobSpec:
    jd_text = textkit.clean_text(jd_text)[: settings.max_jd_chars]
    spec: JobSpec | None = None

    if llm.configured():
        try:
            data = await llm.chat_json(
                SYSTEM, USER_TEMPLATE.format(jd=jd_text), operation="jd_extract", temperature=0.1
            )
            raw_reqs = data.get("requirements") or []
            requirements: list[Requirement] = []
            for item in raw_reqs:
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                category = item.get("category")
                if category not in ("must_have", "nice_to_have", "responsibility"):
                    category = "must_have"
                keywords = [
                    canonicalise(k) or k.strip().lower()
                    for k in (item.get("keywords") or [])
                    if isinstance(k, str) and k.strip()
                ]
                requirements.append(
                    Requirement(
                        id=f"r{len(requirements) + 1}",
                        text=text[:260],
                        category=category,
                        keywords=list(dict.fromkeys(keywords))[:8],
                    )
                )
            if requirements:
                years = data.get("years_required")
                spec = JobSpec(
                    role_title=(data.get("role_title") or None),
                    company=(data.get("company") or None),
                    seniority=(data.get("seniority") or None),
                    years_required=float(years) if isinstance(years, int | float) else None,
                    location=(data.get("location") or None),
                    requirements=requirements,
                    hard_skills=[s for s in (data.get("hard_skills") or []) if isinstance(s, str)][:25],
                    soft_skills=[s for s in (data.get("soft_skills") or []) if isinstance(s, str)][:15],
                    extraction_mode="llm",
                )
        except Exception as exc:
            log.warning("LLM JD extraction failed, using heuristics: %s", exc)

    if spec is None:
        spec = _heuristic_spec(jd_text)

    spec.requirements = _dedupe(spec.requirements)
    if not spec.hard_skills:
        spec.hard_skills = extract_skills(jd_text)[:25]
    if role_title:
        spec.role_title = role_title
    if company:
        spec.company = company
    return spec
