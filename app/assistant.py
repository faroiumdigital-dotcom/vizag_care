"""Builds the prompt, calls Llama through an OpenAI-compatible API, parses the answer tag."""
import re

from . import config
from .kb import get_rules, get_system_prompt
from .suggest import clean, fallback

_client = None
_TAG_RE = re.compile(r"\s*\[(ANSWERED|UNANSWERED)\]\s*$", re.IGNORECASE)
_SUGGEST_RE = re.compile(r"(?im)^\s*SUGGESTIONS?\s*:\s*(.*)$")


def _get_client():
    global _client
    if _client is None:
        if not config.LLAMA_API_KEY:
            raise RuntimeError("LLAMA_API_KEY is not set. Copy .env.example to .env and add your key.")
        from openai import OpenAI

        _client = OpenAI(api_key=config.LLAMA_API_KEY, base_url=config.LLAMA_BASE_URL, timeout=30)
    return _client


def parse_reply(raw: str) -> tuple[str, bool, list[str] | None]:
    """Return (clean_text, answered, suggestions). suggestions is None if the model gave no SUGGESTIONS line."""
    raw = (raw or "").strip()
    suggestions = None
    sm = _SUGGEST_RE.search(raw)
    if sm:
        suggestions = clean(re.split(r"\s*[|;]\s*", sm.group(1)))
        raw = (raw[: sm.start()] + raw[sm.end():]).strip()
    m = _TAG_RE.search(raw)
    if m:
        return raw[: m.start()].strip(), m.group(1).upper() == "ANSWERED", suggestions
    text = re.sub(r"\[(ANSWERED|UNANSWERED)\]", "", raw, flags=re.IGNORECASE).strip()
    phrase = get_rules()["fallback_phrase"].lower()[:30]
    return text, phrase not in text.lower(), suggestions


def _call(model: str, messages: list[dict]):
    kwargs = {}
    if "gpt-oss" in model:
        # Reasoning models spend output tokens on "thinking". Keep it short so the answer is not cut off.
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    return _get_client().chat.completions.create(
        model=model, messages=messages, temperature=config.TEMPERATURE, max_tokens=config.MAX_OUTPUT_TOKENS, **kwargs
    )


def _trim_incomplete(text: str) -> str:
    """If the model was cut off (finish_reason == 'length'), drop the unfinished last line."""
    lines = text.rstrip().split("\n")
    if len(lines) > 1:
        lines = lines[:-1]
    return "\n".join(lines).rstrip()


def ask(message: str, history: list[dict]) -> tuple[str, bool, list[str]]:
    # The system prompt is built per question: rules + only the relevant KB parts (keeps tokens low).
    system = get_system_prompt(message, history)
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]
    try:
        resp = _call(config.LLAMA_MODEL, messages)
    except Exception as e:
        # Model missing (404), too large (413) or rate-limited (429): try the optional fallback model once.
        status = getattr(e, "status_code", None)
        if config.LLAMA_FALLBACK_MODEL and status in (404, 413, 429):
            resp = _call(config.LLAMA_FALLBACK_MODEL, messages)
        else:
            raise
    choice = resp.choices[0]
    text, answered, suggestions = parse_reply(choice.message.content)
    if getattr(choice, "finish_reason", None) == "length":
        print("WARNING: reply was cut off by MAX_OUTPUT_TOKENS - raise it in .env")
        text = _trim_incomplete(text)
    if suggestions is None and answered:  # model forgot the line: use safe topic-based chips
        suggestions = fallback(message, text)
    return text, answered, (suggestions or []) if answered else []


def check_model() -> dict:
    """Tiny real call used by /health?deep=1 so a wrong model or key is visible immediately."""
    try:
        _call(config.LLAMA_MODEL, [{"role": "user", "content": "ping"}])
        return {"model_ok": True}
    except Exception as e:
        return {"model_ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}