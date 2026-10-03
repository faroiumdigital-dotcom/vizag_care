"""Loads the knowledge base once at startup and builds a SMALL, per-question system prompt.

Why: sending the whole KB on every request (~8,000 tokens) exceeds the provider's
tokens-per-minute limit (HTTP 413 on Groq's free tier). Instead we send the fixed rules
plus only the KB sections that look relevant to the question (and, for Telugu/Hindi
questions, the multilingual FAQ block).
"""
import json
import re
from functools import lru_cache

from .config import KB_DIR

TAG_INSTRUCTION = (
    "FORMAT RULE (machine-read, never mention it): after your reply, add two final lines.\n"
    "Line 1: SUGGESTIONS: s1 | s2 | s3  -> three short things the PERSON might want to tap next "
    "(max 5 words each, written from the person's side such as 'Doctor timings', 'How do I book?', "
    "'Show me Cardiology'), in the person's language, related to this conversation, each answerable from the knowledge base.\n"
    "Line 2: [ANSWERED] if you answered from the knowledge base, or [UNANSWERED] if the answer is not in it "
    "(including when you use the fallback phrase). For emergencies or [UNANSWERED], write SUGGESTIONS: none."
)

# Max characters of KB text sent per request (~3 chars/token -> roughly 2,500 tokens).
KB_CHAR_BUDGET = 7500

# Sections that are always included (short and always useful).
CORE_SECTIONS = ("ABOUT", "EMERGENCY")
# Sections that are large; included whole only when clearly asked for, otherwise line by line.
BIG_SECTIONS = ("DEPARTMENTS", "DOCTORS", "FAQS")

# Section -> trigger words (English + Telugu/Hindi, native script and common spellings).
SECTION_KEYWORDS: dict[str, list[str]] = {
    "TIMINGS": ["timing", "timings", "time", "open", "close", "hours", "opd", "sunday", "holiday", "సమయం", "టైమింగ్", "समय", "samayam", "kab"],
    "HOW TO REACH": ["reach", "location", "located", "address", "where", "route", "bus", "railway", "airport", "map", "direction", "చిరునామా", "ఎక్కడ", "पता", "कहाँ", "kaha", "ekkada"],
    "FACILITIES": ["parking", "cafeteria", "atm", "wifi", "wi-fi", "facility", "facilities", "canteen", "prayer", "ambulance", "పార్కింగ్"],
    "DEPARTMENTS": ["department", "departments", "specialty", "speciality", "specialities", "treat", "floor", "block", "విభాగం", "विभाग"],
    "DOCTORS": ["doctor", "doctors", "dr", "specialist", "which doctors", "డాక్టర్", "వైద్యుడు", "डॉक्टर", "dr."],
    "SYMPTOM TO DEPARTMENT": ["fever", "pain", "cough", "cold", "headache", "stomach", "rash", "vomit", "symptom", "symptoms", "sick", "unwell", "which doctor", "which department", "జ్వరం", "నొప్పి", "बुखार", "दर्द", "jwaram", "noppi", "bukhar"],
    "TESTS": ["test", "tests", "lab", "scan", "xray", "x-ray", "mri", "ct", "blood", "ultrasound", "ecg", "report", "reports", "పరీక్ష", "जांच", "टेस्ट"],
    "HEALTH PACKAGES": ["package", "packages", "checkup", "check-up", "health check", "master", "ప్యాకేజీ", "पैकेज"],
    "APPOINTMENT POLICY": ["appointment", "appointments", "book", "booking", "cancel", "reschedule", "token", "walk-in", "walkin", "అపాయింట్‌మెంట్", "అపాయింట్మెంట్", "अपॉइंटमेंट", "appointment"],
    "BILLING AND INSURANCE": ["bill", "billing", "payment", "pay", "insurance", "cashless", "tpa", "fee", "fees", "cost", "price", "charges", "consultation fee", "ఫీజు", "బిల్", "बिल", "फीस", "बीमा", "insurance"],
    "ROOMS": ["room", "rooms", "ward", "icu", "bed", "admission", "admit", "stay", "private", "semi", "గది", "कमरा"],
    "VISITOR POLICY": ["visitor", "visitors", "visiting", "visit", "attender", "attendant", "సందర్శ", "मिलने"],
    "PHARMACY AND LAB": ["pharmacy", "medicine", "medicines", "medical shop", "lab", "collection", "ఫార్మసీ", "మందులు", "फार्मेसी", "दवाई"],
}

_WORD_RE = re.compile(r"[a-z0-9\-\.]+", re.IGNORECASE)
_STOP = set(
    "a an the is are was were be do does did i you we me my your our to of in on at for and or but with from "
    "what which who when where how can could would should will please tell about any there this that it its "
    "have has had get give need want know hi hello hospital vizag care".split()
)
_NON_LATIN_RE = re.compile(r"[\u0900-\u097F\u0C00-\u0C7F]")  # Devanagari (Hindi) + Telugu


def _tokens(text: str) -> set[str]:
    return {w.strip(".-") for w in _WORD_RE.findall(text.lower()) if w not in _STOP and len(w) > 1}


def is_non_latin(text: str) -> bool:
    return bool(_NON_LATIN_RE.search(text))


@lru_cache(maxsize=1)
def get_rules() -> dict:
    return json.loads((KB_DIR / "assistant_rules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _kb_sections() -> list[dict]:
    """Parse the markdown KB into sections: [{name, header, lines:[...]}] in original order."""
    text = (KB_DIR / "vizag_care_kb.md").read_text(encoding="utf-8")
    sections = []
    for block in re.split(r"(?m)^(?=## )", text):
        block = block.strip("\n")
        if not block.startswith("## "):
            continue
        header, *body = block.split("\n")
        name = re.sub(r"\s*\(.*\)\s*$", "", header[3:]).strip().upper()
        # FAQ items are Q/A pairs; everything else is split per line.
        if name == "FAQS":
            lines, cur = [], []
            for ln in body:
                if ln.startswith("Q:") and cur:
                    lines.append("\n".join(cur))
                    cur = []
                if ln.strip():
                    cur.append(ln)
            if cur:
                lines.append("\n".join(cur))
        else:
            lines = [ln for ln in body if ln.strip()]
        sections.append({"name": name, "header": header, "lines": lines})
    return sections


@lru_cache(maxsize=1)
def _multilingual_text() -> str:
    path = KB_DIR / "faqs_multilingual.json"
    if not path.exists():
        return ""
    faqs = json.loads(path.read_text(encoding="utf-8")).get("faqs", [])
    out = ["## TELUGU AND HINDI ANSWERS (use when the user writes in that language)"]
    for f in faqs:
        out.append(f"Q: {f['question']}")
        if f.get("answer_te"):
            out.append(f"A (Telugu): {f['answer_te']}")
        if f.get("answer_hi"):
            out.append(f"A (Hindi): {f['answer_hi']}")
    return "\n".join(out)


def get_kb_text() -> str:
    """Full KB (used for warm-up and tests only; NOT sent to the model in full)."""
    return "\n\n".join([s["header"] + "\n" + "\n".join(s["lines"]) for s in _kb_sections()] + [_multilingual_text()])


def select_kb(query: str) -> str:
    """Pick the KB parts relevant to `query` (which may include recent user messages)."""
    q = query.lower()
    q_tokens = _tokens(query)
    chosen: dict[str, set[int] | None] = {}  # section -> None (whole) or set of line indexes
    used = 0
    sections = {s["name"]: s for s in _kb_sections()}

    def size(name: str, idx: set[int] | None) -> int:
        s = sections[name]
        lines = s["lines"] if idx is None else [s["lines"][i] for i in sorted(idx)]
        return len(s["header"]) + sum(len(x) + 1 for x in lines)

    def add(name: str, idx: set[int] | None) -> None:
        nonlocal used
        if name not in sections:
            return
        prev = chosen.get(name, set())
        merged = None if (idx is None or prev is None) else (prev | idx)
        new_total = used - (size(name, prev) if name in chosen else 0) + size(name, merged)
        if new_total > KB_CHAR_BUDGET and name in chosen:
            return
        if new_total > KB_CHAR_BUDGET and used > 0:
            return
        chosen[name] = merged
        used = new_total

    for name in CORE_SECTIONS:
        add(name, None)

    # 1) Sections whose trigger words appear in the question (whole section for small ones).
    hits = []
    for name, words in SECTION_KEYWORDS.items():
        score = sum(1 for w in words if w in q)
        if score:
            hits.append((score, name))
    for score, name in sorted(hits, reverse=True):
        if name in BIG_SECTIONS and name != "DOCTORS":
            continue  # departments handled line-by-line below
        add(name, None)

    # 2) Line-level matching inside the large sections (DEPARTMENTS, DOCTORS, FAQS).
    scored = []
    for name in BIG_SECTIONS:
        s = sections.get(name)
        if not s or chosen.get(name, set()) is None:
            continue
        for i, line in enumerate(s["lines"]):
            overlap = len(q_tokens & _tokens(line))
            if overlap:
                scored.append((overlap, name, i))
    for overlap, name, i in sorted(scored, reverse=True)[:12]:
        add(name, {i})

    # 3) Nothing matched (e.g. Telugu/Hindi text, greetings, vague questions): send the compact sections.
    if len(chosen) <= len(CORE_SECTIONS):
        for name, s in sections.items():
            if name not in BIG_SECTIONS:
                add(name, None)

    parts = []
    for name, s in sections.items():  # keep original order
        if name in chosen:
            idx = chosen[name]
            lines = s["lines"] if idx is None else [s["lines"][i] for i in sorted(idx)]
            parts.append(s["header"] + "\n" + "\n".join(lines))
    return "\n\n".join(parts)


@lru_cache(maxsize=1)
def _static_prompt_parts() -> str:
    r = get_rules()
    return "\n\n".join(
        [
            r["persona"],
            r["language"],
            "YOU MUST:\n" + "\n".join(f"- {x}" for x in r["must_do"]),
            "YOU MUST NOT:\n" + "\n".join(f"- {x}" for x in r["must_not"]),
            "HOW TO SOUND:\n" + "\n".join(f"- {x}" for x in r.get("style", [])),
            "EXAMPLES OF THE RIGHT TONE:\n"
            + "\n".join(f'User: {e["user"]}\nYou: {e["assistant"]}' for e in r.get("examples", [])),
            f'Fallback phrase when the answer is missing: "{r["fallback_phrase"]}"',
            TAG_INSTRUCTION,
        ]
    )


def get_system_prompt(query: str = "", history: list[dict] | None = None) -> str:
    """Build the system prompt for ONE question: fixed rules + only the relevant KB parts."""
    recent_user = " ".join(m["content"] for m in (history or [])[-2:] if m.get("role") == "user")
    context_query = f"{recent_user} {query}".strip()
    kb = select_kb(context_query)
    if is_non_latin(query) or is_non_latin(recent_user):
        kb += "\n\n" + _multilingual_text()
    return _static_prompt_parts() + "\n\n=== KNOWLEDGE BASE (your only source of facts) ===\n" + kb


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
