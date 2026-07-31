"""Requirement -> evidence matching and the semantic fit score.

Three stages:

1. **Retrieve.** Every requirement and every resume line is embedded in a single
   provider request; cosine similarity shortlists the most plausible lines per
   requirement. If embeddings are unavailable or throttled, an IDF-weighted
   lexical scorer takes over. The shortlist is a recall device only.
2. **Decide.** A grounded LLM judge labels each requirement covered / partial /
   missing and must cite one of the shortlisted line ids. Optionally a
   cross-encoder reranker does this instead, when the key has the throughput.
3. **Score.** Labels are weighted by requirement category. Coverage is never
   inferred from embedding cosine, which is not comparable across queries.
"""

from __future__ import annotations

import logging

from ..config import settings
from ..schemas import Evidence, JobSpec, ParsedResume, Requirement, ScoreBreakdown
from . import judge, retrieval
from .skills import match_keywords

log = logging.getLogger("fitscope.matching")

COVERAGE_VALUE = {"covered": 1.0, "partial": 0.5, "missing": 0.0}


def _candidate_texts(resume: ParsedResume) -> list[tuple[str, str, str]]:
    """(line_id, section, text) tuples that can serve as evidence."""
    items = [(b.id, b.section, b.text) for b in resume.bullets]
    if resume.skills:
        items.append(("skills", "skills", "Listed skills: " + ", ".join(resume.skills)))
    for name in ("education", "certifications", "languages"):
        lines = resume.sections.get(name) or []
        if lines:
            joined = " ".join(lines)[:600]
            if len(joined) > 30:
                items.append((f"sec_{name}", name, f"{name.title()}: {joined}"))
    return items


def _threshold_coverage(score: float) -> str:
    if score >= settings.covered_threshold:
        return "covered"
    if score >= settings.partial_threshold:
        return "partial"
    return "missing"


async def match_requirements(
    resume: ParsedResume, job: JobSpec
) -> tuple[list[Evidence], dict[str, object]]:
    candidates = _candidate_texts(resume)
    stats: dict[str, object] = {
        "candidate_lines": len(candidates),
        "requirement_count": len(job.requirements),
        "retrieval": "lexical-idf",
        "decider": "lexical-threshold",
    }
    if not candidates or not job.requirements:
        return [], stats

    doc_texts = [c[2] for c in candidates]
    query_texts = [r.text for r in job.requirements]

    doc_vectors, query_vectors = await retrieval.embed_pairs(doc_texts, query_texts)
    use_dense = bool(doc_vectors and query_vectors)
    if use_dense:
        stats["retrieval"] = settings.voyage_embed_model

    top_k = min(settings.judge_candidates_per_requirement, len(candidates))

    # --- stage 1: shortlist ------------------------------------------------- #
    shortlists: dict[str, list[tuple[str, str]]] = {}
    ranked_scores: dict[str, list[tuple[int, float]]] = {}
    for index, requirement in enumerate(job.requirements):
        if use_dense:
            scored = [
                (i, retrieval.cosine(query_vectors[index], doc_vectors[i]))
                for i in range(len(doc_texts))
            ]
        else:
            scored = list(enumerate(retrieval.lexical_relevance(requirement.text, doc_texts)))
        scored.sort(key=lambda x: x[1], reverse=True)
        ranked_scores[requirement.id] = scored[:top_k]
        shortlists[requirement.id] = [
            (candidates[i][0], candidates[i][2]) for i, _ in scored[:top_k]
        ]

    # --- stage 2: decide coverage ------------------------------------------- #
    assessments = await judge.assess(job.requirements, shortlists)
    if assessments:
        stats["decider"] = f"llm-judge:{settings.deepseek_model}"

    reranked: dict[str, list[tuple[int, float]]] = {}
    if assessments is None and retrieval.rerank_available():
        for requirement in job.requirements:
            shortlist_indices = [i for i, _ in ranked_scores[requirement.id]]
            ranked = await retrieval.rerank(
                requirement.text, [doc_texts[i] for i in shortlist_indices]
            )
            reranked[requirement.id] = [(shortlist_indices[i], s) for i, s in ranked]
        if reranked:
            stats["decider"] = f"reranker:{settings.voyage_rerank_model}"

    by_id = {cid: (cid, section, text) for cid, section, text in candidates}
    index_of = {candidates[i][0]: i for i in range(len(candidates))}

    evidence: list[Evidence] = []
    for requirement in job.requirements:
        ranked = reranked.get(requirement.id) or ranked_scores[requirement.id]
        best_index, best_score = (ranked[0] if ranked else (None, 0.0))
        decided_by = "reranker" if requirement.id in reranked else "lexical"
        confidence: float | None = None
        note: str | None = None

        assessment = (assessments or {}).get(requirement.id)
        if assessment:
            decided_by = "judge"
            coverage = assessment["coverage"]
            confidence = assessment["confidence"]
            note = assessment["note"]
            evidence_id = assessment["evidence_id"]
            if evidence_id and evidence_id in index_of:
                best_index = index_of[evidence_id]
                lookup = dict(ranked)
                best_score = lookup.get(best_index, best_score)
        else:
            coverage = _threshold_coverage(best_score)

        hits, misses = match_keywords(requirement.keywords, resume.raw_text)
        if coverage == "missing" and requirement.keywords and not misses and not assessment:
            # Every concrete term is present; phrasing differs. Do not overrule the judge.
            coverage = "partial"

        supporting = [
            candidates[i][0]
            for i, score in ranked[1:4]
            if score >= settings.partial_threshold and i != best_index
        ]

        best = candidates[best_index] if best_index is not None else None
        if coverage == "missing":
            best = None

        evidence.append(
            Evidence(
                requirement=requirement,
                coverage=coverage,  # type: ignore[arg-type]
                score=round(float(best_score), 4),
                decided_by=decided_by,  # type: ignore[arg-type]
                confidence=round(confidence, 3) if confidence is not None else None,
                justification=note,
                best_bullet_id=best[0] if best else None,
                best_bullet_text=best[2] if best else None,
                best_bullet_section=best[1] if best else None,
                supporting_bullet_ids=supporting if coverage != "missing" else [],
                keyword_hits=hits,
                keyword_misses=misses,
            )
        )

    _ = by_id
    return evidence, stats


def _category_coverage(evidence: list[Evidence], category: str) -> float:
    items = [e for e in evidence if e.requirement.category == category]
    if not items:
        return 100.0
    return round(sum(COVERAGE_VALUE[e.coverage] for e in items) / len(items) * 100, 1)


def score_fit(evidence: list[Evidence], ats_score: float) -> ScoreBreakdown:
    weights = settings.weights
    weighted = sum(
        weights[e.requirement.category] * COVERAGE_VALUE[e.coverage] for e in evidence
    )
    total_weight = sum(weights[e.requirement.category] for e in evidence)
    semantic = round(weighted / total_weight * 100, 1) if total_weight else 0.0
    overall = round(semantic * settings.semantic_weight + ats_score * settings.ats_weight, 1)

    must = _category_coverage(evidence, "must_have")
    nice = _category_coverage(evidence, "nice_to_have")
    resp = _category_coverage(evidence, "responsibility")

    if overall >= 80 and must >= 80:
        verdict = "Strong match"
        detail = "Apply as-is, then use the rewrites to sharpen the top third of the resume."
    elif overall >= 65:
        verdict = "Competitive with edits"
        detail = "Close the flagged must-have gaps before applying; the base is solid."
    elif overall >= 45:
        verdict = "Needs targeting"
        detail = "Real overlap exists but the resume does not surface it for this role."
    else:
        verdict = "Weak match"
        detail = "The core requirements are largely unevidenced. Consider a closer-fitting role."

    return ScoreBreakdown(
        overall=overall,
        semantic_fit=semantic,
        ats_readiness=round(ats_score, 1),
        must_have_coverage=must,
        nice_to_have_coverage=nice,
        responsibility_coverage=resp,
        covered=sum(1 for e in evidence if e.coverage == "covered"),
        partial=sum(1 for e in evidence if e.coverage == "partial"),
        missing=sum(1 for e in evidence if e.coverage == "missing"),
        verdict=verdict,
        verdict_detail=detail,
    )


_ = Requirement  # re-exported for type checkers
