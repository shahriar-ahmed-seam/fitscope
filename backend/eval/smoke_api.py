"""Manual API smoke check against a running server.

    python -m eval.smoke_api [base_url]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
FIX = Path(__file__).resolve().parent / "fixtures"


def main() -> None:
    resume = (FIX / "resumes" / "ml_platform_engineer.txt").read_text(encoding="utf-8")
    jd = (FIX / "jobs" / "llm_platform_engineer.txt").read_text(encoding="utf-8")

    with httpx.Client(base_url=BASE, timeout=180) as client:
        health = client.get("/health").json()
        print("health:", json.dumps(health["capabilities"]))

        resp = client.post(
            "/api/v1/analyze",
            json={"resume_text": resume, "job_description": jd, "fast_mode": False},
        )
        resp.raise_for_status()
        report = resp.json()
        scores = report["scores"]
        print(
            f"scores: overall={scores['overall']} semantic={scores['semantic_fit']} "
            f"ats={scores['ats_readiness']} verdict={scores['verdict']!r} "
            f"in {report['duration_ms']}ms"
        )
        print("pipeline:", json.dumps(report["pipeline"], default=str)[:220])
        print("share_url:", report.get("share_url"))
        print("requirements:", len(report["evidence"]),
              "| rewrites:", len(report["suggestions"]["rewrites"]),
              "| suggestion mode:", report["suggestions"]["mode"])
        first = report["evidence"][0]
        print(f"sample evidence: [{first['coverage']}] {first['requirement']['text'][:70]}")
        print(f"  cited: {str(first['best_bullet_text'])[:90]}")
        print(f"  note: {first['justification']} (by {first['decided_by']})")

        pid = report.get("public_id")
        if pid:
            fetched = client.get(f"/api/v1/reports/{pid}")
            print("report fetch:", fetched.status_code)
            md = client.get(f"/api/v1/reports/{pid}/markdown")
            print("markdown export:", md.status_code, len(md.text), "chars")
            print("similar:", client.get(f"/api/v1/reports/{pid}/similar").status_code)
        print("recent list:", client.get("/api/v1/reports?limit=5").status_code)
        print("quota:", client.get("/api/v1/quota").json())
        print("metrics available:", client.get("/api/v1/metrics").json().get("available"))
        print("openapi:", client.get("/openapi.json").status_code)


if __name__ == "__main__":
    main()
