"""Loads the knowledge base once at startup and builds the system prompt."""
import json
from functools import lru_cache

from .config import KB_DIR

TAG_INSTRUCTION = (
    "FORMAT RULE: end every reply with exactly one tag on its own last line: "
    "[ANSWERED] if you answered from the knowledge base, or [UNANSWERED] if the answer "
    "is not in the knowledge base (including when you use the fallback phrase). "
    "Never mention or explain this tag."
)


@lru_cache(maxsize=1)
def get_rules() -> dict:
    return json.loads((KB_DIR / "assistant_rules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_kb_text() -> str:
    """Single place that returns the KB. Phase 2: swap this for a database query."""
    kb = (KB_DIR / "vizag_care_kb.md").read_text(encoding="utf-8")
    ml_path = KB_DIR / "faqs_multilingual.json"
    if ml_path.exists():
        faqs = json.loads(ml_path.read_text(encoding="utf-8")).get("faqs", [])
        lines = ["", "## TELUGU AND HINDI ANSWERS (use when the user writes in that language)"]
        for f in faqs:
            lines.append(f"Q: {f['question']}")
            if f.get("answer_te"):
                lines.append(f"A (Telugu): {f['answer_te']}")
            if f.get("answer_hi"):
                lines.append(f"A (Hindi): {f['answer_hi']}")
        kb += "\n".join(lines)
    return kb


@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    r = get_rules()
    parts = [
        r["persona"],
        r["language"],
        "YOU MUST:\n" + "\n".join(f"- {x}" for x in r["must_do"]),
        "YOU MUST NOT:\n" + "\n".join(f"- {x}" for x in r["must_not"]),
        f'Fallback phrase when the answer is missing: "{r["fallback_phrase"]}"',
        TAG_INSTRUCTION,
        "=== KNOWLEDGE BASE (your only source of facts) ===\n" + get_kb_text(),
    ]
    return "\n\n".join(parts)


def public_config() -> dict:
    r = get_rules()
    return {
        "greeting": r["greeting"],
        "greeting_te": r["greeting_te"],
        "quick_replies": r["quick_replies"],
        "disclaimer": r["disclaimer"],
        "emergency_number": "0891-400-1108",
        "reception_number": "0891-400-1000",
    }
