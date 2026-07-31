"""Local development server.

Use this instead of bare `uvicorn app.main:app` on Windows: it installs the
selector event-loop policy that psycopg's async mode requires before the loop is
created.

    python run_dev.py            # http://127.0.0.1:8000
    set PORT=8099 && python run_dev.py
"""

from __future__ import annotations

import os

import uvicorn

import app.winloop  # noqa: F401  (applies the policy on import)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") == "1",
        loop="asyncio",
        log_level="info",
    )
