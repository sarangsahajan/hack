"""Optional cactus-needle layer: transcript -> tool call send_alert(level) -> level.

Used by main.py --needle. If needle or its weights can't load (first run needs internet to
fetch them from Hugging Face), main.py falls back to matcher.detect so the demo never dies.
"""
import os

os.environ.setdefault("NEEDLE_TELEMETRY", "0")  # opt out of anonymous usage pings

from typing import Literal

import needle

_sent = []


@needle.tool
def send_alert(level: Literal["N", "W", "R", "T"]):
    """Send a vibration alert to the wearable. N = the name Shibu was called, W = someone said watch out, R = someone said run, T = someone said tsunami."""
    _sent.append(level)
    return {"sent": level}


class NeedleDetector:
    def __init__(self):
        self.agent = needle.Needle(tools=[send_alert], stateless=True)

    def detect(self, text):
        """Same contract as matcher.detect: (level or None, token)."""
        if not text.strip():
            return None, None
        _sent.clear()
        self.agent.run(text, max_steps=1)
        if _sent and _sent[0] in "NWRT":
            return _sent[0], "needle"
        return None, None

    def close(self):
        self.agent.close()
