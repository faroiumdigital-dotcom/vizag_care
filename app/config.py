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
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama-3.3-70b-versatile")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
RATE_LIMIT_PER_MINUTE = _int("RATE_LIMIT_PER_MINUTE", 30)
MAX_MESSAGE_CHARS = _int("MAX_MESSAGE_CHARS", 500)
HISTORY_MESSAGES = _int("HISTORY_MESSAGES", 6)
SESSION_TTL_MINUTES = _int("SESSION_TTL_MINUTES", 60)
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"
TEMPERATURE = 0.2
