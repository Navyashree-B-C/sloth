# SLOTH — Project Details

Complete reference for the SLOTH wake-up authority system: architecture, flow, APIs, and configuration.

---

## 1. Overview

**SLOTH** is a hybrid wake-up authority system. It is not an alarm app: it uses the OS alarm to wake you, then a web app takes over with voice, personality, and an interaction lock so you cannot exit without complying (saying/typing the correct keyword).

- **Layer 1:** Android (or any) alarm — guaranteed wake.
- **Layer 2:** SLOTH web app — voice, escalation, keyword gate, fullscreen, screen-on until release.

Discipline does not rely on motivation; the system enforces the wake-up.

---

## 2. System Architecture

| Layer | Responsibility |
|-------|----------------|
| **1 – Wake trigger (OS)** | Native alarm. Works with Bedtime ON, Wi‑Fi OFF. Only job: wake you. |
| **2 – Wake authority (SLOTH)** | App opens after alarm dismiss. Voice starts, screen stays on. Release only after correct keyword (and optionally proof/routine when enabled). |

---

## 3. Tech Stack

| Area | Choice |
|------|--------|
| **Frontend** | React + Vite, PWA (manifest, fullscreen, Wake Lock). Hosted on Vercel. |
| **Backend** | Python 3.11, FastAPI, Pydantic. In-memory session store; SQLite for wake history. |
| **Voice (TTS)** | Coqui TTS. Default speaker: Baldur Sanjin. Env: `SLOTH_TTS_SPEAKER`. |
| **Voice (STT)** | Whisper only (local, free) via `openai-whisper`. `POST /session/transcribe`. Requires **ffmpeg** (e.g. `brew install ffmpeg` on macOS). |
| **Android** | Tasker: alarm dismissed → open SLOTH URL with `?autostart=1&alarm_time=HH:mm`, Wi‑Fi on, keep screen on. |

---

## 4. Repository Structure

```
Sloth/
├── backend/
│   ├── app/
│   │   ├── main.py              # Session start, validate, nudge, proof, routine/next, transcribe
│   │   ├── core/
│   │   │   ├── constants.py     # VALID_KEYWORDS, SPOKEN_KEYWORDS, TYPED_KEYWORDS
│   │   │   ├── db.py            # SQLite wake_history (record_session_start/end)
│   │   │   ├── personality.py   # Personality model, DEFAULT_PERSONALITY
│   │   │   └── session_store.py # In-memory sessions, phases
│   │   ├── models/
│   │   │   └── session.py       # Pydantic request/response models
│   │   └── services/
│   │       ├── message_builder.py # build_message(), LISTENING_MESSAGES, phase buckets
│   │       ├── stt.py           # Whisper transcribe_audio()
│   │       └── tts.py           # Coqui synthesize_tts()
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py        # Mocks TTS/DB, clears session store, TestClient
│       └── test_api.py        # Session start, validate, nudge API tests
├── frontend/
│   ├── public/
│   │   └── manifest.webmanifest
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── vite.config.mts
│   └── package.json
├── vercel.json
├── README.md
├── SLOTH 🖤.md                  # Agile backlog / epic status
└── docs/
    └── PROJECT.md               # This file
```

---

## 5. Current Flow (Wake-Up Only)

**Camera proof** and **ROUTINE_ACTIVE (morning routine)** are **disabled** so the app focuses on the wake-up loop only.

### 5.1 Trigger

- **Android:** Alarm fires → user dismisses → Tasker opens URL:  
  `https://your-sloth-url.vercel.app/?autostart=1&alarm_time=07:30`
- **Desktop test:** Open `http://localhost:5173/?autostart=1&alarm_time=07:30` (or add `&delay_sec=0` to skip the 30 s delay).

### 5.2 Delay (optional)

- If `autostart=1` and no `delay_sec`: frontend shows a **30 s countdown** (“Wake up in N s…”).
- `?delay_sec=0` skips the delay and starts the session immediately.

### 5.3 Session start (AWAKENING)

1. Frontend calls **`POST /session/start`** with `{ alarm_time, user_name }`.
2. Backend creates a session (phase `AWAKENING`), records start in SQLite `wake_history`, builds an AWAKENING message and a “listening” prompt, synthesizes both with TTS, returns `session_id`, `text`, `audio_url`, `prompt_audio_url`.
3. Frontend plays **main message** then **listening prompt** (“Say the word. I’m listening.”), sets “Your turn. Speak now.”, shows keyword input and mic / Whisper record.
4. Fullscreen and Wake Lock are requested; `beforeunload` warns on close/refresh.

### 5.4 Idle loop (AWAKENING)

- If the user does nothing for **20 s**, frontend calls **`POST /session/nudge`**.
- Backend returns another AWAKENING message + listening prompt; frontend plays both.
- Repeats until the user submits a keyword.

### 5.5 Keyword (say + type)

- User can:
  - **Type** a word (e.g. “yes”, “ok”).
  - **Say (browser):** mic button → Web Speech API → transcript stored as `spoken`.
  - **Say (backend):** “Record (Whisper)” → ~4 s recording → **`POST /session/transcribe`** (audio file) → backend returns `{ text }` → frontend uses it as `spoken`.
- **Dual keyword (optional):** say one of `SPOKEN_KEYWORDS` (“awake”, “up”) and type one of `TYPED_KEYWORDS` (“yes”, “ok”, “okay”). If only typing, any of `VALID_KEYWORDS` is accepted.
- User submits → **`POST /session/validate`** with `session_id`, `keyword`, and optional `spoken`.

### 5.6 Validate → COMPLIANT → RELEASE

- **Wrong keyword:** Backend moves to RESISTING or ESCALATING, returns new message + listening prompt. Frontend plays both; user can retry.
- **First correct keyword:** Backend sets phase to **COMPLIANT**, returns COMPLIANT message + listening prompt. Frontend plays both; UI stays on keyword input.
- **Second correct keyword (while COMPLIANT):** Backend sets phase to **RELEASE**, calls `record_session_end(released=True)` in SQLite, returns RELEASE message (farewell). Frontend sets `released`, plays farewell, shows “Session complete. You’re done.” with closing animation, releases fullscreen and Wake Lock.

### 5.7 Flow summary (current)

```
Alarm dismiss → Open URL (?autostart=1&alarm_time=HH:mm)
  → [optional] 30 s countdown (?delay_sec=0 to skip)
  → POST /session/start → AWAKENING message + "Say the word. I'm listening."
  → [idle 20 s → POST /session/nudge → repeat AWAKENING + prompt]*
  → User says (mic or Whisper) + types keyword → POST /session/validate
  → COMPLIANT message + prompt ("Say the word again to finish.")
  → User says + types again → POST /session/validate
  → RELEASE message → Session complete → record_session_end() in SQLite
  → Closing animation, Wake Lock released.
```

---

## 6. API Reference

Base URL: backend root (e.g. `http://localhost:8001`).

| Method | Endpoint | Purpose |
|--------|----------|--------|
| POST | `/session/start` | Start wake session. Body: `{ alarm_time?, user_name? }`. Returns `session_id`, `phase`, `text`, `audio_url`, `prompt_text`, `prompt_audio_url`. |
| POST | `/session/validate` | Validate keyword (and optional spoken). Body: `{ session_id, keyword, spoken? }`. Returns `valid`, `phase`, `text`, `audio_url`, `released`, `prompt_*`. |
| POST | `/session/nudge` | Request another AWAKENING line when idle. Body: `{ session_id }`. Only valid in AWAKENING. |
| POST | `/session/transcribe` | Speech-to-text (Whisper). Body: multipart `audio` file. Returns `{ text }`. Requires `openai-whisper`. |
| POST | `/session/proof` | **(Currently unused.)** Mark proof of action (camera) captured. Body: `{ session_id }`. |
| POST | `/session/routine/next` | **(Currently unused.)** Advance routine step. Body: `{ session_id }`. Only in ROUTINE_ACTIVE. |

Static TTS files are served under `/static/audio/`.

---

## 7. Configuration

### 7.1 Frontend

- **API base:** `VITE_API_BASE` (default `http://localhost:8001`).
- **Query params:**
  - `autostart=1` — Start session automatically on load.
  - `alarm_time=HH:mm` — Passed to `POST /session/start`.
  - `delay_sec=N` — Override delay before first TTS (default 30). Use `0` to skip.

### 7.2 Backend

- **TTS speaker:** `SLOTH_TTS_SPEAKER` (default `Baldur Sanjin`). Other options: Damien Black, Wulf Carlevaro, Torcull Diarmuid, etc.
- **SQLite:** Wake history is stored in `backend/sloth_wake.db` (created automatically).

### 7.3 Keywords (backend `core/constants.py`)

- **VALID_KEYWORDS** — Typed-only mode: e.g. `awake`, `up`, `yes`, `ok`, `okay`.
- **SPOKEN_KEYWORDS** — Dual mode (say): `awake`, `up`.
- **TYPED_KEYWORDS** — Dual mode (type): `yes`, `ok`, `okay`.

---

## 8. Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# Optional for male voice: brew install espeak-ng
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Test flow

Open: `http://localhost:5173/?autostart=1&alarm_time=07:30&delay_sec=0`  
Then say/type the keyword twice (first → COMPLIANT, second → RELEASE).

---

## 9. Disabled / Future Features

- **Camera proof :** Backend supports `proof_captured` and `POST /session/proof`; frontend has camera UI code but it is not shown in the current flow. To re-enable: restore the validate logic that requires proof before release and show camera when COMPLIANT.
- **Morning routine :** Backend supports ROUTINE_ACTIVE and `POST /session/routine/next`; frontend has routine UI but it is not shown. To re-enable: restore the validate path COMPLIANT → ROUTINE_ACTIVE → (routine steps) → RELEASE and show “Next step” / “Routine complete” in the UI.

---

## 10. Backend tests

- **Location:** `backend/tests/` (pytest).
- **Run:** From repo root: `cd backend && python -m pytest tests/ -v`
- **Scope:** Session API only: `POST /session/start`, `/session/validate`, `/session/nudge`. TTS and DB are mocked so tests run without Coqui or SQLite.
- **Coverage:** Start returns AWAKENING; validate unknown session 404; wrong keyword → RESISTING/ESCALATING; correct keyword once → COMPLIANT, twice → RELEASE; dual keyword (spoken + typed); nudge in AWAKENING; nudge unknown 404; nudge when not AWAKENING 400.

---

*SLOTH doesn’t ring. It insists.*
