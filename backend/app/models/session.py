from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    """Input from frontend when a wake session begins."""

    alarm_time: str | None = None
    user_name: str | None = None


class MessageOut(BaseModel):
    """Represents a single personality-engine message."""

    template_id: str
    text: str


class SessionStartResponse(BaseModel):
    """Initial response when a session starts. Optional listening prompt before user speaks."""

    session_id: str
    phase: str
    escalation_level: int
    message_id: str
    text: str
    audio_url: str
    prompt_text: str | None = None
    prompt_audio_url: str | None = None


class SessionValidateRequest(BaseModel):
    """Input when user submits keyword for validation. Optional spoken for STT/dual-keyword mode."""

    session_id: str
    keyword: str
    spoken: str | None = None


class SessionValidateResponse(BaseModel):
    """Response after keyword validation; includes next message and audio. Optional listening prompt."""

    valid: bool
    phase: str
    escalation_level: int
    message_id: str
    text: str
    audio_url: str
    released: bool  # True when session is complete (RELEASE phase)
    prompt_text: str | None = None
    prompt_audio_url: str | None = None
    spoken_verified: bool = False  # True when step 1 (phrase) passed; frontend shows type step

