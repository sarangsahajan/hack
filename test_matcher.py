"""No hardware needed:  python test_matcher.py"""
import sys

from main import looks_like_prompt
from matcher import detect

CASES = [
    ("Shibu", "N"),
    ("Hey, Shiboo!", "N"),
    ("Sheebu", "N"),
    ("Shiba", "N"),
    ("Watch out!", "W"),
    ("watchout", "W"),
    ("Watch out Shibu", "W"),
    ("Run!", "R"),
    ("Runnnn", "R"),
    ("run run run", "R"),
    ("Shibu, run", "R"),
    ("Tsunami!", "T"),
    ("tsunami warning", "T"),
    ("Sunami", "T"),
    ("tsu nami", "T"),
    ("Shibu, run, tsunami", "T"),
    ("the running water", None),
    ("watch the road out", None),
    ("watch it", None),
    ("Thank you.", None),
    ("", None),
]
ECHO = [
    ("Shibu, watch out, run, tsunami.", True),
    ("watch out, run, tsunami.", True),
    ("Shibu, run, tsunami", False),
    ("tsunami warning", False),
    ("Thank you.", False),
]

TOKENS = [
    ("Shibu, run, tsunami", "tsunami"),
    ("watch out", "watchout"),
]

bad = 0
for text, want in TOKENS:
    _, tok = detect(text)
    ok = tok == want
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  token {text!r:34} -> {tok}  want {want}")
for text, want in CASES:
    got, tok = detect(text)
    ok = got == want
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {text!r:34} -> {got} ({tok})  want {want}")
for text, want in ECHO:
    got = looks_like_prompt(text)
    ok = got == want
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  echo guard {text!r:34} -> {got}  want {want}")
total = len(TOKENS) + len(CASES) + len(ECHO)
print(f"\n{total - bad}/{total} passed")
sys.exit(1 if bad else 0)
