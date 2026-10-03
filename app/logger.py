import json
from datetime import datetime, timezone

from .config import LOG_DIR

LOG_DIR.mkdir(exist_ok=True)


def _write(name: str, record: dict) -> None:
    record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with open(LOG_DIR / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_chat(session_id: str, question: str, answer: str, answered: bool, emergency: bool = False) -> None:
    """Every question goes to chat.jsonl; unanswered ones are also copied to unanswered.log."""
    _write("chat.jsonl", {"session": session_id, "q": question, "a": answer, "answered": answered, "emergency": emergency})
    if not answered and not emergency:
        _write("unanswered.log", {"session": session_id, "q": question})


def log_error(session_id: str, error: str) -> None:
    _write("errors.log", {"session": session_id, "error": error})
