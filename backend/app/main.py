import asyncio
import os
import random
import tempfile
from pathlib import Path

# Coqui TTS pulls in matplotlib; use project-local cache to avoid permission issues.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(_BACKEND_DIR / ".mpl"))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.constants import TYPED_KEYWORDS, is_phrase_valid
from .core.personality import DEFAULT_PERSONALITY
from .core.db import record_session_end, record_session_start
from .core.session_store import (
    advance_routine_step,
    create_session,
    get_session,
    set_proof_captured,
    set_spoken_verified,
    update_session,
)
from .models.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionValidateRequest,
    SessionValidateResponse,
)
from .services.message_builder import (
    PHASE_MESSAGES,
    BuiltMessage,
    build_listening_prompt,
    build_message,
)
from .services.stt import transcribe_audio
from .services.tts import synthesize_tts

class SessionNudgeRequest(BaseModel):
    """Backend-only model: request another AWAKENING line when user is idle."""

    session_id: str


class SessionProofRequest(BaseModel):
    """Request to mark proof of action (camera) as captured."""

    session_id: str


class SessionProofResponse(BaseModel):
    """Response after proof capture."""

    ok: bool


class SessionRoutineNextRequest(BaseModel):
    """Request to advance to next routine step."""

    session_id: str


class SessionRoutineNextResponse(BaseModel):
    """Response with next routine step message and completion flag."""

    step_index: int
    text: str
    audio_url: str
    routine_complete: bool
    prompt_text: str | None = None
    prompt_audio_url: str | None = None


class TranscribeResponse(BaseModel):
    """Response from speech-to-text endpoint."""

    text: str


app = FastAPI(title="SLOTH Backend")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/session/start", response_model=SessionStartResponse)
async def start_session(payload: SessionStartRequest) -> SessionStartResponse:
    """
    Start a wake session and return the first personality-driven voice message.
    """
    state = create_session(phase="AWAKENING", escalation_level=0)
    record_session_start(state.session_id)

    message = build_message(
        phase="AWAKENING",
        escalation_level=0,
        context={
            "time": payload.alarm_time,
            "userName": payload.user_name or "you",
        },
        personality=DEFAULT_PERSONALITY,
        randomize=True,
    )

    audio_url = await synthesize_tts(message.text)
    prompt = build_listening_prompt(randomize=True)
    prompt_audio_url = await synthesize_tts(prompt.text)

    return SessionStartResponse(
        session_id=state.session_id,
        phase=state.phase,
        escalation_level=state.escalation_level,
        message_id=message.template_id,
        text=message.text,
        audio_url=audio_url,
        prompt_text=prompt.text,
        prompt_audio_url=prompt_audio_url,
    )


@app.post("/session/validate", response_model=SessionValidateResponse)
async def validate_session(payload: SessionValidateRequest) -> SessionValidateResponse:
    """
    Two-step validation: (1) spoken phrase -> spoken_verified; (2) typed yes/ok -> COMPLIANT -> RELEASE.
    """
    state = get_session(payload.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    context = {"userName": "you"}
    spoken_verified = getattr(state, "spoken_verified", False)

    # Step 1: validate spoken phrase only (no typing yet).
    if not spoken_verified:
        spoken = (payload.spoken or payload.keyword or "").strip()
        if not spoken:
            failed_attempts = getattr(state, "failed_attempts", 0)
            if failed_attempts > 0:
                # User already tried and is now silent: move into RESISTING/ESCALATING
                # personality messages instead of repeating the same wrong-phrase line.
                msg = build_message(
                    phase=state.phase,
                    escalation_level=state.escalation_level,
                    context=context,
                    personality=DEFAULT_PERSONALITY,
                    randomize=True,
                )
            else:
                # First time with no speech: explicit instruction about the phrase.
                wrong_text = "Say the phrase: I'm awake or I'm up."
                msg = BuiltMessage(template_id="prompt:say_phrase", text=wrong_text)

            audio_url = await synthesize_tts(msg.text)
            prompt = build_listening_prompt(randomize=True)
            prompt_audio_url = await synthesize_tts(prompt.text)
            return SessionValidateResponse(
                valid=False,
                phase=state.phase,
                escalation_level=state.escalation_level,
                message_id=msg.template_id,
                text=msg.text,
                audio_url=audio_url,
                released=False,
                prompt_text=prompt.text,
                prompt_audio_url=prompt_audio_url,
                spoken_verified=False,
            )
        if is_phrase_valid(spoken):
            set_spoken_verified(payload.session_id)
            correct_text = "Correct. Now type yes or ok."
            audio_url = await synthesize_tts(correct_text)
            return SessionValidateResponse(
                valid=True,
                phase=state.phase,
                escalation_level=state.escalation_level,
                message_id="correct:phrase",
                text=correct_text,
                audio_url=audio_url,
                released=False,
                prompt_text=None,
                prompt_audio_url=None,
                spoken_verified=True,
            )
        # Wrong phrase: RESISTING/ESCALATING.
        new_level = state.escalation_level + 1
        try:
            state.failed_attempts += 1  # type: ignore[attr-defined]
        except AttributeError:
            pass
        if new_level == 1:
            new_phase = "RESISTING"
        else:
            p_escalate = min(0.2 * new_level, 0.8)
            new_phase = "ESCALATING" if random.random() < p_escalate else "RESISTING"
        update_session(payload.session_id, phase=new_phase, escalation_level=new_level)
        wrong_text = "Wrong phrase. Say: I'm awake or I'm up."
        msg = BuiltMessage(template_id="resisting:wrong_phrase", text=wrong_text)
        audio_url = await synthesize_tts(msg.text)
        prompt = build_listening_prompt(randomize=True)
        prompt_audio_url = await synthesize_tts(prompt.text)
        return SessionValidateResponse(
            valid=False,
            phase=new_phase,
            escalation_level=new_level,
            message_id=msg.template_id,
            text=msg.text,
            audio_url=audio_url,
            released=False,
            prompt_text=prompt.text,
            prompt_audio_url=prompt_audio_url,
            spoken_verified=False,
        )

    # Step 2: validate typed keyword only (yes/ok/okay).
    kw = payload.keyword.strip().lower()
    if kw not in TYPED_KEYWORDS:
        new_level = state.escalation_level + 1
        try:
            state.failed_attempts += 1  # type: ignore[attr-defined]
        except AttributeError:
            pass
        if new_level == 1:
            new_phase = "RESISTING"
        else:
            p_escalate = min(0.2 * new_level, 0.8)
            new_phase = "ESCALATING" if random.random() < p_escalate else "RESISTING"
        update_session(payload.session_id, phase=new_phase, escalation_level=new_level)
        msg = build_message(
            phase=new_phase,
            escalation_level=new_level,
            context=context,
            personality=DEFAULT_PERSONALITY,
            randomize=True,
        )
        audio_url = await synthesize_tts(msg.text)
        prompt = build_listening_prompt(randomize=True)
        prompt_audio_url = await synthesize_tts(prompt.text)
        return SessionValidateResponse(
            valid=False,
            phase=new_phase,
            escalation_level=new_level,
            message_id=msg.template_id,
            text=msg.text,
            audio_url=audio_url,
            released=False,
            prompt_text=prompt.text,
            prompt_audio_url=prompt_audio_url,
            spoken_verified=True,
        )

    # Typed keyword correct: first time -> COMPLIANT, second time -> RELEASE.
    if state.phase != "COMPLIANT":
        update_session(payload.session_id, phase="COMPLIANT", escalation_level=0)
        correct_text = "Correct. One more time — type yes or ok."
        audio_url = await synthesize_tts(correct_text)
        prompt = build_listening_prompt(randomize=True)
        prompt_audio_url = await synthesize_tts(prompt.text)
        return SessionValidateResponse(
            valid=True,
            phase="COMPLIANT",
            escalation_level=0,
            message_id="correct:type1",
            text=correct_text,
            audio_url=audio_url,
            released=False,
            prompt_text=prompt.text,
            prompt_audio_url=prompt_audio_url,
            spoken_verified=True,
        )

    update_session(payload.session_id, phase="RELEASE", escalation_level=0)
    state = get_session(payload.session_id)
    if state:
        record_session_end(
            payload.session_id,
            released=True,
            failed_attempts=getattr(state, "failed_attempts", 0),
            nudge_count=getattr(state, "nudge_count", 0),
        )
    correct_text = "Correct. You're done."
    audio_url = await synthesize_tts(correct_text)
    return SessionValidateResponse(
        valid=True,
        phase="RELEASE",
        escalation_level=0,
        message_id="correct:release",
        text=correct_text,
        audio_url=audio_url,
        released=True,
        spoken_verified=True,
    )


@app.post("/session/nudge", response_model=SessionValidateResponse)
async def nudge_session(payload: SessionNudgeRequest) -> SessionValidateResponse:
    """
    Repeat AWAKENING messages when the user is idle (no keyword yet).

    Only valid while the session is still in AWAKENING phase.
    """
    state = get_session(payload.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.phase != "AWAKENING":
        raise HTTPException(
            status_code=400, detail="Nudges are only allowed in AWAKENING phase"
        )

    context = {"userName": "you"}

    # Track how many times we've nudged this session (idle AWAKENING repeats).
    try:
        state.nudge_count += 1  # type: ignore[attr-defined]
    except AttributeError:
        # Older sessions without the field – ignore.
        pass

    message = build_message(
        phase="AWAKENING",
        escalation_level=0,
        context=context,
        personality=DEFAULT_PERSONALITY,
        randomize=True,
    )
    audio_url = await synthesize_tts(message.text)
    prompt = build_listening_prompt(randomize=True)
    prompt_audio_url = await synthesize_tts(prompt.text)
    return SessionValidateResponse(
        valid=False,
        phase="AWAKENING",
        escalation_level=state.escalation_level,
        message_id=message.template_id,
        text=message.text,
        audio_url=audio_url,
        released=False,
        prompt_text=prompt.text,
        prompt_audio_url=prompt_audio_url,
    )


@app.post("/session/proof", response_model=SessionProofResponse)
async def submit_proof(payload: SessionProofRequest) -> SessionProofResponse:
    """Mark proof of action (camera) as captured for this session. Required before release."""
    if not get_session(payload.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    ok = set_proof_captured(payload.session_id)
    return SessionProofResponse(ok=ok)


NUM_ROUTINE_STEPS = len(PHASE_MESSAGES.get("ROUTINE_ACTIVE", []))


@app.post("/session/routine/next", response_model=SessionRoutineNextResponse)
async def routine_next(payload: SessionRoutineNextRequest) -> SessionRoutineNextResponse:
    """Advance to next routine step. Returns message and routine_complete when done."""
    state = get_session(payload.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    ok, step_index, routine_complete = advance_routine_step(
        payload.session_id, NUM_ROUTINE_STEPS
    )
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Routine next only allowed in ROUTINE_ACTIVE phase.",
        )
    context = {"userName": "you"}
    message = build_message(
        phase="ROUTINE_ACTIVE",
        escalation_level=min(step_index, NUM_ROUTINE_STEPS - 1),
        context=context,
        personality=DEFAULT_PERSONALITY,
        randomize=False,
    )
    audio_url = await synthesize_tts(message.text)
    prompt = build_listening_prompt(randomize=True)
    prompt_audio_url = await synthesize_tts(prompt.text)
    return SessionRoutineNextResponse(
        step_index=step_index,
        text=message.text,
        audio_url=audio_url,
        routine_complete=routine_complete,
        prompt_text=prompt.text,
        prompt_audio_url=prompt_audio_url,
    )


@app.post("/session/transcribe", response_model=TranscribeResponse)
async def transcribe_session_audio(audio: UploadFile = File(...)) -> TranscribeResponse:
    """
    Transcribe uploaded audio to text using Whisper. Accepts WAV, WebM, MP3, etc.
    Returns { "text": "..." }. Requires: pip install openai-whisper.
    """
    suffix = Path(audio.filename or "audio").suffix or ".webm"
    try:
        content = await audio.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio: {e}") from e
    if not content:
        return TranscribeResponse(text="")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            path = Path(tmp.name)
        try:
            text = await asyncio.to_thread(transcribe_audio, path, "en")
            return TranscribeResponse(text=text)
        finally:
            path.unlink(missing_ok=True)
    except FileNotFoundError as e:
        if "ffmpeg" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Whisper needs ffmpeg. Install it (e.g. brew install ffmpeg on macOS).",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
    except RuntimeError as e:
        if "not installed" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Speech-to-text not available. Install: pip install openai-whisper",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e

