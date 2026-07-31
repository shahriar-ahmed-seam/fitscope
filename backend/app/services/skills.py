"""Skill ontology lookup used for the deterministic keyword layer."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "skills.json"

STOPWORDS = {
    "and", "or", "the", "with", "for", "a", "an", "of", "to", "in", "on", "at", "by", "as",
    "is", "are", "be", "will", "you", "your", "our", "we", "they", "this", "that", "have",
    "has", "using", "use", "used", "such", "including", "etc", "able", "must", "should",
    "experience", "years", "year", "strong", "good", "excellent", "knowledge", "skills",
    "ability", "work", "working", "team", "teams", "role", "job", "candidate", "plus",
    "preferred", "required", "requirements", "responsibilities", "familiarity", "understanding",
    "hands", "proven", "track", "record", "well", "very", "highly", "least", "more", "other",
}


@lru_cache
def ontology() -> dict[str, list[str]]:
    with DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def _compiled() -> list[tuple[str, re.Pattern[str]]]:
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for canonical, aliases in ontology().items():
        parts = []
        for alias in aliases:
            alias = alias.strip()
            if not alias:
                continue
            escaped = re.escape(alias).replace(r"\ ", r"[\s\-_/]+")
            # \b fails next to symbols such as c++ or c#, so guard with lookarounds.
            left = r"(?<![A-Za-z0-9+#.])"
            right = r"(?![A-Za-z0-9+#])"
            parts.append(f"{left}{escaped}{right}")
        if parts:
            compiled.append((canonical, re.compile("|".join(parts), re.I)))
    return compiled


def extract_skills(text: str) -> list[str]:
    """Canonical skills present in a blob of text, ordered by first appearance."""
    found: list[tuple[int, str]] = []
    for canonical, pattern in _compiled():
        match = pattern.search(text)
        if match:
            found.append((match.start(), canonical))
    found.sort()
    return [name for _, name in found]


def canonicalise(term: str) -> str | None:
    """Map a free-text term onto the ontology when possible."""
    hits = extract_skills(term)
    return hits[0] if hits else None


def keyword_terms(text: str, limit: int = 40) -> list[str]:
    """Ontology skills plus notable capitalised/technical tokens from a JD."""
    terms = list(extract_skills(text))
    seen = set(terms)
    for token in re.findall(r"[A-Za-z][A-Za-z0-9+#./\-]{2,}", text):
        low = token.lower().strip(".-/")
        if low in seen or low in STOPWORDS or len(low) < 3:
            continue
        is_acronym = token.isupper() and 2 <= len(token) <= 6
        is_versioned = bool(re.search(r"[0-9]", token)) and not token.isdigit()
        if is_acronym or is_versioned:
            seen.add(low)
            terms.append(low)
        if len(terms) >= limit:
            break
    return terms[:limit]


def match_keywords(terms: list[str], haystack: str) -> tuple[list[str], list[str]]:
    """Split terms into those present in haystack and those absent."""
    hits: list[str] = []
    misses: list[str] = []
    onto = ontology()
    lowered = haystack.lower()
    for term in terms:
        aliases = onto.get(term, [term])
        present = False
        for alias in aliases:
            alias = alias.strip().lower()
            if not alias:
                continue
            if re.search(
                r"(?<![A-Za-z0-9+#.])" + re.escape(alias).replace(r"\ ", r"[\s\-_/]+")
                + r"(?![A-Za-z0-9+#])",
                lowered,
            ):
                present = True
                break
        (hits if present else misses).append(term)
    return hits, misses
