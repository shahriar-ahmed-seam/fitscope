"""Deterministic ATS-mechanics scoring.

This score is intentionally independent of the semantic fit score: it answers
"will a parser and a 20-second human skim survive this document?", not "is this
person qualified?". Every check is rule-based and reproducible.
"""

from __future__ import annotations

import re

from ..schemas import AtsCheck, AtsResult, JobSpec, ParsedResume
from .skills import match_keywords
from .textkit import METRIC_RE, WEAK_VERBS

FIRST_PERSON = re.compile(r"\b(i|me|my|mine)\b", re.I)
DATE_HINT = re.compile(r"(19|20)\d{2}|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.I)
PHOTO_HINT = re.compile(r"\b(photo|photograph|passport size)\b", re.I)
PRONOUN_HEAVY_RATIO = 0.15


def _check(
    id_: str, label: str, points: float, max_points: float, detail: str, fix: str | None = None
) -> AtsCheck:
    if points >= max_points - 1e-9:
        status = "pass"
    elif points <= max_points * 0.34:
        status = "fail"
    else:
        status = "warn"
    return AtsCheck(
        id=id_,
        label=label,
        status=status,  # type: ignore[arg-type]
        points=round(points, 1),
        max_points=max_points,
        detail=detail,
        fix=fix,
    )


def evaluate(resume: ParsedResume, job: JobSpec) -> AtsResult:
    checks: list[AtsCheck] = []
    text = resume.raw_text
    bullets = resume.bullets

    # 1. Machine readability (12)
    if resume.source_kind == "pdf" and resume.char_count < 900:
        checks.append(_check("parseable", "Machine-readable text", 2, 12,
            f"Only {resume.char_count} characters extracted from the PDF.",
            "Re-export as a text-based PDF (Save as PDF, not a scan or image)."))
    elif resume.char_count < 1200:
        checks.append(_check("parseable", "Machine-readable text", 7, 12,
            f"{resume.word_count} words is thin for a full resume.",
            "Expand experience bullets; most screened resumes run 350-800 words."))
    else:
        checks.append(_check("parseable", "Machine-readable text", 12, 12,
            f"{resume.word_count} words extracted cleanly."))

    # 2. Contact block (10)
    contact_points = 0.0
    missing_contact: list[str] = []
    contact_points += 4 if resume.emails else 0
    if not resume.emails:
        missing_contact.append("email")
    contact_points += 3 if resume.phones else 0
    if not resume.phones:
        missing_contact.append("phone")
    contact_points += 3 if resume.links else 0
    if not resume.links:
        missing_contact.append("LinkedIn/GitHub link")
    checks.append(_check("contact", "Contact details", contact_points, 10,
        "All key contact fields found." if not missing_contact
        else "Missing: " + ", ".join(missing_contact),
        None if not missing_contact
        else "Put email, phone and one profile URL as plain text in the top block."))

    # 3. Standard section headings (12)
    expected = {"experience", "education", "skills"}
    found = expected & set(resume.sections)
    bonus = 2 if ("summary" in resume.sections or "projects" in resume.sections) else 0
    section_points = len(found) / len(expected) * 10 + bonus
    checks.append(_check("sections", "Standard section headings", section_points, 12,
        f"Detected: {', '.join(sorted(resume.sections)) or 'none'}.",
        None if len(found) == len(expected)
        else "Use literal headings: Summary, Experience, Projects, Skills, Education."))

    # 4. Dated history (8)
    experience_text = " ".join(resume.sections.get("experience", []))
    date_hits = len(DATE_HINT.findall(experience_text))
    if date_hits >= 4:
        checks.append(_check("dates", "Dated work history", 8, 8, f"{date_hits} date markers in Experience."))
    elif date_hits >= 2:
        checks.append(_check("dates", "Dated work history", 5, 8, "Some roles look undated.",
            "Give every role a MM/YYYY - MM/YYYY range."))
    else:
        checks.append(_check("dates", "Dated work history", 1, 8,
            "No reliable date ranges found in Experience.",
            "Add MM/YYYY - MM/YYYY to each role; parsers use these to compute tenure."))

    # 5. Quantified achievements (16)
    with_metric = sum(1 for b in bullets if b.has_metric)
    ratio = with_metric / len(bullets) if bullets else 0.0
    metric_points = min(16.0, ratio / 0.45 * 16)
    checks.append(_check("metrics", "Quantified achievements", metric_points, 16,
        f"{with_metric} of {len(bullets)} bullets contain a number "
        f"({ratio * 100:.0f}%; aim for 45%+).",
        None if ratio >= 0.45
        else "Add scale or outcome numbers: latency, %, users, revenue, dataset size."))

    # 6. Strong action verbs (10)
    weak = [b for b in bullets if (b.action_verb or "") in WEAK_VERBS]
    if bullets:
        weak_ratio = len(weak) / len(bullets)
        verb_points = max(0.0, 10 - weak_ratio * 30)
    else:
        weak_ratio, verb_points = 1.0, 0.0
    checks.append(_check("verbs", "Action-verb openings", verb_points, 10,
        f"{len(weak)} bullets open with a passive verb ('worked on', 'responsible for')."
        if weak else "Bullets lead with strong verbs.",
        None if not weak else "Open with the outcome verb: Built, Cut, Scaled, Shipped, Led."))

    # 7. Bullet length discipline (8)
    if bullets:
        long_bullets = [b for b in bullets if b.word_count > 34]
        short_bullets = [b for b in bullets if b.word_count < 8]
        penalty = (len(long_bullets) * 1.5 + len(short_bullets) * 0.8)
        length_points = max(0.0, 8 - penalty)
        detail = (f"{len(long_bullets)} bullets over 34 words, {len(short_bullets)} under 8 words.")
    else:
        length_points, detail = 0.0, "No bullets detected."
    checks.append(_check("length", "Bullet length", length_points, 8, detail,
        None if length_points >= 8 else "Keep bullets between 12 and 30 words, one idea each."))

    # 8. Keyword coverage against this JD (18)
    jd_terms = list(dict.fromkeys(job.hard_skills or []))[:30]
    hits, misses = match_keywords(jd_terms, text)
    coverage = (len(hits) / len(jd_terms)) if jd_terms else 1.0
    keyword_points = min(18.0, coverage / 0.7 * 18)
    checks.append(_check("keywords", "Role keyword coverage", keyword_points, 18,
        f"{len(hits)} of {len(jd_terms)} JD keywords appear in the resume "
        f"({coverage * 100:.0f}%).",
        None if coverage >= 0.7
        else "Mirror the employer's exact terms for tools you have genuinely used."))

    # 9. Tone and formatting hygiene (6)
    hygiene = 6.0
    notes: list[str] = []
    words = max(resume.word_count, 1)
    if len(FIRST_PERSON.findall(text)) / words > PRONOUN_HEAVY_RATIO / 10:
        hygiene -= 2
        notes.append("first-person pronouns")
    if PHOTO_HINT.search(text):
        hygiene -= 1
        notes.append("photo reference")
    if resume.pages and resume.pages > 2:
        hygiene -= 2
        notes.append(f"{resume.pages} pages")
    if any("|" in line and len(line) > 120 for line in text.split("\n")):
        hygiene -= 1
        notes.append("table-like rows")
    checks.append(_check("hygiene", "Formatting hygiene", max(hygiene, 0.0), 6,
        "Clean." if not notes else "Issues: " + ", ".join(notes),
        None if not notes else "Drop pronouns and photos, keep to 1-2 pages, avoid tables."))

    total = sum(c.points for c in checks)
    total_max = sum(c.max_points for c in checks)
    score = round(total / total_max * 100, 1) if total_max else 0.0

    return AtsResult(
        score=score,
        checks=checks,
        keyword_coverage=round(coverage * 100, 1),
        matched_keywords=hits,
        missing_keywords=misses,
    )


def weakest_bullets(resume: ParsedResume, limit: int = 6) -> list:
    """Bullets most in need of a rewrite: no metric, weak verb, or bad length."""
    scored = []
    for b in resume.bullets:
        if b.section not in ("experience", "projects", "summary", "header"):
            continue
        penalty = 0.0
        penalty += 0 if b.has_metric else 2.0
        penalty += 1.5 if (b.action_verb or "") in WEAK_VERBS else 0.0
        penalty += 1.0 if b.word_count > 34 or b.word_count < 10 else 0.0
        penalty += 0.5 if not METRIC_RE.search(b.text) else 0.0
        if penalty > 0:
            scored.append((penalty, b))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    return [b for _, b in scored[:limit]]
