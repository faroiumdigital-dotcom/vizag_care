"""Server-side chat history. The browser only sends a session_id, never history."""
import re
import threading
import time
import uuid
from collections import deque

from .config import HISTORY_MESSAGES, SESSION_TTL_MINUTES

_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_lock = threading.Lock()
_sessions: dict[str, dict] = {}


def normalize_session_id(session_id: str | None) -> str:
    """Return a safe id; make a new one if missing or malformed."""
    if session_id and _SESSION_RE.match(session_id):
        return session_id
    return uuid.uuid4().hex


def _purge(now: float) -> None:
    ttl = SESSION_TTL_MINUTES * 60
    for sid in [s for s, v in _sessions.items() if now - v["last"] > ttl]:
        del _sessions[sid]


def get_history(session_id: str) -> list[dict]:
    with _lock:
        s = _sessions.get(session_id)
        return list(s["messages"]) if s else []


def add_exchange(session_id: str, user_text: str, assistant_text: str) -> None:
    now = time.time()
    with _lock:
        _purge(now)
        s = _sessions.setdefault(session_id, {"messages": deque(maxlen=HISTORY_MESSAGES), "last": now})
        s["messages"].append({"role": "user", "content": user_text})
        s["messages"].append({"role": "assistant", "content": assistant_text})
        s["last"] = now
