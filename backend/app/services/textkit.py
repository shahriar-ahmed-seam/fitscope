"""Deterministic text utilities: normalisation, sectioning, bullet extraction.

No LLM involved here on purpose. The structural understanding of a resume must
be reproducible so the ATS score is stable across runs.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

CURRENT_YEAR = date.today().year

BULLET_PREFIX = re.compile(r"^\s*(?:[-–—•▪●◦*·o]|\d{1,2}[.)])\s+")
WHITESPACE = re.compile(r"[ \t\u00a0]+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4}")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s,;)\]]+", re.I)
YEAR_RANGE_RE = re.compile(
    r"(19|20)\d{2}\s*(?:-|–|—|to|until|through)\s*((19|20)\d{2}|present|current|now|ongoing)",
    re.I,
)
YEARS_CLAIM_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.I)
METRIC_RE = re.compile(
    r"(\d[\d,.]*\s*%|\$\s?\d[\d,.]*\s*[kmb]?\b|\b\d[\d,.]*\s*(?:x|×)\b"
    r"|\b\d[\d,.]*\s*(?:ms|s|sec|seconds|minutes|hours|days|weeks|months)\b"
    r"|\b\d[\d,.]*\s*(?:k|m|b|bn)?\+?\s*(?:users?|customers?|requests?|rps|qps|records?|rows?|"
    r"documents?|images?|models?|students?|teams?|projects?|downloads?|stars?|clients?|tickets?|"
    r"transactions?|events?|queries?|tokens?|hours?)\b"
    r"|\bp9[59]\b|\bfrom\s+\d+[\d,.%]*\s+to\s+\d+)",
    re.I,
)

WEAK_VERBS = {
    "worked",
    "helped",
    "assisted",
    "participated",
    "responsible",
    "involved",
    "handled",
    "did",
    "used",
    "supported",
    "learned",
    "attended",
    "tried",
}

STRONG_VERBS = {
    "architected", "built", "shipped", "designed", "led", "launched", "reduced", "increased",
    "improved", "optimized", "optimised", "automated", "scaled", "migrated", "implemented",
    "delivered", "cut", "accelerated", "deployed", "engineered", "developed", "created",
    "established", "drove", "grew", "eliminated", "resolved", "mentored", "owned", "rewrote",
    "refactored", "integrated", "benchmarked", "instrumented", "productionized", "trained",
    "fine-tuned", "evaluated", "published", "streamlined", "hardened", "modernized",
}

SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("summary", re.compile(r"^(professional\s+)?(summary|profile|objective|about( me)?|overview)\b", re.I)),
    ("experience", re.compile(
        r"^(work\s+|professional\s+|relevant\s+|industry\s+)?"
        r"(experience|employment|history|career)\b", re.I)),
    ("projects", re.compile(
        r"^(selected\s+|key\s+|personal\s+|academic\s+)?(projects?|portfolio|open source)\b", re.I)),
    ("education", re.compile(r"^(education|academic|qualifications?|degrees?)\b", re.I)),
    ("skills", re.compile(
        r"^(technical\s+|core\s+|key\s+)?"
        r"(skills?|competencies|technolog(y|ies)|tech stack|toolkit|expertise)\b", re.I)),
    ("certifications", re.compile(r"^(certifications?|licen[cs]es?|courses?|training)\b", re.I)),
    ("awards", re.compile(r"^(awards?|honors?|honours?|achievements?|recognition)\b", re.I)),
    ("publications", re.compile(r"^(publications?|papers?|research|talks?|patents?)\b", re.I)),
    ("volunteering", re.compile(
        r"^(volunteer(ing)?|community|extracurricular|leadership)\b", re.I)),
    ("languages", re.compile(r"^(languages?|language proficiency)\b", re.I)),
    ("interests", re.compile(r"^(interests?|hobbies)\b", re.I)),
    ("references", re.compile(r"^(references?)\b", re.I)),
    ("contact", re.compile(r"^(contact|personal (details|information))\b", re.I)),
]


def sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", "ignore"))
        h.update(b"\x1f")
    return h.hexdigest()


def clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = WHITESPACE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def looks_like_heading(line: str) -> str | None:
    """Return the canonical section name when a line reads like a heading."""
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped) > 42 or BULLET_PREFIX.match(line):
        return None
    if len(stripped.split()) > 5:
        return None
    for name, pattern in SECTION_PATTERNS:
        if pattern.match(stripped):
            return name
    return None


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "header"
    for line in text.split("\n"):
        if not line.strip():
            continue
        heading = looks_like_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line.strip())
    return sections


def _split_run_on(line: str) -> list[str]:
    """Split lines that pack several bullets onto one row."""
    parts = re.split(r"\s{2,}(?=[-•●▪])|(?<=[.;])\s+(?=[-•●▪])", line)
    return [p for p in (x.strip() for x in parts) if p]


def first_verb(text: str) -> str | None:
    for token in re.findall(r"[A-Za-z][A-Za-z\-']+", text)[:4]:
        low = token.lower()
        if low in STRONG_VERBS or low in WEAK_VERBS or low.endswith("ed") or low.endswith("ing"):
            return low
    tokens = re.findall(r"[A-Za-z][A-Za-z\-']+", text)
    return tokens[0].lower() if tokens else None


def extract_bullets(sections: dict[str, list[str]]) -> list[dict]:
    """Pull achievement-like lines out of the resume, tagged with their section."""
    bullets: list[dict] = []
    seen: set[str] = set()
    priority = ("experience", "projects", "summary", "header", "awards", "publications",
                "volunteering", "certifications", "education", "skills")
    ordered = [s for s in priority if s in sections] + [s for s in sections if s not in priority]

    for section in ordered:
        for line in sections[section]:
            for chunk in _split_run_on(line):
                bare = BULLET_PREFIX.sub("", chunk).strip(" .;")
                if len(bare) < 25:
                    continue
                words = bare.split()
                if len(words) < 4 or len(words) > 90:
                    continue
                # Skip lines that are mostly a date range or a contact row.
                if EMAIL_RE.search(bare) and len(words) < 12:
                    continue
                key = re.sub(r"[^a-z0-9]", "", bare.lower())[:120]
                if key in seen:
                    continue
                seen.add(key)
                bullets.append(
                    {
                        "id": f"b{len(bullets) + 1}",
                        "text": bare,
                        "section": section,
                        "has_metric": bool(METRIC_RE.search(bare)),
                        "word_count": len(words),
                        "action_verb": first_verb(bare),
                    }
                )
    return bullets


def extract_contacts(text: str) -> tuple[list[str], list[str], list[str]]:
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))
    links = list(dict.fromkeys(m.rstrip(".") for m in URL_RE.findall(text)))
    phones: list[str] = []
    head = "\n".join(text.split("\n")[:14])
    for candidate in PHONE_RE.findall(head):
        digits = re.sub(r"\D", "", candidate)
        if 9 <= len(digits) <= 15:
            phones.append(candidate.strip())
    return emails[:4], list(dict.fromkeys(phones))[:3], links[:8]


def estimate_years(text: str) -> float | None:
    """Prefer an explicit claim, else infer from date ranges in the text."""
    claims = [float(m) for m in YEARS_CLAIM_RE.findall(text)]
    claims = [c for c in claims if 0 < c <= 45]
    if claims:
        return max(claims)

    spans: list[tuple[int, int]] = []
    for match in YEAR_RANGE_RE.finditer(text):
        nums = [int(n) for n in re.findall(r"(?:19|20)\d{2}", match.group(0))]
        if not nums:
            continue
        start = nums[0]
        end = nums[1] if len(nums) > 1 else CURRENT_YEAR
        if 1970 <= start <= end <= 2035:
            spans.append((start, end))
    if not spans:
        return None
    spans.sort()
    merged: list[list[int]] = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    total = sum(e - s for s, e in merged)
    return float(total) if total else None


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
