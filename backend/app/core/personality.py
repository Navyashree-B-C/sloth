from dataclasses import dataclass


@dataclass(frozen=True)
class Personality:
    """
    Describes how the system should talk.

    This is intentionally small and deterministic so that
    message selection stays predictable and testable.
    """

    id: str
    tone: str  # e.g. "sarcastic", "caring"
    intensity_curve: str  # e.g. "fast", "medium", "slow"
    swear_allowance: bool = False


DEFAULT_PERSONALITY = Personality(
    id="default_savage",
    tone="sarcastic",
    intensity_curve="fast",
    swear_allowance=False,
)

