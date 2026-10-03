import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv is optional for tests
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"
LOG_DIR = BASE_DIR / "logs"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


LLAMA_API_KEY = os.getenv("LLAMA_API_KEY", "")
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "https://api.groq.com/openai/v1")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "openai/gpt-oss-20b")
LLAMA_FALLBACK_MODEL = os.getenv("LLAMA_FALLBACK_MODEL", "")  # optional, tried once on 404/413/429
def _origins(raw: str) -> list[str]:
    """Accept sloppy input: spaces, quotes, newlines, trailing slashes."""
    out = []
    for o in raw.replace("\n", ",").replace(";", ",").split(","):
        o = o.strip().strip("\"'").strip().rstrip("/")
        if o:
            out.append(o)
    return out


ALLOWED_ORIGINS = _origins(os.getenv("ALLOWED_ORIGINS", "http://localhost:5173"))
RATE_LIMIT_PER_MINUTE = _int("RATE_LIMIT_PER_MINUTE", 30)
MAX_MESSAGE_CHARS = _int("MAX_MESSAGE_CHARS", 500)
HISTORY_MESSAGES = _int("HISTORY_MESSAGES", 4)
MAX_OUTPUT_TOKENS = _int("MAX_OUTPUT_TOKENS", 1200)
SESSION_TTL_MINUTES = _int("SESSION_TTL_MINUTES", 60)
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"
TEMPERATURE = 0.2