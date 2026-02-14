import random
from dataclasses import dataclass
from typing import Any, Dict, List

from ..core.personality import DEFAULT_PERSONALITY, Personality


# Phase buckets: sarcastic, authoritative. Punctuation creates natural pause.
PHASE_MESSAGES: Dict[str, List[str]] = {
    "AWAKENING": [
        "Hey. Wake up.\nNow.",
        "Eyes open... right now.",
        "Up. On your feet.",
        "Rise up... before this gets unpleasant.",
        "Get up. You're not in charge here.",
        "Alarm's over. Sleep is not.",
        "You said you'd wake.\nProve it.",
        "This is not optional. Get up.",
        "You are awake now... act like it.",
    ],
    "RESISTING": [
        "That's the wrong word. Say awake or up, then type yes or ok.",
        "That was wrong... try again.",
        "Wrong word. Say it right.",
        "Nice try. Again.",
        "You know the word. Use it.",
        "You're stalling. I see you.",
        "Cute. Fix it.",
        "Is that really your best? Say the word.",
    ],
    "ESCALATING": [
        "Sit up. Now.",
        "No more stalling. Say the word.",
        "Say the word... correctly.",
        "Are you still lying down? Fix that.",
        "Last chance. Don't blow it.",
        "Get moving. I'm done waiting.",
    ],
    "COMPLIANT": [
        "Good... stay with me.",
        "That's more like it.",
        "There we go.\nDon't drift.",
        "I knew you'd listen.",
        "Better. Keep going.",
        "See? You can do this.",
    ],
    "ROUTINE_ACTIVE": [
        "Posture. Fix it.",
        "Hold it. Don't rush.",
        "Slow down. I'm watching.",
        "Focus. Almost there.",
    ],
    "RELEASE": [
        "You're done. Good work.",
        "That's it. See you tomorrow.",
        "We're finished. Rest earned.",
    ],
}

# In-character prompt played before user's speaking turn (EPIC 10). Picked at random.
LISTENING_MESSAGES = [
    "Say the word. I'm listening.",
    "Your turn. Say it.",
    "Go on. I'm listening.",
    "Say the word.",
    "I'm listening. Say it.",
    "Your turn. Say the word.",
    "Say it. I'm waiting.",
    "The word. Now.",
    "Go on. Say the word.",
    "Say the word. Your turn.",
]


@dataclass
class BuiltMessage:
    template_id: str
    text: str


def _pick_index(escalation_level: int, max_index: int, use_random: bool) -> int:
    """
    Pick message index: higher escalation -> more intense messages.
    use_random adds variety so same phase doesn't always repeat.
    """
    if escalation_level < 0:
        base = 0
    elif escalation_level > max_index:
        base = max_index
    else:
        base = escalation_level

    if use_random and max_index >= 0:
        return random.randint(0, max(max_index, base))
    return min(base, max_index)


def build_message(
    phase: str,
    escalation_level: int,
    context: Dict[str, Any] | None = None,
    personality: Personality = DEFAULT_PERSONALITY,
    randomize: bool = True,
) -> BuiltMessage:
    """
    Build personality-driven message for a phase.

    randomize=True adds variety; same phase returns different punchy lines.
    escalation_level pushes toward more intense messages when resisting.
    """
    bucket = PHASE_MESSAGES.get(phase.upper())
    if not bucket:
        raise ValueError(f"Unknown phase for message builder: {phase!r}")

    max_idx = len(bucket) - 1
    idx = _pick_index(escalation_level, max_idx, use_random=randomize)
    raw = bucket[idx]

    ctx = context or {}
    text = raw.format(**{k: v for k, v in ctx.items() if isinstance(v, str)})

    template_id = f"{personality.id}:{phase.upper()}:{idx}"
    return BuiltMessage(template_id=template_id, text=text)


def build_listening_prompt(randomize: bool = True) -> BuiltMessage:
    """Build a short 'say the word / I'm listening' prompt before the user's speaking turn."""
    idx = random.randint(0, len(LISTENING_MESSAGES) - 1) if randomize else 0
    text = LISTENING_MESSAGES[idx]
    return BuiltMessage(template_id=f"listening:{idx}", text=text)

