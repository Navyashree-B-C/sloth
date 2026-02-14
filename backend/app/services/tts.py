"""
Coqui TTS integration for SLOTH voice output.

Uses the free, open-source Coqui TTS library. Model is loaded lazily on first use.
Synthesis runs in a thread pool to avoid blocking the async event loop.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Final

# Store Coqui models in project; avoids global cache dir.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
os.environ.setdefault("XDG_DATA_HOME", str(_BACKEND_DIR / ".tts_cache"))
# XTTS requires ToS agreement; set for non-interactive use (CPML non-commercial).
os.environ["COQUI_TOS_AGREED"] = "1"
# Ensure espeak-ng is found when uvicorn runs from IDE (PATH may lack /opt/homebrew/bin).
_homebrew_bin = Path("/opt/homebrew/bin")
if _homebrew_bin.exists():
    _path = os.environ.get("PATH", "")
    if str(_homebrew_bin) not in _path:
        os.environ["PATH"] = f"{_homebrew_bin}:{_path}"

TTS_BASE_URL: Final[str] = "/static/audio"
# XTTS: deep, character-like male. Override with env SLOTH_TTS_SPEAKER.
# Deep/character options: Damien Black, Wulf Carlevaro, Baldur Sanjin, Torcull Diarmuid.
# Others: Craig Gutsy, Andrew Chipper, Viktor Menelaos.
COQUI_MODEL: Final[str] = "tts_models/multilingual/multi-dataset/xtts_v2"
COQUI_SPEAKER: Final[str] = os.environ.get("SLOTH_TTS_SPEAKER", "Baldur Sanjin")
COQUI_LANGUAGE: Final[str] = "en"
COQUI_FALLBACK_MODEL: Final[str] = "tts_models/en/vctk/vits"
COQUI_FALLBACK_SPEAKER: Final[str] = "p225"
COQUI_LAST_RESORT_MODEL: Final[str] = "tts_models/en/ljspeech/tacotron2-DDC"

_tts_instance = None


def _get_tts():
    """Lazy-load the Coqui TTS model. Blocking; call from thread pool."""
    global _tts_instance
    if _tts_instance is None:
        import torch
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Prefer XTTS (expressive male); fall back to VCTK then tacotron2.
        for model, speaker, use_speaker, is_xtts in [
            (COQUI_MODEL, COQUI_SPEAKER, True, True),
            (COQUI_FALLBACK_MODEL, COQUI_FALLBACK_SPEAKER, True, False),
            (COQUI_LAST_RESORT_MODEL, None, False, False),
        ]:
            try:
                _tts_instance = TTS(model).to(device)
                _tts_instance._speaker = speaker
                _tts_instance._use_speaker = use_speaker
                _tts_instance._is_xtts = is_xtts
                break
            except (FileNotFoundError, OSError) as e:
                err = str(e).lower()
                if "espeak" in err and model == COQUI_FALLBACK_MODEL:
                    continue  # Try tacotron2
                elif model != COQUI_LAST_RESORT_MODEL:
                    continue
                raise
    return _tts_instance


def _apply_fade_in(wav_path: Path, fade_ms: int = 25) -> None:
    """
    Apply short fade-in to soften start click. No extra delay.
    Ramps first N ms from 0 to 1. In-place.
    """
    import struct
    import wave

    with wave.open(str(wav_path), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())

    rate = params.framerate
    n_channels = params.nchannels
    samp_width = params.sampwidth
    total_samples = len(frames) // samp_width
    n_fade_samples = min(int(rate * fade_ms / 1000) * n_channels, total_samples)

    if n_fade_samples <= 0:
        return

    fmt = {1: "b", 2: "h", 4: "i"}.get(samp_width, "h")
    fade_data = frames[: n_fade_samples * samp_width]
    samples = list(struct.iter_unpack(f"<{fmt}", fade_data))

    faded = [int(s[0] * (i + 1) / n_fade_samples) for i, s in enumerate(samples)]
    new_frames = struct.pack(f"<{len(faded)}{fmt}", *faded) + frames[n_fade_samples * samp_width :]

    with wave.open(str(wav_path), "wb") as w:
        w.setparams(params)
        w.writeframes(new_frames)


def _synthesize_to_file(text: str, out_path: Path) -> None:
    """
    Synthesize text to WAV file. Blocking; run in thread pool.

    Uses split_sentences=False for short phrases. Applies brief fade-in to
    soften start click without adding delay.
    """
    tts = _get_tts()
    if getattr(tts, "_use_speaker", False):
        if getattr(tts, "_is_xtts", False):
            tts.tts_to_file(
                text=text,
                speaker=tts._speaker,
                language=COQUI_LANGUAGE,
                file_path=str(out_path),
                split_sentences=False,
            )
        else:
            tts.tts_to_file(text=text, speaker=tts._speaker, file_path=str(out_path))
    else:
        tts.tts_to_file(text=text, file_path=str(out_path))

    _apply_fade_in(out_path)


# Bump when changing voice/model or post-processing to regenerate audio.
TTS_CACHE_VERSION: Final[int] = 6


async def synthesize_tts(text: str) -> str:
    """
    Synthesize text to speech using Coqui TTS.

    Writes a WAV file to static/audio and returns the served URL.
    Cache key includes TTS_CACHE_VERSION so voice changes regenerate audio.
    """
    safe_id = abs(hash((text, TTS_CACHE_VERSION))) % 10_000_000
    filename = f"{safe_id}.wav"

    app_dir = Path(__file__).resolve().parents[1]  # backend/app
    audio_dir = app_dir / "static" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    out_path = audio_dir / filename
    if not out_path.exists():
        await asyncio.to_thread(_synthesize_to_file, text, out_path)

    return f"{TTS_BASE_URL}/{filename}"
