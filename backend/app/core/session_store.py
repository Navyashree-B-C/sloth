"""
In-memory session store for wake sessions.
Single-user; no auth. Session state: phase + escalation_level.
"""

import uuid
from dataclasses import dataclass

# Phase flow: AWAKENING -> (keyword) -> RESISTING/ESCALATING or COMPLIANT -> RELEASE
VALID_PHASES = frozenset({"AWAKENING", "RESISTING", "ESCALATING", "COMPLIANT", "ROUTINE_ACTIVE", "RELEASE"})


@dataclass
class SessionState:
    """State for one wake session."""

    session_id: str
    phase: str
    escalation_level: int
    # How many times we've nudged this session with AWAKENING lines (idle repeats).
    nudge_count: int = 0
    # How many failed keyword attempts (wrong word).
    failed_attempts: int = 0
    # Proof of action (camera) captured before release (EPIC 5).
    proof_captured: bool = False
    # Routine (EPIC 6): current step index; when routine_complete, next correct keyword releases.
    routine_step: int = 0
    routine_complete: bool = False
    # Two-step flow: True after user said the correct phrase; next we expect typed yes/ok.
    spoken_verified: bool = False

    def __post_init__(self) -> None:
        if self.phase not in VALID_PHASES:
            raise ValueError(f"Invalid phase: {self.phase!r}")


# In-memory store: session_id -> SessionState
_sessions: dict[str, SessionState] = {}


def create_session(phase: str = "AWAKENING", escalation_level: int = 0) -> SessionState:
    """Create a new session and return its state."""
    session_id = str(uuid.uuid4())
    state = SessionState(session_id=session_id, phase=phase, escalation_level=escalation_level)
    _sessions[session_id] = state
    return state


def get_session(session_id: str) -> SessionState | None:
    """Return session state if it exists."""
    return _sessions.get(session_id)


def update_session(session_id: str, phase: str, escalation_level: int) -> SessionState | None:
    """Update session phase and level. Returns updated state or None if not found."""
    state = _sessions.get(session_id)
    if not state:
        return None
    state.phase = phase
    state.escalation_level = escalation_level
    return state


def set_proof_captured(session_id: str) -> bool:
    """Mark proof of action (camera) as captured. Returns True if session exists."""
    state = _sessions.get(session_id)
    if not state:
        return False
    state.proof_captured = True  # type: ignore[attr-defined]
    return True


def set_spoken_verified(session_id: str, value: bool = True) -> bool:
    """Mark that the user said the correct phrase; next step is to type yes/ok. Returns True if session exists."""
    state = _sessions.get(session_id)
    if not state:
        return False
    state.spoken_verified = value  # type: ignore[attr-defined]
    return True


def advance_routine_step(session_id: str, num_steps: int) -> tuple[bool, int, bool]:
    """
    Advance routine step. Returns (ok, current_step_index, routine_complete).
    """
    state = _sessions.get(session_id)
    if not state or state.phase != "ROUTINE_ACTIVE":
        return (False, 0, False)
    state.routine_step = getattr(state, "routine_step", 0) + 1  # type: ignore[attr-defined]
    step = state.routine_step
    if step >= num_steps:
        state.routine_complete = True  # type: ignore[attr-defined]
    return (True, step, getattr(state, "routine_complete", False))
