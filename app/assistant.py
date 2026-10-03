"""Builds the prompt, calls Llama through an OpenAI-compatible API, parses the answer tag."""
import re

from . import config
from .kb import get_rules, get_system_prompt

_client = None
_TAG_RE = re.compile(r"\s*\[(ANSWERED|UNANSWERED)\]\s*$", re.IGNORECASE)


def _get_client():
    global _client
    if _client is None:
        if not config.LLAMA_API_KEY:
            raise RuntimeError("LLAMA_API_KEY is not set. Copy .env.example to .env and add your key.")
        from openai import OpenAI

        _client = OpenAI(api_key=config.LLAMA_API_KEY, base_url=config.LLAMA_BASE_URL, timeout=30)
    return _client


def parse_reply(raw: str) -> tuple[str, bool]:
    """Return (clean_text, answered). Uses the tag; falls back to the fallback phrase."""
    raw = (raw or "").strip()
    m = _TAG_RE.search(raw)
    if m:
        return raw[: m.start()].strip(), m.group(1).upper() == "ANSWERED"
    clean = re.sub(r"\[(ANSWERED|UNANSWERED)\]", "", raw, flags=re.IGNORECASE).strip()
    phrase = get_rules()["fallback_phrase"].lower()[:30]
    return clean, phrase not in clean.lower()


def ask(message: str, history: list[dict]) -> tuple[str, bool]:
    messages = [{"role": "system", "content": get_system_prompt()}, *history, {"role": "user", "content": message}]
    resp = _get_client().chat.completions.create(
        model=config.LLAMA_MODEL, messages=messages, temperature=config.TEMPERATURE, max_tokens=500
    )
    return parse_reply(resp.choices[0].message.content)
