"""Follow-up suggestion chips. The model proposes them; this gives a safe fallback if it does not."""
import re

_TOPICS = [  # (trigger words in the question + answer, chips) - first match wins
    (["appointment", "book", "booking"], ["Doctor timings", "Do you accept insurance?", "How do I reach the hospital?"]),
    (["department", "specialt"], ["I want to consult a doctor", "Which doctor should I see?", "Doctor timings"]),
    (["doctor", "dr.", "timing", "opd"], ["How do I book an appointment?", "Consultation fees", "Where is the hospital?"]),
    (["package", "checkup", "check-up"], ["What tests are included?", "How do I book a checkup?", "Do you accept insurance?"]),
    (["insurance", "bill", "cashless", "payment", "fee"], ["How do I book an appointment?", "Health packages", "Doctor timings"]),
    (["parking", "reach", "located", "address", "bus", "station"], ["OPD timings", "Which doctors are available?", "Is there a cafeteria?"]),
    (["room", "ward", "visitor", "visiting"], ["Visiting hours", "Insurance for admission", "Parking details"]),
]
_DEFAULT = ["Doctors & timings", "Departments", "Health packages"]
_NON_LATIN = re.compile(r"[\u0900-\u097F\u0C00-\u0C7F]")


def clean(items: list[str]) -> list[str]:
    out = []
    for x in items:
        x = x.strip(" -*\"'\u2022")
        if 2 < len(x) <= 40 and x.lower() != "none" and x not in out:
            out.append(x)
    return out[:3]


def fallback(question: str, answer: str) -> list[str]:
    if _NON_LATIN.search(question) or _NON_LATIN.search(answer):
        return []
    text = f"{question} {answer}".lower()
    for words, chips in _TOPICS:
        if any(w in text for w in words):
            return chips
    return _DEFAULT
