"""
Constants for session and keyword behavior.
Two-step flow: (1) say a phrase -> spoken_verified; (2) type yes/ok -> COMPLIANT -> RELEASE.
"""

import re

# Step 2: typed keyword must be one of these (case-insensitive).
TYPED_KEYWORDS = frozenset({"yes", "ok", "okay"})

# Step 1: allowed spoken phrases (canonical forms after normalization).
# Phrases like "I'm awake", "I'm up" and variants (awake, up, wake, etc.) map here.
VALID_PHRASES = frozenset({
    "i'm awake",
    "i am awake",
    "awake",
    "im awake",
    "i'm up",
    "i am up",
    "up",
    "im up",
    "wake up",
    "get up",
    "a wake",
    "awaken",
    "wake",
})


def _normalize_phrase(spoken: str) -> str:
    """Lowercase, collapse spaces, strip punctuation, normalize apostrophes, im -> i'm."""
    if not spoken:
        return ""
    s = spoken.strip().lower()
    s = s.replace("\u2019", "'")
    s = re.sub(r"[.!?,;:]+$", "", s).strip()
    s = re.sub(r"^\s*[.!?,;:]+\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bim\b", "i'm", s)
    return s.strip()


def is_phrase_valid(spoken: str) -> bool:
    """True if the spoken phrase (STT output) matches an allowed phrase."""
    canonical = _normalize_phrase(spoken)
    if not canonical:
        return False
    return canonical in VALID_PHRASES
