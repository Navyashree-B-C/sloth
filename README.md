# SLOTH

SLOTH is a wake-enforcement web system designed to eliminate snoozing and post-alarm drift through structured interaction.

It activates during your wake window and maintains control until you complete a required confirmation flow.

No passive reminders.  
No reliance on motivation.  
Just enforced engagement.

---

## 🧠 The Problem

Most alarm systems succeed at one thing: making noise.

They fail at the critical window immediately after dismissal — when users drift back into bed, scroll, or stall.

Waking up isn't a willpower problem.

It's a systems problem.

SLOTH is built to occupy that vulnerable window and replace drift with structured action.

---

## ⚙️ How SLOTH Works

1. Your wake time arrives.
2. Android automation launches SLOTH in the browser.
3. A short tap enables audio (browser requirement).
4. Voice begins immediately.
5. You must:
   - Say the required phrase (e.g., "I'm awake" / "I'm up")
   - Type the confirmation keyword (yes or ok)

Until both confirmations are completed, the session remains active.

This dual-input requirement (speech + typed confirmation) prevents passive dismissal.

---

## 🔥 Core Capabilities

- Voice-driven wake interaction (not just alarm sounds)
- Personality-based messaging system
- Escalation logic if delayed or incorrect
- Interaction lock requiring explicit compliance
- Deterministic session start via query parameters
- Lightweight, PWA-style fullscreen interface

---

## 🌐 Live App

[https://sloth.vercel.app](https://sloth.vercel.app)

---

## 🧩 Architecture Overview

SLOTH uses a hybrid structure:

**1️⃣ Trigger Layer (Automation)**  
Android automation tools (MacroDroid or Automate) launch SLOTH during the wake window. This separates system-level scheduling from enforcement logic.

**2️⃣ Authority Layer (Web + Backend)**  
Once launched:

- Frontend manages interaction state
- Backend validates session flow
- Voice synthesis delivers escalating prompts
- Session remains active until compliance is confirmed

This separation keeps the system deterministic and modular.

---

## 🛠 Tech Stack

### Frontend

- React
- Vite
- Web Audio API
- PWA-style fullscreen behavior

### Backend

- Python 3.11
- FastAPI
- Pydantic
- SQLite (upgradeable)

### Voice

- Coqui XTTS — speaker configurable via `SLOTH_TTS_SPEAKER`
- Local TTS keeps latency low and avoids external API dependency.

---

## 🤖 Android Automation Setup

SLOTH relies on external automation tools to launch at the correct time.

You can use **MacroDroid** or **Automate**.

### Example — Time-based trigger

- **Trigger:** Day/Time at wake time
- **Action:** Open website  
  `https://sloth.vercel.app/?autostart=1&alarm_time=HH:mm`  
  Optional: add `&delay_sec=0` to skip countdown.

### Example — Wake window trigger (recommended)

- **Trigger:** Device active within a time window (e.g. Device unlocked)
- **Constraint:** Between e.g. 6:00–8:00 AM
- **Action:** Open website  
  `https://sloth.vercel.app/?autostart=1&delay_sec=0`

---

## 🧪 Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

**Test locally:**  
`http://localhost:5173/?autostart=1&alarm_time=07:30` — add `&delay_sec=0` to skip countdown.

---

## 📁 Repository Structure

```
sloth/
├── backend/
│   ├── app/
│   │   ├── main.py              # Session start, validate, nudge, proof, routine/next, transcribe
│   │   ├── core/
│   │   │   ├── constants.py     # Valid phrases, typed keywords
│   │   │   ├── db.py           # SQLite wake_history
│   │   │   ├── personality.py  # Personality model, DEFAULT_PERSONALITY
│   │   │   └── session_store.py # In-memory sessions, phases
│   │   ├── models/
│   │   │   └── session.py      # Pydantic request/response models
│   │   └── services/
│   │       ├── message_builder.py # Phase messages, build_message(), LISTENING_MESSAGES
│   │       ├── stt.py          # Whisper transcribe_audio()
│   │       └── tts.py          # Coqui synthesize_tts()
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       ├── conftest.py         # Mocks TTS/DB, TestClient
│       └── test_api.py         # Session start, validate, nudge API tests
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
├── .github/
│   └── workflows/
│       └── ci.yml              # Backend pytest, frontend build
├── docs/
│   └── PROJECT.md              # Architecture, API reference
|
├── README.md
```

---

## 🎯 Design Principles

- Use native system reliability for scheduling.
- Separate triggering from enforcement.
- Replace motivation with state-based logic.
- Escalate interaction based on delay.
- Keep dependencies minimal and controllable.

SLOTH is an experiment in behavioral systems engineering — using automation and AI interaction to eliminate decision drift.

---

## ⚠️ Scope

SLOTH is built for personal use and experimentation. Voice synthesis and automation integrations are intended for private, non-commercial purposes.

---

**SLOTH doesn't ring. It enforces the transition from sleep to action.**
