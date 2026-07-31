"""Rewrite suggestions: LLM-authored, grounded in the evidence table."""

from __future__ import annotations

import logging

from ..schemas import BulletRewrite, Evidence, JobSpec, ParsedResume, Suggestions
from . import llm
from .ats import weakest_bullets
from .textkit import WEAK_VERBS

log = logging.getLogger("fitscope.suggest")

SYSTEM = (
    "You are a senior resume editor for technical roles. You rewrite bullets to be specific, "
    "outcome-first and ATS-friendly. Absolute rule: never invent employers, tools, metrics or "
    "results that are not present in the original bullet. When a number is missing, insert a "
    "clearly marked placeholder like [X%] or [N users] for the candidate to fill in."
)

USER_TEMPLATE = """Target role: {role}
Company: {company}

Requirements the resume does NOT yet evidence:
{gaps}

Requirements it already evidences well:
{strengths}

Candidate bullets that need work:
{bullets}

Return JSON with exactly this shape:
{{
  "tailored_summary": "2-3 sentence professional summary aimed at this role, first person implied, no pronouns, only using facts visible in the bullets",
  "rewrites": [
    {{
      "bullet_id": "id of the original bullet",
      "original": "the original text",
      "rewritten": "improved version, 12-28 words, starts with a strong past-tense verb",
      "reason": "what changed and why it helps, max 15 words",
      "targets": ["requirement ids this now speaks to"]
    }}
  ],
  "add_these": ["up to 5 concrete additions: a missing skills line, a project, a certification - each tied to a real gap"],
  "quick_wins": ["up to 5 formatting or wording fixes that take under a minute each"]
}}

Rewrite every bullet you are given. Keep the candidate's real scope and seniority."""


def _heuristic(resume: ParsedResume, evidence: list[Evidence], job: JobSpec) -> Suggestions:
    """Deterministic fallback so the product never returns an empty panel."""
    rewrites: list[BulletRewrite] = []
    for bullet in weakest_bullets(resume, limit=5):
        reasons = []
        if not bullet.has_metric:
            reasons.append("add a number")
        if (bullet.action_verb or "") in WEAK_VERBS:
            reasons.append("lead with a stronger verb")
        if bullet.word_count > 34:
            reasons.append("split into two bullets")
        rewrites.append(
            BulletRewrite(
                bullet_id=bullet.id,
                original=bullet.text,
                rewritten=bullet.text,
                reason=", ".join(reasons) or "tighten wording",
            )
        )

    gaps = [e for e in evidence if e.coverage != "covered"]
    add_these = [
        f"Evidence for: {e.requirement.text}"
        for e in sorted(gaps, key=lambda e: e.score)[:5]
    ]
    missing_terms = sorted({k for e in gaps for k in e.keyword_misses})[:8]
    quick_wins = []
    if missing_terms:
        quick_wins.append("Add a Skills line covering: " + ", ".join(missing_terms))
    if not resume.links:
        quick_wins.append("Add your GitHub and LinkedIn URLs to the header.")
    if "summary" not in resume.sections:
        quick_wins.append("Add a 3-line Summary tuned to this role at the top.")
    return Suggestions(
        tailored_summary=None,
        rewrites=rewrites,
        add_these=add_these,
        quick_wins=quick_wins,
        mode="heuristic",
    )


async def build_suggestions(
    resume: ParsedResume, evidence: list[Evidence], job: JobSpec
) -> Suggestions:
    fallback = _heuristic(resume, evidence, job)
    if not llm.configured():
        return fallback

    gaps = [e for e in evidence if e.coverage != "covered"]
    gaps.sort(key=lambda e: (e.coverage != "missing", e.score))
    strengths = [e for e in evidence if e.coverage == "covered"][:5]
    targets = weakest_bullets(resume, limit=6)
    if not targets:
        targets = resume.bullets[:5]

    gap_lines = "\n".join(
        f"- [{e.requirement.id}] ({e.requirement.category}) {e.requirement.text}"
        + (f" | missing terms: {', '.join(e.keyword_misses[:5])}" if e.keyword_misses else "")
        for e in gaps[:10]
    ) or "- none"
    strength_lines = "\n".join(
        f"- [{e.requirement.id}] {e.requirement.text}" for e in strengths
    ) or "- none"
    bullet_lines = "\n".join(f'- [{b.id}] "{b.text}"' for b in targets) or "- none"

    try:
        data = await llm.chat_json(
            SYSTEM,
            USER_TEMPLATE.format(
                role=job.role_title or "unspecified",
                company=job.company or "unspecified",
                gaps=gap_lines,
                strengths=strength_lines,
                bullets=bullet_lines,
            ),
            operation="suggestions",
            temperature=0.35,
        )
    except Exception as exc:
        log.warning("suggestion generation failed: %s", exc)
        return fallback

    by_id = {b.id: b.text for b in resume.bullets}
    rewrites: list[BulletRewrite] = []
    for item in data.get("rewrites") or []:
        rewritten = (item.get("rewritten") or "").strip()
        if not rewritten:
            continue
        bullet_id = item.get("bullet_id")
        original = (item.get("original") or by_id.get(bullet_id, "")).strip()
        if not original or rewritten.lower() == original.lower():
            continue
        rewrites.append(
            BulletRewrite(
                bullet_id=bullet_id if bullet_id in by_id else None,
                original=original,
                rewritten=rewritten,
                reason=(item.get("reason") or "sharpened for this role").strip()[:160],
                targets=[t for t in (item.get("targets") or []) if isinstance(t, str)][:4],
            )
        )

    summary = (data.get("tailored_summary") or "").strip() or None
    add_these = [s.strip() for s in (data.get("add_these") or []) if isinstance(s, str) and s.strip()]
    quick_wins = [s.strip() for s in (data.get("quick_wins") or []) if isinstance(s, str) and s.strip()]

    if not rewrites and not add_these:
        return fallback

    return Suggestions(
        tailored_summary=summary,
        rewrites=rewrites[:8],
        add_these=(add_these or fallback.add_these)[:6],
        quick_wins=(quick_wins or fallback.quick_wins)[:6],
        mode="llm",
    )
