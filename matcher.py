"""Keyword/fuzzy matcher for the prototype vocabulary. No LLM involved.

Levels, lowest -> highest importance (higher always wins):
    N  name "Shibu"        light pulse
    W  "WATCH OUT"
    R  "RUNNNN"
    T  "TSUNAMI"

detect(text) -> (level or None, matched_token)
"""
import re

from rapidfuzz import fuzz

NAME = "shibu"
ORDER = ["N", "W", "R", "T"]  # ascending importance

NAME_THRESHOLD = 80
TSUNAMI_THRESHOLD = 75
WATCHOUT_THRESHOLD = 85


def _words(text: str):
    return re.sub(r"[^a-z\s]", " ", text.lower()).split()


def _collapse(s: str) -> str:
    """runnnn -> run, shibuu -> shibu"""
    return re.sub(r"(.)\1+", r"\1", s)


def _skeleton(s: str) -> str:
    """Vowel runs -> 'a', so shibu/shiboo/sheebu/shivu all look alike."""
    return re.sub(r"[aeiouy]+", "a", _collapse(s))


def detect(text: str):
    words = _words(text)
    singles = [_collapse(w) for w in words]
    pairs = [a + b for a, b in zip(singles, singles[1:])]  # "tsu nami", "watch out"
    hits = {}

    name_sk = _skeleton(NAME)
    for w in words:
        if len(w) >= 3 and fuzz.ratio(_skeleton(w), name_sk) >= NAME_THRESHOLD:
            hits["N"] = w

    for c in singles + pairs:  # singles first, so "tsunami" beats the pair "runtsunami"
        if "W" not in hits and fuzz.ratio(c, "watchout") >= WATCHOUT_THRESHOLD:
            hits["W"] = c
        if "T" not in hits and fuzz.ratio(c, "tsunami") >= TSUNAMI_THRESHOLD:
            hits["T"] = c

    for c in singles:
        if c == "run":
            hits["R"] = c

    for level in reversed(ORDER):
        if level in hits:
            return level, hits[level]
    return None, None


if __name__ == "__main__":
    import sys

    print(detect(" ".join(sys.argv[1:])))
