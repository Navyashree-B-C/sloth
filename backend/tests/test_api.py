"""
API tests for session start, validate, and nudge.
Two-step flow: (1) say phrase -> spoken_verified; (2) type yes/ok -> COMPLIANT -> RELEASE.
Uses mocked TTS/DB via conftest.
"""

import uuid

import pytest


def test_session_start_returns_awakening(client):
    """POST /session/start returns 200, phase AWAKENING, and audio URLs."""
    r = client.post(
        "/session/start",
        json={"alarm_time": "07:00", "user_name": "Test"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["phase"] == "AWAKENING"
    assert data["escalation_level"] == 0
    assert "session_id" in data and len(data["session_id"]) > 0
    assert data["audio_url"] == "/static/audio/fake.wav"
    assert data["prompt_audio_url"] == "/static/audio/fake.wav"
    assert "text" in data and "prompt_text" in data


def test_validate_unknown_session_404(client):
    """POST /session/validate with unknown session_id returns 404."""
    r = client.post(
        "/session/validate",
        json={"session_id": str(uuid.uuid4()), "keyword": "yes"},
    )
    assert r.status_code == 404


def test_validate_wrong_phrase_returns_not_valid(client):
    """POST /session/validate with wrong phrase (step 1) returns valid=False, RESISTING/ESCALATING."""
    start = client.post("/session/start", json={"alarm_time": "07:00"})
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    r = client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "wrongphrase", "spoken": "wrongphrase"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert data["phase"] in ("RESISTING", "ESCALATING")
    assert data["released"] is False
    assert data["spoken_verified"] is False
    assert data["audio_url"] == "/static/audio/fake.wav"


def test_validate_phrase_then_type_compliant_then_release(client):
    """Step 1: correct phrase -> spoken_verified. Step 2: yes -> COMPLIANT. Step 3: yes -> RELEASE."""
    start = client.post("/session/start", json={"alarm_time": "07:00"})
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    v0 = client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "i'm awake", "spoken": "i'm awake"},
    )
    assert v0.status_code == 200
    d0 = v0.json()
    assert d0["valid"] is True
    assert d0["spoken_verified"] is True
    assert d0["released"] is False

    v1 = client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "yes"},
    )
    assert v1.status_code == 200
    d1 = v1.json()
    assert d1["valid"] is True
    assert d1["phase"] == "COMPLIANT"
    assert d1["released"] is False
    assert d1["spoken_verified"] is True

    v2 = client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "yes"},
    )
    assert v2.status_code == 200
    d2 = v2.json()
    assert d2["valid"] is True
    assert d2["phase"] == "RELEASE"
    assert d2["released"] is True
    assert d2["spoken_verified"] is True


def test_validate_wrong_typed_after_phrase_returns_not_valid(client):
    """After phrase OK, wrong typed keyword returns valid=False."""
    start = client.post("/session/start", json={"alarm_time": "07:00"})
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "awake", "spoken": "awake"},
    )

    r = client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "nope"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert data["spoken_verified"] is True
    assert data["released"] is False


def test_nudge_returns_awakening(client):
    """POST /session/nudge with valid AWAKENING session returns 200 and AWAKENING message."""
    start = client.post("/session/start", json={"alarm_time": "07:00"})
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    r = client.post("/session/nudge", json={"session_id": session_id})
    assert r.status_code == 200
    data = r.json()
    assert data["phase"] == "AWAKENING"
    assert data["audio_url"] == "/static/audio/fake.wav"
    assert data["prompt_audio_url"] == "/static/audio/fake.wav"


def test_nudge_unknown_session_404(client):
    """POST /session/nudge with unknown session_id returns 404."""
    r = client.post(
        "/session/nudge",
        json={"session_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


def test_nudge_non_awakening_400(client):
    """POST /session/nudge when session is past AWAKENING (e.g. COMPLIANT) returns 400."""
    start = client.post("/session/start", json={"alarm_time": "07:00"})
    session_id = start.json()["session_id"]
    client.post(
        "/session/validate",
        json={"session_id": session_id, "keyword": "awake", "spoken": "awake"},
    )
    client.post("/session/validate", json={"session_id": session_id, "keyword": "yes"})

    r = client.post("/session/nudge", json={"session_id": session_id})
    assert r.status_code == 400
