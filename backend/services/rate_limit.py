"""Public-play budget: global daily session count + per-IP hourly count.

In-memory, same scope as the session store. A valid access code bypasses
everything (judges / demo recording).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from backend import config

_day_key: str = ""
_day_count: int = 0
_ip_starts: dict[str, deque] = defaultdict(deque)


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def check_public_budget(ip: str) -> str | None:
    """Returns an error message if over budget, else None (and records the start)."""
    global _day_key, _day_count
    if _day_key != _today():
        _day_key, _day_count = _today(), 0
        _ip_starts.clear()

    if _day_count >= config.PUBLIC_DAILY_SESSIONS:
        return "HAL is over its public memory budget for today — come back tomorrow (or use an access code)."

    starts = _ip_starts[ip]
    cutoff = time.time() - 3600
    while starts and starts[0] < cutoff:
        starts.popleft()
    if len(starts) >= config.PUBLIC_SESSIONS_PER_IP_HOUR:
        return "Easy, detective — too many new investigations from your address. Try again in an hour."

    starts.append(time.time())
    _day_count += 1
    return None
