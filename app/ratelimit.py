"""Small in-memory sliding-window limiter (per key, per minute)."""
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def allow(key: str, limit: int, window: float = 60.0) -> bool:
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        if len(_hits) > 5000:  # keep memory bounded
            for k in [k for k, v in _hits.items() if not v]:
                del _hits[k]
        return True
