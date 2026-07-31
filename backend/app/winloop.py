"""Windows event-loop compatibility shim.

psycopg's async mode cannot run on the ProactorEventLoop that Python selects by
default on Windows. Importing this module before the loop is created switches to
the selector policy. It is a no-op on Linux, so production images are unaffected.
"""

from __future__ import annotations

import asyncio
import sys


def apply() -> None:
    if sys.platform == "win32":
        policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        if policy is not None and not isinstance(asyncio.get_event_loop_policy(), policy):
            asyncio.set_event_loop_policy(policy())


apply()
