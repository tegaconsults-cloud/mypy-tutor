# Voice Feature Investigation — MyPy Tutor Backend

**Scope:** Read-only investigation of why the voice feature (`POST /voice/chat` speech-to-text + `POST /tts/speak` text-to-speech) is not working. No code was modified.

**Bottom line up front:** The Gemini TTS path (`/tts/speak`) is implemented correctly and matches Google's official REST API exactly. The Gemini STT path (`/voice/chat`) is also structurally correct, with two real code defects: (1) the system prompt is built with the wrong argument order, and (2) the audio MIME type sent to Gemini carries a codec suffix that Gemini is not documented to accept. Neither of those alone would make the feature "completely broken" — which strongly suggests the actual live failure is a **configuration problem: `GEMINI_API_KEY` is not set in the Render dashboard**, since every voice call depends on it and it is declared `sync: false` (manual entry) in `render.yaml`. Verify that first.

---

## BACKEND /voice/chat — findings

Handler: `app/main.py` `voice_chat()` at line 8143 (`@app.post("/voice/chat")`). It runs three stages: STT → chat LLM → TTS.

**Auth**
- Requires a signed-in user: `user=Depends(get_current_user)`; returns `401 "Sign in to use voice chat."` when absent (line ~8159). The token is an **itsdangerous `URLSafeTimedSerializer`** session token (`app/auth.py` `create_session_token` / `verify_session_token`), read from the `Authorization: Bearer <token>` header. It is **not** a JWT. This matters for the frontend (see frontend section).

**Stage 1 — Transcription (`_gemini_stt`, app/main.py line ~8024)**
- HTTP method/URL: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}` (lines 8032–8035). `?key=` query-param auth is the correct Gemini REST auth scheme (not a Bearer token).
- Model: `gemini-2.0-flash`. This is a valid, currently-available model in the v1beta API and supports audio/multimodal `inlineData` input. Correct.
- Audio transport: base64 `inlineData` with `mimeType` + `data`, plus a text instruction part (lines 8036–8047). This is the correct multimodal request shape.
- **MIME type is passed through verbatim from the client** (line 8040): `"mimeType": mime_type`. The frontend sends `audio/webm;codecs=opus` on Chrome (see frontend section). Google's audio-understanding docs list `audio/webm` as supported, but **not** the `;codecs=opus` parameterized form. A codec-suffixed MIME type is a known rejection trigger for the `inlineData` mimeType. This is a real risk that would surface as `Gemini STT HTTP 400: ...`.
- Transcript extraction: `data["candidates"][0]["content"]["parts"][0]["text"]` (lines 8058–8060), returning `""` on `KeyError`/`IndexError`. Correct path for a text response.
- Timeout: `httpx.post(..., timeout=10)` (line 8054). 10s is adequate for short clips.
- `GEMINI_API_KEY` read via `_os.getenv("GEMINI_API_KEY", "")`; raises `RuntimeError("GEMINI_API_KEY not set")` if empty (lines 8026–8029). The caller maps this to `HTTP 503 "Gemini not configured."` (line 8190). All other STT errors map to `502 "Transcription failed/error"` (lines 8191–8193). Empty transcript → `422 "Could not transcribe audio..."` (lines 8196–8197).

**Stage 2 — Chat LLM (lines 8199–8210)**
- Calls `get_completion(system_prompt=system, messages=[{"role":"user","content":transcript}], intent="concept", temperature=0.7)`. The `get_completion` cascade (Groq → Gemini → OpenRouter) is the same one used by `/chat`, so this stage is robust. Failures are caught and replaced with a canned apology string rather than a hard error.
- **BUG — wrong argument order for the system prompt.** Line 8202: `system = build_system_prompt(level, learner_id)`. The actual signature (`app/prompts.py` line 347) is `build_system_prompt(intent, topic=None, level="beginner", is_gap_topic=False)`. So `intent` receives the level string (e.g. `"beginner"`) and `topic` receives the learner_id (e.g. `"usr_abc123"`). It does not crash — `prompts.get(intent, _GENERAL_PROMPT)` falls back to the general prompt, and a bogus `**{learner_id}**` topic line is appended — but Sir. Tega's spoken replies are degraded and oddly contextualised. The caller already knows the real intent (`"concept"`, passed to `get_completion`); it should be passed to `build_system_prompt` instead.

**Stage 3 — TTS (lines 8211–8226)**
- Markdown is stripped, the reply is capped to 3000 chars, then `_gemini_tts(tts_text, voice=voice)` is called. On failure `audio_out = ""` and the endpoint still returns 200 with the text reply, so the frontend can fall back to browser TTS. This graceful degradation is correct.

**Cross-cutting backend concerns**
- `httpx.post` (the **synchronous** top-level call) is used inside `async def` handlers for both `_gemini_stt` and `_gemini_tts`. This blocks the single uvicorn event-loop worker for the full duration of each Gemini call (up to 10s, and `/voice/chat` makes two such calls in sequence). On Render's free tier (`workers: 1`) this can stall all other requests and contribute to health-check timeouts under load. Not the sole root cause, but a real robustness defect.
- CORS: the frontend origin `https://mypytutor.com.ng` is in `_allowed_origins` and the `allow_origin_regex` covers it; `Content-Type` and `Authorization` are in `allow_headers`. No CORS obstruction for these POSTs.
- `app/llm_client.py` module docstring says "Voice/TTS does NOT call this — it uses the browser Web Speech API." This is **stale/wrong** — the voice routes call `get_completion` (chat stage) and call Gemini REST directly for STT/TTS. Misleading only; no functional impact.

---

## BACKEND /tts/speak — findings

Handler: `app/main.py` `tts_speak()` at line 8094 (`@app.post("/tts/speak")`). Helper `_gemini_tts()` at line ~7970.

- HTTP method/URL: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}` (lines 7983–7987). `?key=` auth, correct.
- Model: `gemini-2.5-flash-preview-tts`. **Confirmed valid** against Google's model docs (`ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-preview-tts`). This is the current single-speaker Gemini TTS model. Correct.
- Request body (lines 7988–7998): `generationConfig.responseModalities=["AUDIO"]` + `speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName=voice`. **This matches Google's documented TTS REST request shape exactly** (verified against Google's speech-generation reference and third-party examples using the identical `prebuiltVoiceConfig`/`voiceName` structure).
- Voice: defaults to `"Aoede"`; frontend offers `Aoede, Kore, Charon, Puck, Fenrir, Leda, Orus, Zephyr`. These are the eight documented Gemini prebuilt voices. Correct.
- Response parsing (lines 8003–8015): reads `candidates[0].content.parts[0].inlineData.data` (base64 PCM), with a fallback to the snake_case `inline_data` alias. This is the correct path. The returned bytes are raw **LINEAR16 PCM, 24 kHz, mono** per Gemini TTS spec.
- WAV wrapping (`_pcm_to_wav`, lines ~8060–8085): wraps the PCM with `sample_rate=24000, channels=1, sample_width=2` (16-bit). This matches the Gemini TTS output format exactly, so the produced WAV is valid and playable.
- Content-Type: returns a JSON body `{"audio_b64": ..., "mime_type": "audio/wav", "char_count": N}` (NOT a binary audio stream). The frontend decodes the base64 into a `data:audio/wav;base64,...` URL and plays it. The `mime_type` field is informational; the HTTP response itself is `application/json`. This is internally consistent with the frontend.
- Timeout: `httpx.post(..., timeout=10)` (line 7998). For long replies (capped at 5000 chars in `/tts/speak`, 3000 in `/voice/chat`) 10s can be tight on cold paths; failure mode is graceful (`audio_b64: ""` + `tts_error`, HTTP 200) so the frontend degrades to browser TTS rather than erroring.
- Error handling: any exception returns HTTP 200 with empty `audio_b64` and a `tts_error` string (lines 8128–8135). So `/tts/speak` never surfaces a hard failure to the user; it silently degrades.
- **No auth dependency** on `tts_speak` (signature is just `request: Request`). This is by design (it speaks arbitrary text and touches no learner data). The frontend still sends a Bearer header, which is ignored.

**Verdict on /tts/speak:** the implementation is correct. If it is "not working" it is because `GEMINI_API_KEY` is unset (returns empty audio → frontend falls back to browser TTS, which may look like "Gemini voice isn't working") or because the frontend integration is wrong (see below).

---

## FRONTEND voice.js — findings

File: `static/voice.js` (the backend-served copy). The student-facing chat UI actually lives in the separate Vercel TSX frontend repo (not in this workspace); `static/voice.js` is the shared module both could load.

**Audio capture**
- `MediaRecorder` with MIME preference `['audio/webm;codecs=opus','audio/webm','audio/ogg','audio/mp4','']` (first supported wins). On Chrome this resolves to `audio/webm;codecs=opus`.
- On stop, the Blob is built with `new Blob(_audioChunks, { type: _mediaRec.mimeType || 'audio/webm' })`, and `detected = blob.type || 'audio/webm'` is passed as `mimeType` to `_sendToGemini`. **So the full codec-suffixed string (`audio/webm;codecs=opus`) is what reaches the backend and is forwarded to Gemini** — the likely STT rejection trigger noted above.
- `getUserMedia({ audio: true })` is called with a `NotAllowedError` handler (mic-permission UX is present). Mic access requires a secure context (HTTPS or localhost); on the production HTTPS frontend this is satisfied.

**Transport to /voice/chat**
- Audio is converted to base64 via `FileReader.readAsDataURL` and sent as JSON `{ audio_b64, mime_type, learner_id, level, voice }` with `Content-Type: application/json` and `Authorization: Bearer <tok>`. Base64 JSON is consistent with the backend's `inlineData.data` expectation.
- **Auth gate:** `_sendToGemini` aborts with a toast `"Please sign in to use voice chat."` if no token (`_getToken()`). `_getToken()` reads `localStorage` keys `mpt_token` / `token` / `auth_token` (and sessionStorage `mpt_token`). If the Vercel frontend stores the backend session token under a different key, `/voice/chat` will get `401` and show `"Voice error: Sign in to use voice chat."`.
- **Dead JWT code:** `_getLearnerID()` does `JSON.parse(atob(tok.split('.')[1]...))`, assuming the token is a JWT. The backend token is itsdangerous, not a JWT, so this always throws and returns `''` (caught). Harmless — the backend ignores the empty `learner_id` and uses the authenticated `user.learner_id` instead.

**Response handling & playback**
- Expects `data.transcript`, `data.reply_text`, `data.audio_b64` from `/voice/chat`. Puts `transcript` into the input, fires `SirTegaVoice._onReply(transcript, reply_text)`, and plays `audio_b64` via `_playWav`.
- `_playWav` builds `new Audio('data:audio/wav;base64,' + b64wav)` and `.play()`s it. Plain HTMLAudioElement playback — fine. If `audio_b64` is empty it falls back to `speechSynthesis` browser TTS (`_browserSpeak`). So even total TTS failure degrades gracefully on the frontend.
- `/tts/speak` is called by `_geminiSpeak` for the 🔊 Listen button. On any failure it falls back to `_browserSpeak`.

**apiBase / origin — the key frontend risk**
- `init(options)` sets `_apiBase = (options && options.apiBase) || location.origin`. If the host page calls `init` **without** `apiBase`, voice calls go to the page's own origin. The only in-repo caller, `static/admin.html`, sets `apiBase: location.origin` (line ~1956) — correct there because admin is served by the backend. **The student chat page lives in the Vercel repo; if that page loads `voice.js` and calls `init` without `apiBase: 'https://mypytutor.onrender.com'`, requests hit `https://mypytutor.com.ng/voice/chat` (the SPA) and never reach the FastAPI backend.** This could not be verified from this workspace and is a leading integration suspect.
- HTTPS/HTTP: microphone use requires HTTPS; production is HTTPS, so no issue there.

---

## ROOT CAUSES (ranked by likelihood of being the actual failure)

1. **`GEMINI_API_KEY` not set in the Render dashboard (configuration, not code).** Every voice call (STT and TTS) requires it; `render.yaml` declares it `sync: false` (must be entered manually in Render → Environment). If only `GROQ_API_KEY` was configured, `/voice/chat` returns `503 "Gemini not configured."` and `/tts/speak` returns empty audio (silently degrading to browser TTS). Given the deployment/email-automation context of this engagement, an unset Gemini key is the most probable single explanation for "voice not working." **Verify first in Render → mypy-tutor → Environment.**

2. **Frontend `apiBase` not pointed at the backend (integration).** `voice.js` defaults to `location.origin`. If the Vercel chat page calls `SirTegaVoice.init({...})` without `apiBase: 'https://mypytutor.onrender.com'`, voice requests never reach the backend. Cannot confirm without the Vercel repo, but it is a high-likelihood integration defect.

3. **Audio MIME type carries a codec suffix (`audio/webm;codecs=opus`) into Gemini STT.** The frontend forwards the full `MediaRecorder.mimeType`; Gemini's docs list `audio/webm` but not the parameterized form, so the STT `inlineData.mimeType` may be rejected with HTTP 400 → surfaced to the user as `502 "Transcription error"`. Affects Chrome users (the majority). Medium confidence — Gemini is sometimes lenient, but codec params are a documented risk.

4. **`build_system_prompt(level, learner_id)` wrong argument order (definite code bug).** Does not break the feature, but degrades Sir. Tega's spoken replies and injects the learner_id as a bogus topic. Worth fixing alongside the others.

5. **Synchronous `httpx.post` inside async handlers blocks the single Render worker.** Not a standalone cause of "not working," but under load it can make the service appear to hang and can contribute to Render health-check timeouts.

6. **TTS timeout 10s occasionally too short for long replies.** Failure is graceful (browser-TTS fallback), so this would manifest as "Gemini voice sometimes silent / falls back to robotic browser voice," not a hard failure.

---

## EXACT FIXES NEEDED (file, line, what to change)

> Line numbers are from the current `app/main.py`; verify against the live file before editing. Implement nothing from this report — it is read-only.

**Fix A — Ensure `GEMINI_API_KEY` is set (ops, no code).**
- `render.yaml` already declares `GEMINI_API_KEY` (`sync: false`). Confirm a real key is present in Render → mypy-tutor → Environment. Without it, nothing below matters.

**Fix B — Pass the audio MIME type without the codec suffix to Gemini.**
- File: `app/main.py`, `_gemini_stt`, line 8040.
- Current: `"mimeType": mime_type,` where `mime_type` may be `audio/webm;codecs=opus`.
- Change to strip parameters before sending, e.g.:
  ```python
  clean_mime = mime_type.split(";", 1)[0].strip() or "audio/webm"
  ...
  "mimeType": clean_mime,
  ```
- (Alternatively, normalise in `static/voice.js` `_sendToGemini` before sending `mime_type`.) This removes the most likely STT rejection trigger.

**Fix C — Build the system prompt with the correct arguments.**
- File: `app/main.py`, `voice_chat`, line 8202.
- Current:
  ```python
  system = build_system_prompt(level, learner_id)
  ```
- Correct (matches `build_system_prompt(intent, topic=None, level="beginner", is_gap_topic=False)`):
  ```python
  system = build_system_prompt(intent="concept", level=level)
  ```
- This makes Sir. Tega use the concept-teaching prompt and stops the learner_id being injected as a topic.

**Fix D — Point the frontend at the backend (integration, in the Vercel repo).**
- Wherever the student chat page calls `SirTegaVoice.init({...})`, ensure it passes `apiBase: 'https://mypytutor.onrender.com'` (or reads it from the same API-base constant the rest of the chat UI uses). Without it, voice calls hit the SPA origin. (Could not be verified from this workspace — confirm in the frontend repo.)

**Fix E — Make Gemini calls non-blocking and tolerant (robustness).**
- File: `app/main.py`, `_gemini_tts` (line 7998) and `_gemini_stt` (line 8054).
- These use synchronous `httpx.post` inside `async def`, blocking the single worker. Consider an `httpx.AsyncClient` with `await` (raising timeouts to ~20–30s) so concurrent requests aren't stalled and long TTS generations don't time out. Lower priority than A–D but recommended once the feature is unblocked.

**Fix F — Correct the stale docstring (cosmetic).**
- File: `app/llm_client.py`, the `get_completion` docstring: "Voice/TTS does NOT call this — it uses the browser Web Speech API." is incorrect; voice routes do call `get_completion` for the chat stage and call Gemini REST for STT/TTS. Update or remove to avoid misleading future work.

---

## What was verified vs. not verified

**Verified by reading code:** all route handler logic, the Gemini REST request/response shapes, the `build_system_prompt` signature mismatch, the itsdangerous (non-JWT) token format, the MediaRecorder→base64→inlineData transport, the `_pcm_to_wav` format, and the CORS config.

**Verified against external sources:** `gemini-2.5-flash-preview-tts` is a valid current model and its `responseModalities:["AUDIO"]` + `prebuiltVoiceConfig.voiceName` request shape and 24 kHz/16-bit/mono PCM output match Google's docs; `gemini-2.0-flash` supports audio `inlineData`; Gemini's supported audio input list includes `audio/webm` (but not a parameterized codec form).

**Not verifiable from this workspace (flagged as risks, not facts):** whether `GEMINI_API_KEY` is actually populated in the Render dashboard; how the Vercel student chat page calls `SirTegaVoice.init` (specifically whether `apiBase` is set and which localStorage key holds the session token). These two are the most likely live causes and should be checked first in production.
