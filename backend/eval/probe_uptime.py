"""Hit every read endpoint repeatedly and report edge-level failures.

    python -m eval.probe_uptime [base_url] [rounds]

Useful after a deploy: Render's router briefly answers with
`x-render-routing: no-server` while the previous instance drains, and this
distinguishes that from application errors.
"""

from __future__ import annotations

import sys
import time
from collections import Counter

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 5

PATHS = [
    "/",
    "/health",
    "/readyz",
    "/openapi.json",
    "/api/v1/quota",
    "/api/v1/scoring",
    "/api/v1/reports?limit=1",
]


def main() -> None:
    failures: Counter[str] = Counter()
    total = 0
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for round_index in range(ROUNDS):
            for path in PATHS:
                total += 1
                try:
                    response = client.get(BASE + path)
                except Exception as exc:  # noqa: BLE001
                    failures[f"{path} {type(exc).__name__}"] += 1
                    continue
                if response.status_code != 200:
                    routing = response.headers.get("x-render-routing", "-")
                    failures[f"{path} {response.status_code} routing={routing}"] += 1
            if round_index < ROUNDS - 1:
                time.sleep(3)

    ok = total - sum(failures.values())
    print(f"{ok}/{total} requests OK")
    for key, count in failures.most_common():
        print(f"  {count}x {key}")


if __name__ == "__main__":
    main()
