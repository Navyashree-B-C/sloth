# SLOTH 🖤

*A hybrid wake-up authority system that doesn’t let you escape.*

SLOTH is not an alarm app. It is a **behavior-control system** that uses the OS alarm to wake you, then takes over with voice, personality, escalation, and an interaction lock. Discipline does not rely on motivation.

---

## System Architecture

| Layer | Responsibility |
|-------|----------------|
| **1 – Wake trigger (OS)** | Android native alarm. Works with Bedtime ON, Wi‑Fi OFF. Guaranteed wake. |
| **2 – Wake authority (SLOTH)** | App opens after alarm dismiss. Voice starts, screen stays on. Release only after keyword compliance. |

---

## Tech Stack

| Area | Choice |
|------|--------|
| **Frontend** | React + Vite, PWA (manifest, fullscreen, Wake Lock). Hosted on Vercel. |
| **Backend** | Python 3.11, FastAPI, Pydantic. In-memory session store; SQLite wake history. |
| **Voice** | Coqui TTS; optional STT via Whisper (`openai-whisper`). |
| **Android** | Tasker: alarm dismissed → open SLOTH URL (`?autostart=1&alarm_time=HH:mm`), Wi‑Fi on, keep screen on. |

---

## Repository Structure (as in codebase)

```
Sloth/
├── backend/app/
│   ├── main.py              # Session start, validate, nudge, proof, routine/next, transcribe
│   ├── core/                # constants, db, personality, session_store
│   ├── models/              # session.py (Pydantic)
│   └── services/            # message_builder, stt, tts
├── frontend/src/            # App.jsx, main.jsx, styles.css
├── docs/PROJECT.md          # Full flow and API reference
└── vercel.json
```

---

## Definition of Ready

- User Story follows template: **As a \<user\> I want \<feature\> So that \<benefit\>**.
- Acceptance criteria are defined and agreed.
- No implementation starts without acceptance criteria.

## Definition of Done

- Acceptance criterion is implemented and verifiable.
- Implementation is documented (file/behavior) in this backlog.
- Code adheres to project rules (see `.cursor/rules`).

---

## Agile Backlog

*Status reflects current codebase. Camera proof and morning routine are disabled; focus is wake-up flow.*

---

### EPIC 1 – Hybrid Wake Trigger

**User Story**

> As a **heavy sleeper**  
> I want **my OS alarm to wake me and immediately open SLOTH with context**  
> So that **I cannot drift back to sleep after dismissal**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Web autostart: opening with `?autostart=1&alarm_time=HH:mm` starts a wake session and passes `alarm_time` to `POST /session/start`. | ✅ Done | Frontend `App.jsx`: parse query, call `handleStart()` on mount when `autostart=1`. |
| AC2 | Android alarm → SLOTH handoff: Tasker/Android connects alarm dismissal to opening the SLOTH URL with `autostart=1`. | ✅ Doc | README: Tasker profile (alarm dismissed → open URL). No in-repo Tasker export. |
| AC3 | Screen-on until release: when launched from alarm, SLOTH keeps the screen awake until the session is released. | ✅ Done | Wake Lock API + fullscreen when session active; PWA meta in `index.html`, `manifest.webmanifest`. |

---

### EPIC 2 – Wake Session Authority

**User Story**

> As a **user who just dismissed my alarm**  
> I want **SLOTH to take control immediately with voice**  
> So that **I can’t quietly ignore the wake‑up**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Session start API: `POST /session/start` creates a session in AWAKENING and returns `session_id`, `phase`, `text`, `audio_url`. | ✅ Done | `backend/app/main.py`: `start_session`, `create_session`, `build_message`, `synthesize_tts`. |
| AC2 | Immediate audio: frontend loads and plays `audio_url` automatically after `/session/start` succeeds. | ✅ Done | `App.jsx`: `playAudioWithCooldown(audioUrl)` after start; cooldown 800 ms. |
| AC3 | Visible loading/error state while waiting for backend/TTS; failures show a clear error and fallback. | ✅ Done | `App.jsx`: `loading`, `error`, fallback copy. |
| AC4 | Escape prevention: fullscreen, navigation guards, and screen-on until release. | ✅ Done | Fullscreen on session active, `beforeunload` guard, Wake Lock in `App.jsx`. |

---

### EPIC 3 – Personality Engine

**User Story**

> As a **user**  
> I want **SLOTH to talk with a consistent, intense personality across phases**  
> So that **wake‑ups feel human and engaging instead of robotic**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Phase buckets: phases AWAKENING, RESISTING, ESCALATING, COMPLIANT, ROUTINE_ACTIVE, RELEASE with short punchy lines per phase. | ✅ Done | `message_builder.py`: `PHASE_MESSAGES` dict. |
| AC2 | Deterministic builder: `build_message(phase, escalationLevel, context, personality)` returns `template_id` and `text`. | ✅ Done | `message_builder.py`: `build_message()`. |
| AC3 | Personality model: `Personality` dataclass with `id`, `tone`, `intensity_curve`, `swear_allowance` and `DEFAULT_PERSONALITY`. | ✅ Done | `core/personality.py`. |
| AC4 | Unified voice path: all session endpoints build messages via personality engine and synthesize audio via TTS. | ✅ Done | `main.py`, `tts.py`: all responses use `build_message` + `synthesize_tts`. |
| AC5 | Rich context: messages incorporate time, failures, streaks, and user name in a structured way. | ⬜ Backlog | — |
| AC6 | Behavior-based tuning: personality tone/intensity adapts to past behavior. | ⬜ Backlog | — |

---

### EPIC 4 – Interaction Lock (Keyword Gate)

**User Story**

> As a **user**  
> I want **the alarm to stop only after I give the correct keyword**  
> So that **I must consciously comply before getting relief**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Validate API: `POST /session/validate` accepts `session_id`, `keyword`, optional `spoken`; returns `valid`, `phase`, `text`, `audio_url`, `released`. | ✅ Done | `main.py`: `validate_session`; `SessionValidateRequest` has `spoken` optional. |
| AC2 | Keyword rules: a small set of accepted keywords checked case-insensitively (e.g. awake, up, yes, ok, okay). | ✅ Done | `core/constants.py`: `VALID_KEYWORDS`, `SPOKEN_KEYWORDS`, `TYPED_KEYWORDS`; `_is_keyword_valid()`. |
| AC3 | Retry and escalation: wrong keyword increases escalation level and moves between RESISTING and ESCALATING. | ✅ Done | `main.py`: bump level, probabilistic phase choice. |
| AC4 | Frontend keyword loop: after first message, keyword input appears; submit → validate → play next message; repeat until RELEASE. | ✅ Done | `App.jsx`: `handleValidate`, play main + prompt, loop until `released`. |
| AC5 | Idle AWAKENING nudges: while in AWAKENING with no input, system periodically plays new AWAKENING lines via `POST /session/nudge`. | ✅ Done | Frontend 20 s idle timer; `main.py`: `nudge_session`. |
| AC6 | Spoken keyword (STT): users can speak the keyword (mic + STT) in addition to typing. | ✅ Done | Web Speech API (mic button) + Whisper (`POST /session/transcribe`); frontend sends `spoken` when set. |

---

### EPIC 5 – Proof of Action (Camera) — Disabled

**User Story**

> As a **user**  
> I want **to prove I’m physically awake using my camera**  
> So that **SLOTH doesn’t release me while I’m still in bed**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Camera permission and capture: frontend requests camera and captures one or more proof frames. | ⬜ Disabled | Backend has `POST /session/proof` and `proof_captured`; frontend has camera UI but flow does not require proof. |
| AC2 | Proof validation before release: success criteria applied before release. | ⬜ Disabled | Validate no longer requires proof; direct COMPLIANT → RELEASE. |
| AC3 | Escalation on failure or refusal to capture. | ⬜ Backlog | — |

---

### EPIC 6 – Morning Routine — Disabled

**User Story**

> As a **user**  
> I want **SLOTH to guide me through a short morning routine after waking**  
> So that **I keep moving and don’t slide back into bed**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | ROUTINE_ACTIVE flow after COMPLIANT: session can enter ROUTINE_ACTIVE with a defined sequence of steps. | ⬜ Disabled | Backend supports ROUTINE_ACTIVE and `POST /session/routine/next`; validate skips routine and goes COMPLIANT → RELEASE. |
| AC2 | Step-by-step guidance: each step announced by voice and mirrored in UI with next/done. | ⬜ Disabled | — |
| AC3 | Release only after all required steps completed. | ⬜ Disabled | — |

---

### EPIC 7 – Memory & Adaptation

**User Story**

> As a **user**  
> I want **SLOTH to learn how I behave over time**  
> So that **it escalates smartly without lots of manual settings**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Persistent wake history: wake attempts, success/failure, and timing stored beyond a single session. | ✅ Done | `core/db.py`: SQLite `wake_history`; `record_session_start`, `record_session_end` in `main.py`. |
| AC2 | Per-session metrics: each session tracks failed attempts and idle nudges. | ✅ Done | `session_store.py`: `SessionState.failed_attempts`, `nudge_count`. |
| AC3 | Adaptive escalation: thresholds and script choices adjust from history. | ⬜ Backlog | — |
| AC4 | User preferences: name, keywords, alarm profiles persisted and used in context. | ⬜ Backlog | — |

---

### EPIC 8 – Web Authority Interface

**User Story**

> As a **user testing on desktop or Android browser**  
> I want **a web interface that mirrors the wake-up authority flow**  
> So that **I can run the core loop without a native app**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | React/Vite shell: `frontend/` Vite app with App, index.html, API base via `VITE_API_BASE`. | ✅ Done | `frontend/`: `App.jsx`, `main.jsx`, `vite.config.mts`. |
| AC2 | Session wiring: start and validate (and nudge) flows wired to backend. | ✅ Done | `App.jsx`: `handleStart`, `handleValidate`, `handleNudge`. |
| AC3 | Autostart from query: `autostart=1&alarm_time=HH:mm` triggers automatic session start. | ✅ Done | `App.jsx`: useEffect with `autostart=1`, optional `delay_sec`. |
| AC4 | Mobile-first layout: responsive UI with loading/error states and keyword input. | ✅ Done | `styles.css`, `App.jsx`. |
| AC5 | PWA and screen-on: manifest, fullscreen, Wake Lock, add-to-home hints. | ✅ Done | `manifest.webmanifest`, `index.html` meta, Wake Lock in `App.jsx`. |

---

### EPIC 9 – Workflow Completion (per SLOTH_WORKFLOW)

**User Story**

> As a **user**  
> I want **SLOTH to match the designed workflow (delay, spoken keyword, dual say/type, closing moment)**  
> So that **the wake-up flow is cognitively engaging and clearly complete**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | 30 s delay before first AWAKENING: wait then start session and play TTS. | ✅ Done | Frontend: countdown when `autostart=1`; `?delay_sec=0` to skip. |
| AC2 | STT (spoken keyword): mic/Web Speech or backend Whisper; transcript used as `spoken` in validate. | ✅ Done | Mic button (Web Speech API); Record Whisper → `POST /session/transcribe` → set `spokenWord`; validate sends `spoken`. |
| AC3 | Dual keyword (say X, type Y): two distinct phrases; both required when spoken is provided. | ✅ Done | `constants.py`: SPOKEN_KEYWORDS, TYPED_KEYWORDS; `_is_keyword_valid(keyword, spoken)`. |
| AC4 | Closing-session animation on RELEASE. | ✅ Done | `.release-wrap` CSS animation (fade + scale) in `styles.css`; used when `released`. |

---

### EPIC 10 – Backend STT & Conversational Turn Flow

**User Story**

> As a **user**  
> I want **to speak my keyword to the backend (Whisper) and get a turn-by-turn flow where SLOTH asks me to say the word and signals “I’m listening”**  
> So that **it feels like a conversation and works consistently across browsers**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | Listening prompt (in-character): dedicated “Say the word. I’m listening.” lines before user’s turn. | ✅ Done | `message_builder.py`: `LISTENING_MESSAGES`, `build_listening_prompt()`; start/validate/nudge return `prompt_text`, `prompt_audio_url`; frontend plays main then prompt. |
| AC2 | Backend STT (Whisper): endpoint accepts audio and returns transcript. | ✅ Done | `POST /session/transcribe`; `services/stt.py`: `transcribe_audio()` with `openai-whisper`. |
| AC3 | Wire transcript into validate: frontend sends audio → transcribe → passes `spoken` to validate. | ✅ Done | Frontend: Record (Whisper) → upload → set `spokenWord`; validate body includes `spoken`. |
| AC4 | Speaking turn after every TTS: after main + listening prompt, user can speak (mic or Whisper). | ✅ Done | Frontend plays main + prompt then shows “Your turn. Speak now.” and keyword input + mic/Whisper buttons. |
| AC5 | Turn UX: clear “Your turn” / “Speak now” state and visual. | ✅ Done | `speakNow` state; `.speak-now` class; “Your turn. Speak now.” when `speakNow`. |

---

### EPIC 11 – CI/CD & Deployment

**User Story**

> As a **developer**  
> I want **automated tests and builds on every push, and frontend/backend deployed from the repo**  
> So that **releases are reliable and I don’t deploy broken code**.

**Acceptance Criteria**

| ID | Criterion | Status | Implementation |
|----|-----------|--------|----------------|
| AC1 | CI runs on push/PR: one workflow runs backend tests and frontend build in parallel. | ✅ Done | `.github/workflows/ci.yml`: jobs `backend` (Python, pytest) and `frontend` (Node, npm ci + build). |
| AC2 | Backend CI: install `backend/requirements.txt`, run pytest for `backend/tests` with mocked TTS/DB. | ✅ Done | `ci.yml` backend job: `pip install -r backend/requirements.txt`, `pytest backend/tests` (from repo root with `PYTHONPATH=backend`). |
| AC3 | Frontend CI: install deps and build; no deploy in CI. | ✅ Done | `ci.yml` frontend job: `cd frontend && npm ci && npm run build`. |
| AC4 | Frontend deploy: Vercel connected to repo; deploys from `main`; optional: require CI status before deploy. | ⬜ Doc | Connect repo in Vercel; root or `frontend` per `vercel.json`; set `VITE_API_BASE` to Render backend URL. |
| AC5 | Backend deploy: Render Web Service; root `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. | ⬜ Doc | Create Web Service in Render, link repo, set root directory and start command. |
| AC6 | Frontend points at backend: production frontend uses backend URL via env (e.g. `VITE_API_BASE`). | ⬜ Doc | In Vercel project env set `VITE_API_BASE` to `https://<service>.onrender.com`. |

**Tasks**

| Task | Description | Status |
|------|-------------|--------|
| T1 | Add GitHub Actions workflow for CI (backend + frontend jobs). | ✅ Done |
| T2 | Document Vercel project setup (root/build, env, branch). | ⬜ Backlog |
| T3 | Document Render Web Service setup (root, build, start, env). | ⬜ Backlog |

---

## Backlog (Future Work)

| Area | Items |
|------|--------|
| EPIC 3 | Rich context in messages; behavior-based tuning. |
| EPIC 5 | Re-enable camera proof and gate release on proof. |
| EPIC 6 | Re-enable ROUTINE_ACTIVE and step-by-step routine before release. |
| EPIC 7 | Adaptive escalation from history; user preferences (name, keywords, profiles). |
| EPIC 11 | Vercel/Render deploy docs (T2, T3); optional branch protection with CI status. |
| Optional | Tasker export in repo; fuzzy keyword match; auto-start mic after prompt. |

---

## Current Flow Summary (Wake-Up Only)

1. Alarm dismiss → open URL `?autostart=1&alarm_time=HH:mm` (optional `&delay_sec=0`).
2. Optional 30 s countdown → `POST /session/start` → AWAKENING message + listening prompt → “Your turn. Speak now.”
3. Idle 20 s → `POST /session/nudge` → repeat AWAKENING + prompt.
4. User says (mic or Whisper) + types keyword → `POST /session/validate` → COMPLIANT message + prompt.
5. User says + types again → `POST /session/validate` → RELEASE → “Session complete. You’re done.” → closing animation.

Full flow and API reference: **`docs/PROJECT.md`**.

---

*SLOTH doesn’t ring. It insists.*
