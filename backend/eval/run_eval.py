"""Evaluation harness for the FitScope scorer.

Runs every labelled resume x job pair through the real pipeline and reports:

  * Spearman rank correlation between FitScope's semantic fit and human labels
  * Pearson correlation on the raw scores
  * Pairwise ranking accuracy (of all label-distinct pairs, how many are ordered correctly)
  * Top-1 accuracy: for each resume, does the best-scoring job match the human's best
  * Latency percentiles per analysis

Usage (from backend/):
    python -m eval.run_eval               # full pipeline, LLM JD extraction
    python -m eval.run_eval --no-llm      # deterministic mode, no provider calls
    python -m eval.run_eval --out eval/results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import app.winloop  # noqa: F401  (Windows selector event loop, no-op elsewhere)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _rank(values: list[float]) -> list[float]:
    """Average ranks, ties shared."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(_rank(xs), _rank(ys))


def pairwise_accuracy(pairs: list[tuple[float, float]]) -> tuple[int, int]:
    """(correctly ordered, comparable) over all label-distinct combinations."""
    correct = comparable = 0
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            (h1, m1), (h2, m2) = pairs[i], pairs[j]
            if h1 == h2:
                continue
            comparable += 1
            if (h1 > h2 and m1 > m2) or (h1 < h2 and m1 < m2):
                correct += 1
    return correct, comparable


async def main() -> None:
    parser = argparse.ArgumentParser(description="FitScope evaluation harness")
    parser.add_argument("--no-llm", action="store_true", help="disable DeepSeek and Voyage calls")
    parser.add_argument("--out", default=str(Path(__file__).parent / "results.json"))
    parser.add_argument("--fast", action="store_true", help="skip rewrite generation (default on)")
    args = parser.parse_args()

    from app.config import settings  # imported after argparse so overrides apply

    if args.no_llm:
        settings.deepseek_api_key = ""
        settings.voyage_api_key = ""

    from app import db
    from app.services import parsing, pipeline

    await db.connect()

    spec = json.loads((FIXTURES / "pairs.json").read_text(encoding="utf-8"))
    resumes = {
        p.stem: p.read_text(encoding="utf-8") for p in (FIXTURES / "resumes").glob("*.txt")
    }
    jobs = {p.stem: p.read_text(encoding="utf-8") for p in (FIXTURES / "jobs").glob("*.txt")}

    rows: list[dict] = []
    latencies: list[int] = []

    for pair in spec["pairs"]:
        resume_text = resumes[pair["resume"]]
        jd_text = jobs[pair["job"]]
        parsed = parsing.parse_resume_text(resume_text)
        started = time.perf_counter()
        report = await pipeline.analyze(
            parsed, jd_text, fast_mode=True, save=False, client_hash="eval"
        )
        wall_ms = int((time.perf_counter() - started) * 1000)
        latencies.append(wall_ms)
        rows.append(
            {
                "id": pair["id"],
                "resume": pair["resume"],
                "job": pair["job"],
                "human_fit": pair["human_fit"],
                "semantic_fit": report.scores.semantic_fit,
                "overall": report.scores.overall,
                "ats": report.scores.ats_readiness,
                "must_have_coverage": report.scores.must_have_coverage,
                "requirements": len(report.evidence),
                "covered": report.scores.covered,
                "partial": report.scores.partial,
                "missing": report.scores.missing,
                "latency_ms": wall_ms,
            }
        )
        print(
            f"{pair['id']}  {pair['resume'][:22]:<22} x {pair['job'][:26]:<26} "
            f"human={pair['human_fit']:>3}  semantic={report.scores.semantic_fit:>5.1f}  "
            f"overall={report.scores.overall:>5.1f}  ats={report.scores.ats_readiness:>5.1f}  "
            f"{wall_ms:>5}ms"
        )

    human = [r["human_fit"] for r in rows]
    semantic = [r["semantic_fit"] for r in rows]
    overall = [r["overall"] for r in rows]

    correct, comparable = pairwise_accuracy(list(zip(human, semantic, strict=False)))

    top1_hits = 0
    resume_names = sorted({r["resume"] for r in rows})
    for name in resume_names:
        subset = [r for r in rows if r["resume"] == name]
        best_human = max(subset, key=lambda r: r["human_fit"])["job"]
        best_model = max(subset, key=lambda r: r["semantic_fit"])["job"]
        top1_hits += int(best_human == best_model)

    summary = {
        "pairs": len(rows),
        "spearman_semantic_vs_human": round(spearman(human, semantic), 4),
        "pearson_semantic_vs_human": round(pearson(human, semantic), 4),
        "spearman_overall_vs_human": round(spearman(human, overall), 4),
        "pairwise_ranking_accuracy": round(correct / comparable, 4) if comparable else None,
        "pairwise_comparisons": comparable,
        "top1_job_match_accuracy": round(top1_hits / len(resume_names), 4),
        "latency_ms": {
            "median": int(statistics.median(latencies)),
            "p95": int(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]),
            "max": max(latencies),
        },
        "mode": "deterministic (no providers)" if args.no_llm else "full pipeline",
    }

    print("\n=== summary ===")
    for key, value in summary.items():
        print(f"{key:<32} {value}")

    Path(args.out).write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {args.out}")
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
