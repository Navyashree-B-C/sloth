

# SLOTH

SLOTH is a **hybrid wake-up authority system** built to eliminate snoozing, avoidance, and morning drift.

It combines the **reliability of Android OS alarms** with a **personality-driven web app** that takes control the moment you wake up.

SLOTH does not rely on motivation.
It enforces consistency.

---

## 🧠 How SLOTH Works

### Layer 1 — Wake Trigger (Android OS)

* Uses the native Android alarm
* Works even when:

  * Bedtime mode is ON
  * Wi-Fi is OFF
  * Phone is locked

This layer’s only job is to **wake you up**.

---

### Layer 2 — Wake Authority (SLOTH App)

Once the alarm is dismissed:

* Tasker automation runs
* Wi-Fi is enabled
* SLOTH opens automatically
* Voice starts immediately

From this point, SLOTH is in control.

---

## 🔥 Core Capabilities

* Voice-based wake-up (not sounds)
* Personality-driven messaging (witty, sarcastic)
* Escalation if the user delays or fails
* Interaction lock (keywords required)

---

## 🧩 Tech Stack

### Frontend (Authority Interface)

* React + Vite
* Web Audio API
* Web Camera API
* PWA-style fullscreen experience
* Hosted on **Vercel**

### Backend (Brain)

* Python 3.11
* FastAPI
* Pydantic
* APScheduler (session logic)
* SQLite (upgradeable)
* Hosted on **Render**

### Voice

* Coqui XTTS (free, local, expressive)
* Tune: `SLOTH_TTS_SPEAKER` env var. 

### Android Automation (Tasker)

* **Trigger**: Event → Alarm dismissed (Clock app).
* **Task**:
  1. Wi-Fi → On (if needed).
  2. Launch App / Browser → open URL:  
     `https://your-sloth-url.vercel.app/?autostart=1&alarm_time=HH:mm`  
     (Replace with your deployed frontend URL and desired time, e.g. `07:30`.)
  3. Keep screen on: use Tasker’s “Stay On” or a custom scene that holds wake lock until SLOTH releases.

**Simulate on desktop**: Open  
`http://localhost:5173/?autostart=1&alarm_time=07:30`  
to start a session without an alarm. Add `&delay_sec=0` to skip the countdown.

---

## 📁 Repository Structure

```
sloth/
├── backend/
│   ├── app/
│   │   ├── main.py           # Session start, validate, nudge, proof, routine/next, transcribe
│   │   ├── core/             # constants, db, personality, session_store
│   │   ├── models/           # session.py (Pydantic)
│   │   └── services/         # message_builder, stt, tts
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.mts
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
├── docs/                     # PROJECT.md
|
└── README.md
```

---

## 🚀 Getting Started (Local)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# For male voice: brew install espeak-ng
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🖤 Design Philosophy

SLOTH is designed with one belief:

> Waking up is not a discipline problem — it’s a systems problem.

SLOTH builds a system that:

* Wakes you
* Keeps you awake
* Moves you forward

---

## ⚠️ Disclaimer

SLOTH is built for **personal use**.
Voice customization and automation are intended only for private, non-commercial use.

---

**SLOTH doesn’t ring. It insists.**
