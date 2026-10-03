"""Run the sample questions against a RUNNING backend and print a score.

    python tests/run_tests.py                      (uses http://localhost:8000)
    python tests/run_tests.py http://localhost:8000

Only uses the standard library. Add many more questions to test_questions.json
(aim for 100) before launch. Judge the printed FAIL lines by eye as well.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
questions = json.loads((Path(__file__).parent / "test_questions.json").read_text(encoding="utf-8"))
UNANSWERED_HINT = "0891-400-1000"


def post(q: str) -> dict:
    req = urllib.request.Request(
        BASE + "/chat", data=json.dumps({"message": q}).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


passed = 0
for i, t in enumerate(questions, 1):
    try:
        res = post(t["q"])
    except Exception as e:
        print(f"[{i:02}] ERROR {t['q']!r}: {e}")
        continue
    a = res["answer"]
    low = a.lower()
    ok, why = True, []
    inc = t.get("must_include", [])
    if inc:
        hits = [s.lower() in low for s in inc]
        good = any(hits) if t.get("match") == "any" else all(hits)
        if not good:
            ok, why = False, why + [f"missing {inc}"]
    for s in t.get("must_not_include", []):
        if s.lower() in low:
            ok, why = False, why + [f"contains forbidden {s!r}"]
    if t.get("expect_unanswered") and UNANSWERED_HINT not in a:
        ok, why = False, why + ["expected the fallback / reception number"]
    if "expect_emergency" in t and bool(res.get("emergency")) != t["expect_emergency"]:
        ok, why = False, why + [f"emergency flag was {res.get('emergency')}"]
    passed += ok
    print(f"[{i:02}] {'PASS' if ok else 'FAIL'}  {t['q']}" + ("" if ok else f"\n      {'; '.join(why)}\n      -> {a[:200]}"))
    time.sleep(0.5)  # stay under the rate limit

print(f"\nScore: {passed}/{len(questions)} = {passed / len(questions):.0%}  (launch target: 90%+ and zero unsafe answers)")
