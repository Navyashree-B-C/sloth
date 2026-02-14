"""
STT (speech-to-text) for SLOTH using OpenAI Whisper.

Optional: install with `pip install openai-whisper`. If not installed,
transcribe_audio raises RuntimeError and the transcribe endpoint returns 503.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

_whisper_model = None


def _get_whisper_model():
    """Lazy-load Whisper model. Prefer small model for speed (base or tiny)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
        except ImportError as e:
            raise RuntimeError(
                "Whisper not installed. Run: pip install openai-whisper"
            ) from e
        _whisper_model = whisper.load_model("base", device="cpu")
    return _whisper_model


def transcribe_audio(audio_path: Path, language: str = "en") -> str:
    """
    Transcribe audio file to text. Returns trimmed string or empty if nothing recognized.
    """
    model = _get_whisper_model()
    result = model.transcribe(str(audio_path), language=language, fp16=False)
    text = (result.get("text") or "").strip()
    return text
