import re
import time
from dataclasses import dataclass

MAX_INPUT_CHARS = 4000
MIN_SECONDS_BETWEEN_CALLS = 1.0

BLOCKED_TOPICS = [
    "make a bomb",
    "explosive device",
    "child sexual",
    "credit card dump",
    "how to hack into",
    "malware source code",
    "kill someone",
]

INJECTION_PATTERNS = [
    r"ignore (all|any|previous|above) instructions",
    r"disregard (all|any|previous) (rules|instructions)",
    r"you are now (in )?developer mode",
    r"reveal (your|the) system prompt",
    r"act as (an|a) unrestricted",
    r"jailbreak",
    r"\bDAN\b",
    r"pretend (you have|to have) no (rules|restrictions|guidelines)",
]

PII_PATTERNS = {
    "email": r"[\w.\-]+@[\w.\-]+\.\w+",
    "phone_in": r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",
    "card": r"\b(?:\d[ -]*?){13,16}\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
}

LEAK_MARKERS = [
    "system prompt:",
    "you are a helpful, accurate and professional ai assistant",
]

_last_call: dict[str, float] = {}


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    sanitized_text: str = ""


def _redact_pii(text: str) -> str:
    redacted = text
    for label, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f"[REDACTED_{label.upper()}]", redacted)
    return redacted


def check_input(thread_id: str, text: str) -> GuardrailResult:
    if not text or not text.strip():
        return GuardrailResult(False, "Empty message.")
    if len(text) > MAX_INPUT_CHARS:
        return GuardrailResult(False, f"Message too long (> {MAX_INPUT_CHARS} characters).")

    now = time.time()
    last = _last_call.get(thread_id, 0.0)
    if now - last < MIN_SECONDS_BETWEEN_CALLS:
        return GuardrailResult(False, "You're sending messages too fast — please slow down a moment.")
    _last_call[thread_id] = now

    lowered = text.lower()
    if any(phrase in lowered for phrase in BLOCKED_TOPICS):
        return GuardrailResult(False, "This request touches on content I can't help with.")
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardrailResult(False, "That looks like an attempt to override my instructions, so I can't proceed with it.")

    return GuardrailResult(True, sanitized_text=text)


def check_output(text: str) -> GuardrailResult:
    if not text:
        return GuardrailResult(True, sanitized_text=text)
    lowered = text.lower()
    if any(marker in lowered for marker in LEAK_MARKERS):
        return GuardrailResult(False, "Response withheld: it looked like it was leaking internal instructions. Please rephrase your question.")
    return GuardrailResult(True, sanitized_text=_redact_pii(text))
