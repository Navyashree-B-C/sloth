import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_API_BASE = "http://localhost:8001";
const AUDIO_PLAY_COOLDOWN_MS = 800;
/** Pause between main message and "say the word" prompt so they don't sound like one phrase. */
const MESSAGE_TO_PROMPT_PAUSE_MS = 700;
/** Delay before auto-starting mic when it's the user's turn (so prompt has sunk in). */
const AUTO_RECORD_DELAY_MS = 800;
/** Delay before first AWAKENING TTS (per workflow). Override with ?delay_sec=0 for testing. */
const AWAKENING_DELAY_MS = 30000;
let lastAudioPlayAt = 0;
let audioPlayInProgress = false;

const getApiBase = () => {
  const fromEnv = import.meta.env?.VITE_API_BASE;
  return (fromEnv && String(fromEnv)) || DEFAULT_API_BASE;
};

function App() {
  const apiBase = useMemo(getApiBase, []);

  const [sessionId, setSessionId] = useState(null);
  const [phase, setPhase] = useState(null);
  const [escalationLevel, setEscalationLevel] = useState(0);
  const [voiceText, setVoiceText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showKeywordInput, setShowKeywordInput] = useState(false);
  const [released, setReleased] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [spokenWord, setSpokenWord] = useState("");
  const [delaySeconds, setDelaySeconds] = useState(null);
  const [micError, setMicError] = useState(null);
  const [recordingWhisper, setRecordingWhisper] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakNow, setSpeakNow] = useState(false);
  const [proofCaptured, setProofCaptured] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [routineComplete, setRoutineComplete] = useState(false);
  /** True after backend said phrase was correct; show type step (yes/ok) only. */
  const [spokenVerified, setSpokenVerified] = useState(false);
  /** True after first tap; required by browser before fullscreen and audio.play(). */
  const [userHasGestured, setUserHasGestured] = useState(false);

  const autostartDone = useRef(false);
  /** When play() is blocked (no user gesture), store URLs to play on first tap. */
  const pendingAudioRef = useRef(null);
  const wakeLockRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const validatingRef = useRef(false);
  const validateAttemptRef = useRef(null);
  const keywordRef = useRef("");
  const spokenVerifiedRef = useRef(false);
  keywordRef.current = keyword;
  spokenVerifiedRef.current = spokenVerified;

  const handleStart = useCallback(async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setVoiceText("Getting up is non‑negotiable. Hold on.");

    try {
      const params = new URLSearchParams(window.location.search);
      const alarmTime = params.get("alarm_time") || null;

      const res = await fetch(`${apiBase}/session/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          alarm_time: alarmTime,
          user_name: null,
        }),
      });

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
      }

      const data = await res.json();

      setSessionId(data.session_id);
      setPhase(data.phase);
      setEscalationLevel(data.escalation_level);
      setVoiceText(data.text);

      const audioUrl = new URL(data.audio_url, apiBase).toString();
      const promptUrl = data.prompt_audio_url
        ? new URL(data.prompt_audio_url, apiBase).toString()
        : null;
      try {
        await playSequence(audioUrl, promptUrl);
      } catch (_playErr) {
        pendingAudioRef.current = { audioUrl, promptUrl };
      }
      setSpeakNow(true);
      setShowKeywordInput(true);
      setSpokenVerified(false);
    } catch (err) {
      console.error(err);
      setError(err.message || "Backend is not responding.");
      setVoiceText("Backend is not responding. You still have to get up.");
    } finally {
      setLoading(false);
    }
  }, [apiBase, loading]);

  const silentNextMessageTimeoutRef = useRef(null);

  const validateAttempt = useCallback(
    async (keywordVal, spokenVal, allowEmpty = false) => {
      const k = (keywordVal || "").trim();
      const s = (spokenVal || "").trim();
      if (!sessionId || validatingRef.current) return;
      if (!allowEmpty && !spokenVerified && !k && !s) return;
      if (!allowEmpty && spokenVerified && !k) return;
      validatingRef.current = true;
      if (silentNextMessageTimeoutRef.current) {
        clearTimeout(silentNextMessageTimeoutRef.current);
        silentNextMessageTimeoutRef.current = null;
      }
      setLoading(true);
      setError(null);

      const body = { session_id: sessionId, keyword: k || s };
      if (s && !spokenVerified) body.spoken = s;

      try {
        const res = await fetch(`${apiBase}/session/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          if (res.status === 404 && errData?.detail === "Session not found") {
            setSessionId(null);
            setShowKeywordInput(false);
            setReleased(false);
            setVoiceText("Session expired. Refresh SLOTH to start again.");
            setError("Session expired. Please restart.");
            setLoading(false);
            validatingRef.current = false;
            return;
          }
          throw new Error(errData.detail || `Backend error: ${res.status}`);
        }

        const data = await res.json();
        setPhase(data.phase);
        setEscalationLevel(data.escalation_level);
        setVoiceText(data.text);
        if (data.released) setReleased(true);
        setSpokenVerified(!!data.spoken_verified);

        const audioUrl = new URL(data.audio_url, apiBase).toString();
        const promptUrl = data.prompt_audio_url
          ? new URL(data.prompt_audio_url, apiBase).toString()
          : null;
        await playSequence(audioUrl, promptUrl, true);
        setSpeakNow(!data.released);
        if (
          !data.released &&
          (data.phase === "RESISTING" || data.phase === "ESCALATING")
        ) {
          const SILENT_NEXT_MS = 10000;
          silentNextMessageTimeoutRef.current = setTimeout(() => {
            silentNextMessageTimeoutRef.current = null;
            if (validateAttemptRef.current) validateAttemptRef.current("", "", true);
          }, SILENT_NEXT_MS);
        }
      } catch (err) {
        console.error(err);
        setError(err.message || "Validation failed.");
      } finally {
        setLoading(false);
        validatingRef.current = false;
      }
    },
    [apiBase, sessionId, spokenVerified]
  );
  validateAttemptRef.current = validateAttempt;

  const handleValidate = useCallback(
    (e) => {
      e?.preventDefault();
      const k = keyword.trim();
      const s = spokenWord.trim();
      if (!sessionId || loading) return;
      if (spokenVerified && !k) return;
      if (!spokenVerified && !k && !s) return;
      validateAttempt(spokenVerified ? k : (k || s), s);
    },
    [apiBase, sessionId, keyword, spokenWord, loading, spokenVerified, validateAttempt]
  );

  const RECORD_WHISPER_MS = 4000;

  const startRecordingWhisper = useCallback(async () => {
    setMicError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicError("Microphone not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      const chunks = [];
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = async () => {
        setRecordingWhisper(false);
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        if (chunks.length === 0) return;
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        setTranscribing(true);
        try {
          const formData = new FormData();
          formData.append("audio", blob, "audio.webm");
          const res = await fetch(`${apiBase}/session/transcribe`, {
            method: "POST",
            body: formData,
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            setMicError(err.detail || `Transcribe failed: ${res.status}`);
            return;
          }
          const data = await res.json();
          if (data.text) {
            const text = String(data.text).trim();
            if (text && validateAttemptRef.current) {
              setSpokenWord(text);
              const typed = (keywordRef.current || "").trim();
              if (spokenVerifiedRef.current) {
                if (typed) validateAttemptRef.current(typed, text);
              } else {
                validateAttemptRef.current(typed || text, text);
              }
            }
          }
        } catch (err) {
          setMicError(err.message || "Transcribe failed.");
        } finally {
          setTranscribing(false);
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecordingWhisper(true);
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
          mediaRecorderRef.current = null;
        }
      }, RECORD_WHISPER_MS);
    } catch (err) {
      setMicError(err.message || "Microphone access denied. Use HTTPS or localhost.");
    }
  }, [apiBase]);

  const stopRecordingWhisper = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setRecordingWhisper(false);
  }, []);

  // Auto-start recording only in step 1 (say phrase); not when spokenVerified (type step).
  useEffect(() => {
    if (!speakNow || !showKeywordInput || released || spokenVerified || recordingWhisper || transcribing || loading) return;
    const t = setTimeout(() => {
      startRecordingWhisper();
    }, AUTO_RECORD_DELAY_MS);
    return () => clearTimeout(t);
  }, [speakNow, showKeywordInput, released, spokenVerified, recordingWhisper, transcribing, loading, startRecordingWhisper]);

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      setError("Camera access denied or unavailable.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => {
    if (showCamera && !proofCaptured) startCamera();
    return () => stopCamera();
  }, [showCamera, proofCaptured, startCamera, stopCamera]);

  const handleRoutineNext = useCallback(async () => {
    if (!sessionId || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/session/routine/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Routine next failed.");
      const data = await res.json();
      setVoiceText(data.text);
      setRoutineComplete(data.routine_complete);
      const audioUrl = new URL(data.audio_url, apiBase).toString();
      const promptUrl = data.prompt_audio_url
        ? new URL(data.prompt_audio_url, apiBase).toString()
        : null;
      await playSequence(audioUrl, promptUrl);
      setSpeakNow(true);
    } catch (err) {
      setError(err.message || "Routine failed.");
    } finally {
      setLoading(false);
    }
  }, [apiBase, sessionId, loading]);

  const captureProof = useCallback(async () => {
    if (!sessionId || !videoRef.current?.srcObject) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    try {
      const res = await fetch(`${apiBase}/session/proof`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error("Proof submit failed.");
      setProofCaptured(true);
      setShowCamera(false);
      setError(null);
      stopCamera();
    } catch (err) {
      setError(err.message || "Proof failed.");
    }
  }, [apiBase, sessionId, stopCamera]);

  const handleNudge = useCallback(
    async () => {
      if (!sessionId || loading || released || phase !== "AWAKENING") return;

      try {
        const res = await fetch(`${apiBase}/session/nudge`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));

          // If the session vanished or AWAKENING is over, just stop nudging silently.
          if (
            (res.status === 404 && errData?.detail === "Session not found") ||
            (res.status === 400 && errData?.detail === "Nudges are only allowed in AWAKENING phase")
          ) {
            return;
          }

          throw new Error(errData.detail || `Backend error: ${res.status}`);
        }

        const data = await res.json();
        setPhase(data.phase);
        setEscalationLevel(data.escalation_level);
        setVoiceText(data.text);

        const audioUrl = new URL(data.audio_url, apiBase).toString();
        const promptUrl = data.prompt_audio_url
          ? new URL(data.prompt_audio_url, apiBase).toString()
          : null;
        await playSequence(audioUrl, promptUrl);
        setSpeakNow(true);
      } catch (err) {
        console.error(err);
        setError(err.message || "Nudge failed.");
      }
    },
    [apiBase, sessionId, loading, released, phase]
  );

  // While still in AWAKENING and user is idle, repeat AWAKENING lines.
  useEffect(() => {
    if (!sessionId || phase !== "AWAKENING" || released) return;

    const timeoutId = setTimeout(() => {
      handleNudge();
    }, 20000); // 20s idle before another AWAKENING line

    return () => clearTimeout(timeoutId);
  }, [sessionId, phase, released, handleNudge, voiceText]);

  // When opened from alarm (Tasker) with ?autostart=1, wait delay then start session (per workflow: 30s before AWAKENING).
  useEffect(() => {
    if (autostartDone.current) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("autostart") !== "1") return;
    autostartDone.current = true;
    const delaySec = parseInt(params.get("delay_sec") ?? "", 10);
    const totalSec = Number.isFinite(delaySec) && delaySec >= 0 ? delaySec : AWAKENING_DELAY_MS / 1000;
    if (totalSec <= 0) {
      handleStart();
      return;
    }
    setDelaySeconds(totalSec);
  }, [handleStart]);

  // Countdown during autostart delay; when 0, start session.
  useEffect(() => {
    if (delaySeconds === null || delaySeconds <= 0) return;
    const t = setTimeout(() => {
      const next = delaySeconds - 1;
      setDelaySeconds(next);
      if (next <= 0) {
        setDelaySeconds(null);
        handleStart();
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [delaySeconds, handleStart]);

  // Fullscreen only after user gesture (browser requirement).
  useEffect(() => {
    if (!sessionId || released || !userHasGestured) return;
    const doc = document.documentElement;
    if (doc.requestFullscreen) {
      doc.requestFullscreen().catch(() => {});
    }
    return () => {
      if (document.fullscreenElement === doc && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, [sessionId, released, userHasGestured]);

  // Screen wake lock: keep screen on while session is active until release.
  useEffect(() => {
    if (!sessionId || released) return;
    if ("wakeLock" in navigator) {
      navigator.wakeLock.request("screen").then((lock) => {
        wakeLockRef.current = lock;
      }).catch(() => {});
    }
    return () => {
      if (wakeLockRef.current) {
        wakeLockRef.current.release();
        wakeLockRef.current = null;
      }
    };
  }, [sessionId, released]);

  // Navigation guard: warn on close/refresh when session active and not released.
  useEffect(() => {
    const handler = (e) => {
      if (sessionId && !released) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [sessionId, released]);

  // First tap unlocks fullscreen and plays any pending audio (browser requires user gesture).
  const handleFirstTap = useCallback(
    (e) => {
      if (userHasGestured || !sessionId || released) return;
      e.preventDefault();
      e.stopPropagation();
      setUserHasGestured(true);
      const doc = document.documentElement;
      if (doc.requestFullscreen) doc.requestFullscreen().catch(() => {});
      const pending = pendingAudioRef.current;
      if (pending) {
        pendingAudioRef.current = null;
        playSequence(pending.audioUrl, pending.promptUrl).catch(() => {});
      }
    },
    [sessionId, released, userHasGestured]
  );

  return (
    <main className="app" onClick={handleFirstTap}>
      <section className="screen screen--center">
        <h1>SLOTH 🖤</h1>
        <p className="voice-text">
          {delaySeconds !== null ? `Wake up in ${delaySeconds} s…` : voiceText}
        </p>

        {released ? (
          <div className="release-wrap">
            <p className="release-message">Session complete. You&apos;re done.</p>
          </div>
        ) : showKeywordInput ? (
          <form onSubmit={handleValidate} className="keyword-form">
            {speakNow && !spokenVerified && <p className="speak-now">Your turn. Say the phrase.</p>}
            {speakNow && spokenVerified && <p className="speak-now">Now type yes or ok.</p>}
            <p className="keyword-hint">
              {spokenVerified ? "Type &quot;yes&quot; or &quot;ok&quot;." : "Say: I&apos;m awake or I&apos;m up."}
            </p>
            {!spokenVerified && (recordingWhisper || transcribing) && (
              <div className="listening-indicator" aria-live="polite">
                <div className="listening-mic-wrap">
                  <span className="listening-icon" aria-hidden="true">🎤</span>
                  <span className="listening-ring" aria-hidden="true" />
                  <span className="listening-ring listening-ring--2" aria-hidden="true" />
                  <span className="listening-ring listening-ring--3" aria-hidden="true" />
                </div>
                <p className="listening-label">
                  {recordingWhisper ? "Listening…" : "Transcribing…"}
                </p>
              </div>
            )}
            <div className="keyword-row">
              <input
                type="text"
                className="keyword-input"
                placeholder={spokenVerified ? "yes or ok" : "Type after you say the phrase"}
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                disabled={loading}
                autoFocus={spokenVerified}
                autoComplete="off"
              />
            </div>
            {spokenWord ? <p className="spoken-capture">&quot;{spokenWord}&quot;</p> : null}
            {micError ? <p className="error-text">{micError}</p> : null}
            <button
              type="submit"
              className="primary-btn"
              disabled={loading || (spokenVerified ? !keyword.trim() : !keyword.trim() && !spokenWord.trim())}
            >
              {loading ? "Checking..." : "Submit"}
            </button>
          </form>
        ) : null}

        {error && <p className="error-text">{error}</p>}
      </section>
    </main>
  );
}

/** Play main clip, pause, then prompt clip; resolves when done. Skips prompt if same URL. forcePlay: play even if another clip was in progress (e.g. validate response). */
async function playSequence(audioUrl, promptUrl, forcePlay = false) {
  if (!forcePlay && audioPlayInProgress) return;
  audioPlayInProgress = true;
  try {
    await playAudioWithCooldown(audioUrl);
    if (promptUrl && promptUrl !== audioUrl) {
      await new Promise((r) => setTimeout(r, MESSAGE_TO_PROMPT_PAUSE_MS));
      await playAudioWithCooldown(promptUrl);
    }
  } finally {
    audioPlayInProgress = false;
  }
}

/** Play TTS from URL with cooldown; resolves when playback ends (not when play() starts). */
async function playAudioWithCooldown(src) {
  const now = Date.now();
  const elapsed = now - lastAudioPlayAt;
  if (elapsed < AUDIO_PLAY_COOLDOWN_MS) {
    await new Promise((r) => setTimeout(r, AUDIO_PLAY_COOLDOWN_MS - elapsed));
  }

  const audio = new Audio(src);
  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = () => {
      audio.removeEventListener("canplaythrough", onCanPlay);
      audio.removeEventListener("error", onError);
      audio.removeEventListener("ended", onEnded);
    };
    const onCanPlay = () => {
      if (settled) return;
      lastAudioPlayAt = Date.now();
      audio.play().catch((err) => {
        if (!settled) {
          settled = true;
          cleanup();
          reject(err);
        }
      });
    };
    const onError = () => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error("Audio failed to load"));
    };
    const onEnded = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };
    audio.addEventListener("canplaythrough", onCanPlay, { once: true });
    audio.addEventListener("error", onError, { once: true });
    audio.addEventListener("ended", onEnded, { once: true });
    audio.load();
    setTimeout(() => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error("Audio load timeout"));
    }, 15000);
  });
}

export default App;

