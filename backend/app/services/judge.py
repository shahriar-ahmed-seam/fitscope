"""Grounded coverage judging.

Retrieval narrows each requirement down to a handful of candidate resume lines.
This module decides, for each requirement, whether those candidates actually
satisfy it. The judge may only cite line ids it was given, so evidence in the UI
is always traceable to real resume text — the model cannot invent a bullet.

One request covers every requirement, which keeps latency and cost flat with
respect to the number of requirements.
"""

from __future__ import annotations

import logging

from ..config import settings
from ..schemas import Requirement
from . import llm

log = logging.getLogger("fitscope.judge")

SYSTEM = (
    "You are a strict technical screener. For each job requirement you are given the resume lines "
    "most likely to satisfy it. Decide how well the resume evidences the requirement. "
    "Judge only what the lines actually say: transferable and clearly adjacent experience counts as "
    "partial, wishful interpretation does not count at all. You may only cite line ids from the "
    "candidates provided."
)

USER_TEMPLATE = """Assess each requirement against the candidate resume lines.

Labels:
- "covered": a line demonstrates this requirement directly, at a comparable depth.
- "partial": related or adjacent evidence, or the right skill without the stated depth,
  scale or seniority.
- "missing": no real evidence among the candidate lines.

Return JSON: {{"assessments": [
  {{
    "requirement_id": "r1",
    "coverage": "covered" | "partial" | "missing",
    "evidence_id": "id of the single best line, or null when missing",
    "confidence": 0.0-1.0,
    "note": "max 14 words explaining the decision, quoting the deciding detail"
  }}
]}}

Return exactly one assessment per requirement id, no extras.

REQUIREMENTS AND CANDIDATE LINES:
{blocks}"""


def _format_blocks(
    requirements: list[Requirement], shortlists: dict[str, list[tuple[str, str]]]
) -> str:
    chunks: list[str] = []
    for req in requirements:
        candidates = shortlists.get(req.id, [])
        lines = "\n".join(f'    {cid}: "{text[:320]}"' for cid, text in candidates) or "    (none)"
        chunks.append(
            f"[{req.id}] ({req.category.replace('_', ' ')}) {req.text}\n"
            f"  candidate lines:\n{lines}"
        )
    return "\n\n".join(chunks)


async def assess(
    requirements: list[Requirement], shortlists: dict[str, list[tuple[str, str]]]
) -> dict[str, dict] | None:
    """Return {requirement_id: {coverage, evidence_id, confidence, note}} or None."""
    if not settings.judge_enabled or not llm.configured() or not requirements:
        return None

    try:
        data = await llm.chat_json(
            SYSTEM,
            USER_TEMPLATE.format(blocks=_format_blocks(requirements, shortlists)),
            operation="coverage_judge",
            temperature=0.0,
        )
    except Exception as exc:
        log.warning("coverage judging failed, falling back to similarity scores: %s", exc)
        return None

    valid_ids = {req.id for req in requirements}
    out: dict[str, dict] = {}
    for item in data.get("assessments") or []:
        rid = item.get("requirement_id")
        if rid not in valid_ids:
            continue
        coverage = item.get("coverage")
        if coverage not in ("covered", "partial", "missing"):
            continue
        allowed = {cid for cid, _ in shortlists.get(rid, [])}
        evidence_id = item.get("evidence_id")
        if evidence_id not in allowed:
            evidence_id = None
        if coverage != "missing" and evidence_id is None:
            # A positive label with no citable line is not usable evidence.
            coverage = "partial" if allowed else "missing"
        confidence = item.get("confidence")
        out[rid] = {
            "coverage": coverage,
            "evidence_id": evidence_id,
            "confidence": float(confidence) if isinstance(confidence, int | float) else None,
            "note": (item.get("note") or "").strip()[:160] or None,
        }

    if len(out) < max(1, len(requirements) // 2):
        log.warning("judge returned %s of %s assessments; discarding", len(out), len(requirements))
        return None
    return out
