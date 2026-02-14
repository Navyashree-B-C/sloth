"""
Pytest configuration and shared fixtures for SLOTH backend tests.
Mocks TTS and DB so tests run without Coqui or SQLite file.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Patch TTS and DB before importing app so they are mocked during app load.
FAKE_AUDIO_URL = "/static/audio/fake.wav"


@pytest.fixture(autouse=True)
def mock_tts_and_db():
    """Mock synthesize_tts and record_session_* in main so endpoint code doesn't call Coqui or DB."""
    async def fake_synthesize(_text: str) -> str:
        return FAKE_AUDIO_URL

    with (
        patch("app.main.synthesize_tts", new_callable=AsyncMock, side_effect=fake_synthesize),
        patch("app.main.record_session_start"),
        patch("app.main.record_session_end"),
    ):
        yield


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear in-memory session store before and after each test."""
    from app.core import session_store
    session_store._sessions.clear()
    yield
    session_store._sessions.clear()


@pytest.fixture
def client(mock_tts_and_db):
    """FastAPI test client with mocked TTS/DB."""
    from app.main import app
    return TestClient(app)
