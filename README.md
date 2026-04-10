# 🔥 SLOTH — Wake Enforcement System

SLOTH is a wake-enforcement system designed to eliminate snoozing and post-alarm drift through **forced interaction and cognitive compliance**.

No passive reminders.
No reliance on motivation.
No easy exits.

You wake up because the system **doesn’t let you stay asleep.**

---

## 🎬 Demo

👉 https://youtu.be/gocuX0dU9Qo

---

## 🧠 The Problem

Traditional alarms fail at the only moment that matters—

**the seconds after dismissal.**

That’s where people:

* go back to bed
* open their phone
* lose momentum

Waking up isn’t about discipline.

It’s about control over that vulnerable window.

SLOTH takes control.

---

## ⚙️ How It Works

1. Wake time hits
2. Android automation launches SLOTH
3. User enables audio (browser requirement)
4. Voice interaction begins instantly
5. User must:

   * Speak a valid wake phrase
   * Type a confirmation keyword

Until both are completed, **the session does not release control.**

---

## 🔥 Core Capabilities

* Voice-driven enforcement
* Dual-layer confirmation (speech + typed input)
* Escalation logic on delay/failure
* Personality-based interaction
* Deterministic session control
* Lightweight fullscreen PWA

---

## 🌐 Live App

👉 https://sloth.vercel.app

---

## 🧩 Architecture Overview

```
                ┌──────────────────────────────┐
                │     ANDROID AUTOMATION       │
                │ (MacroDroid / Automate)      │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │        FRONTEND (React)      │
                │  - UI / Fullscreen PWA       │
                │  - Audio Control             │
                │  - Input Handling            │
                └──────────────┬───────────────┘
                               │ API Calls
                               ▼
                ┌──────────────────────────────┐
                │       BACKEND (FastAPI)      │
                │  - Session Management        │
                │  - Validation Logic          │
                │  - Escalation Engine         │
                └───────┬───────────┬──────────┘
                        │           │
                        ▼           ▼
          ┌──────────────────┐   ┌──────────────────┐
          │   STT (Whisper)  │   │   TTS (Coqui)    │
          │ Speech → Text    │   │ Text → Voice     │
          └──────────────────┘   └──────────────────┘
                        │
                        ▼
                ┌──────────────────────────────┐
                │        USER RESPONSE         │
                │ (Speech + Typed Confirmation)│
                └──────────────────────────────┘
```

---

## 🏗 Architecture Breakdown

### 1️⃣ Trigger Layer (Automation)

* External tools trigger system reliably
* Decouples scheduling from logic
* Ensures deterministic start

### 2️⃣ Enforcement Layer (Web System)

* Frontend locks user into interaction
* Backend validates compliance
* Voice system escalates prompts
* Session persists until completion

---

## 🛠 Tech Stack

### Frontend

* React
* Vite
* Web Audio API
* PWA fullscreen mode

### Backend

* Python 3.11
* FastAPI
* Pydantic
* SQLite

### Voice

* Whisper (Speech-to-Text)
* Coqui XTTS (Text-to-Speech)

---

## 🤖 Android Automation Setup

### Time Trigger

```
https://sloth.vercel.app/?autostart=1&alarm_time=HH:mm
```

### Wake Window (Recommended)

```
https://sloth.vercel.app/?autostart=1&delay_sec=0
```

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

Test:

```
http://localhost:5173/?autostart=1&alarm_time=07:30&delay_sec=0
```

---

## 🎯 Design Philosophy

* Remove dependency on motivation
* Enforce behavioral transition
* Use system reliability for triggers
* Keep logic deterministic
* Minimize bypass paths

---

## ⚠️ Scope

Built for personal use and experimentation.
Voice + automation integrations are non-commercial.

---

## ⚠️ Third-Party Licenses

This project uses open-source components such as Whisper and Coqui XTTS.
Please refer to their respective licenses for usage terms.

---

## 📄 License

This project is licensed under **All Rights Reserved**.

You may not copy, modify, distribute, or use this software without explicit permission from the author.

---

## 🧠 Final Note

Most systems ask you to wake up.

SLOTH makes sure you **don’t have a choice.**
