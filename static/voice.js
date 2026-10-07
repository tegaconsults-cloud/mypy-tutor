/**
 * SirTegaVoice — Gemini-powered voice feature for MyPy Tutor
 * ===========================================================
 *
 * Flow:
 *   Student taps 🎤  →  MediaRecorder captures audio
 *   Student taps 🎤 again (or silence timeout)  →  audio sent to POST /voice/chat
 *   Backend:  Gemini STT → Sir. Tega LLM → Gemini TTS  →  WAV audio + reply text
 *   Frontend: WAV played back + reply text shown in chat
 *
 * Fallback:  If Gemini voice is unavailable (no API key / network), the
 *            module falls back to browser Web Speech API for both STT and TTS
 *            so the feature always works in some form.
 *
 * Setup (called once after DOM is ready):
 *   SirTegaVoice.init({ apiBase: 'https://mypytutor.onrender.com' });
 *
 * After every AI text response (browser-TTS fallback path):
 *   SirTegaVoice.onNewResponse(messageBubbleEl, responseText);
 */

(function (global) {
  'use strict';

  /* ─── Config ─────────────────────────────────────────────────────────── */
  const STORAGE_KEY     = 'mpt_voice_prefs';
  const SILENCE_TIMEOUT = 2800;   // ms of silence before auto-stop
  const MAX_RECORD_MS   = 30000;  // max recording length
  const MIC_BTN_ID      = 'mic-btn';
  const INPUT_ID        = 'message-input';
  const VOICE_STATUS_ID = 'voice-status';
  const SPEAK_BTN_CLASS = 'sir-tega-speak-btn';

  /* ─── State ──────────────────────────────────────────────────────────── */
  let _apiBase      = '';
  let _token        = '';          // JWT — set by init or refreshed each call
  let _learnerId    = '';
  let _level        = 'beginner';
  let _voice        = 'Aoede';     // Gemini TTS voice

  let _recording    = false;       // mic is capturing
  let _processing   = false;       // waiting for Gemini response
  let _playing      = false;       // audio is playing back
  let _mediaRec     = null;        // MediaRecorder instance
  let _audioChunks  = [];
  let _silenceTimer = null;
  let _maxTimer     = null;
  let _currentAudio = null;        // current HTMLAudioElement

  // Browser TTS fallback (used for 🔊 Listen button on existing messages)
  let _browserTTSAvail = ('speechSynthesis' in window);
  let _browserSpeaking = false;

  let _prefs = {
    geminiVoice: true,     // use Gemini voice pipeline
    autoSpeak:   false,    // auto-read AI responses
    voice:       'Aoede',  // Gemini TTS voice name
    rate:        1.0,      // browser TTS fallback rate
    pitch:       1.0,
    volume:      1.0,
    voiceName:   '',       // browser TTS voice name
  };

  /* ─── Persistence ────────────────────────────────────────────────────── */
  function _load()  { try { Object.assign(_prefs, JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}')); } catch(_){} }
  function _save()  { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_prefs)); } catch(_){} }

  /* ─── Token helpers ──────────────────────────────────────────────────── */
  function _getToken() {
    return localStorage.getItem('mpt_token')
        || localStorage.getItem('token')
        || localStorage.getItem('auth_token')
        || sessionStorage.getItem('mpt_token')
        || _token || '';
  }
  function _getLearnerID() {
    const lid = localStorage.getItem('mpt_learner_id')
             || localStorage.getItem('learner_id')
             || _learnerId || '';
    if (lid) return lid;
    try {
      const tok = _getToken();
      if (!tok) return '';
      const p = JSON.parse(atob(tok.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
      return p.learner_id || p.sub || '';
    } catch(_) { return ''; }
  }

  /* ─── DOM helpers ────────────────────────────────────────────────────── */
  function _micBtn()   { return document.getElementById(MIC_BTN_ID); }
  function _inputEl()  { return document.getElementById(INPUT_ID); }
  function _statusEl() { return document.getElementById(VOICE_STATUS_ID); }

  function _setStatus(text, type) {
    const el = _statusEl();
    if (!el) return;
    el.textContent = text || '';
    el.className   = text ? ('stv-status stv-status-' + (type||'info')) : '';
  }

  function _setBtnState(state) {
    const btn = _micBtn();
    if (!btn) return;
    btn.className = 'stv-mic-' + state;
    btn.setAttribute('aria-label',
      state === 'idle'       ? 'Start voice chat with Sir. Tega' :
      state === 'listening'  ? 'Recording — tap to stop' :
      state === 'processing' ? 'Processing…' :
      state === 'playing'    ? 'Sir. Tega is speaking — tap to stop' : 'Voice');
    btn.title = btn.getAttribute('aria-label');
  }

  /* ─── Audio playback ─────────────────────────────────────────────────── */
  function _playWav(b64wav) {
    _stopPlayback();
    const dataUrl  = 'data:audio/wav;base64,' + b64wav;
    _currentAudio  = new Audio(dataUrl);
    _playing       = true;
    _setBtnState('playing');
    _setStatus('Sir. Tega is speaking…', 'speaking');
    _currentAudio.onended = () => {
      _playing = false;
      _setBtnState('idle');
      _setStatus('');
    };
    _currentAudio.onerror = () => {
      _playing = false;
      _setBtnState('idle');
      _setStatus('');
    };
    _currentAudio.play().catch(err => {
      console.warn('[SirTegaVoice] Audio play error:', err);
      _playing = false;
      _setBtnState('idle');
      _setStatus('');
    });
  }

  function _stopPlayback() {
    if (_currentAudio) {
      try { _currentAudio.pause(); _currentAudio.src = ''; } catch(_) {}
      _currentAudio = null;
    }
    _playing = false;
    // Also cancel browser TTS if it was running
    if (_browserTTSAvail && _browserSpeaking) {
      speechSynthesis.cancel();
      _browserSpeaking = false;
    }
    _updateSpeakBtns(false);
  }

  /* ─── MediaRecorder recording ────────────────────────────────────────── */
  async function _startRecording() {
    if (_recording || _processing) return;

    // Stop any current playback so mic picks up cleanly
    _stopPlayback();

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch(err) {
      const msg = err.name === 'NotAllowedError'
        ? 'Microphone access denied. Allow microphone in your browser settings.'
        : 'Could not access microphone: ' + err.message;
      _toast(msg, 'warn');
      return;
    }

    // Pick the best supported MIME type
    const mimeType = ['audio/webm;codecs=opus','audio/webm','audio/ogg','audio/mp4','']
      .find(m => !m || MediaRecorder.isTypeSupported(m)) || '';

    _audioChunks = [];
    _mediaRec    = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    _recording   = true;
    _setBtnState('listening');
    _setStatus('Listening… tap 🎤 to stop', 'listening');

    _mediaRec.ondataavailable = e => {
      if (e.data && e.data.size > 0) _audioChunks.push(e.data);
    };

    _mediaRec.onstop = async () => {
      // Stop all microphone tracks
      stream.getTracks().forEach(t => t.stop());
      clearTimeout(_silenceTimer);
      clearTimeout(_maxTimer);

      if (_audioChunks.length === 0) {
        _recording = false;
        _setBtnState('idle');
        _setStatus('');
        return;
      }

      const blob     = new Blob(_audioChunks, { type: _mediaRec.mimeType || 'audio/webm' });
      const detected = blob.type || 'audio/webm';
      _audioChunks   = [];
      _recording     = false;

      await _sendToGemini(blob, detected);
    };

    _mediaRec.start(200);  // collect 200ms chunks

    // Auto-stop after max duration
    _maxTimer = setTimeout(() => { if (_recording) _stopRecording(); }, MAX_RECORD_MS);

    // Silence detection using Web Audio API (optional — degrades gracefully)
    _startSilenceDetection(stream);
  }

  function _stopRecording() {
    if (!_recording || !_mediaRec) return;
    try { _mediaRec.stop(); } catch(_) {}
  }

  function _startSilenceDetection(stream) {
    try {
      const ctx      = new (window.AudioContext || window.webkitAudioContext)();
      const source   = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const buf = new Uint8Array(analyser.frequencyBinCount);

      function check() {
        if (!_recording) { try { ctx.close(); } catch(_) {} return; }
        analyser.getByteFrequencyData(buf);
        const avg = buf.reduce((a,b) => a+b, 0) / buf.length;
        if (avg < 8) {
          // Very quiet — start/reset silence timer
          if (!_silenceTimer) {
            _silenceTimer = setTimeout(() => {
              if (_recording) _stopRecording();
            }, SILENCE_TIMEOUT);
          }
        } else {
          clearTimeout(_silenceTimer);
          _silenceTimer = null;
        }
        requestAnimationFrame(check);
      }
      requestAnimationFrame(check);
    } catch(_) {
      // Web Audio API not available — silence detection disabled, user stops manually
    }
  }

  /* ─── Gemini voice pipeline ──────────────────────────────────────────── */
  async function _sendToGemini(blob, mimeType) {
    _processing = true;
    _setBtnState('processing');
    _setStatus('Processing with Gemini…', 'processing');

    // Convert Blob → base64
    let b64;
    try {
      b64 = await new Promise((res, rej) => {
        const fr = new FileReader();
        fr.onload  = () => res(fr.result.split(',')[1]);
        fr.onerror = rej;
        fr.readAsDataURL(blob);
      });
    } catch(err) {
      _processing = false;
      _setBtnState('idle');
      _setStatus('');
      _toast('Could not read audio data.', 'warn');
      return;
    }

    const tok = _getToken();
    if (!tok) {
      _processing = false;
      _setBtnState('idle');
      _setStatus('');
      _toast('Please sign in to use voice chat.', 'warn');
      return;
    }

    try {
      const resp = await fetch(_apiBase + '/voice/chat', {
        method:  'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': 'Bearer ' + tok,
        },
        body: JSON.stringify({
          audio_b64:  b64,
          mime_type:  mimeType,
          learner_id: _getLearnerID(),
          level:      _level,
          voice:      _prefs.voice || _voice,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Server error ' + resp.status }));
        throw new Error(err.detail || 'Voice chat failed');
      }

      const data = await resp.json();

      // Show transcript in input
      const inp = _inputEl();
      if (inp && data.transcript) {
        inp.value = data.transcript;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }

      // Show reply text in chat (hook for host app)
      if (data.reply_text && typeof global.SirTegaVoice._onReply === 'function') {
        global.SirTegaVoice._onReply(data.transcript, data.reply_text);
      }

      // Play Gemini TTS audio
      if (data.audio_b64) {
        _playWav(data.audio_b64);
      } else if (_browserTTSAvail && data.reply_text) {
        // TTS generation failed server-side — use browser fallback
        _browserSpeak(data.reply_text);
      }

      _setStatus('');

    } catch(err) {
      console.warn('[SirTegaVoice] Gemini voice error:', err);
      _toast('Voice error: ' + err.message, 'warn');
      _setStatus('');

      // Fall back to browser STT result already in the input
      const inp = _inputEl();
      if (inp && inp.value.trim()) {
        _toast('Transcript ready — tap Send to ask Sir. Tega', 'info');
      }
    } finally {
      _processing = false;
      if (!_playing) _setBtnState('idle');
    }
  }

  /* ─── Gemini TTS for existing text (🔊 Listen button) ──────────────── */
  async function _geminiSpeak(text) {
    const tok = _getToken();
    if (!tok) { _browserSpeak(text); return; }

    _stopPlayback();
    _updateSpeakBtns(true);

    try {
      const resp = await fetch(_apiBase + '/tts/speak', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok },
        body: JSON.stringify({ text, voice: _prefs.voice || _voice }),
      });

      if (!resp.ok) throw new Error('TTS server error ' + resp.status);
      const data = await resp.json();

      if (data.audio_b64) {
        _playWav(data.audio_b64);
      } else {
        throw new Error('No audio returned');
      }
    } catch(err) {
      console.warn('[SirTegaVoice] /tts/speak failed, using browser TTS:', err);
      _updateSpeakBtns(false);
      _browserSpeak(text);
    }
  }

  /* ─── Browser TTS fallback ───────────────────────────────────────────── */
  const _MAX_CHUNK = 220;

  function _browserSpeak(raw) {
    if (!_browserTTSAvail || !_prefs.enabled) return;
    speechSynthesis.cancel();
    _browserSpeaking = true;
    _updateSpeakBtns(true);

    const text   = _cleanText(raw);
    const chunks = _chunkText(text);
    const voice  = _pickBrowserVoice();
    let   idx    = 0;

    function next() {
      if (idx >= chunks.length) {
        _browserSpeaking = false;
        _updateSpeakBtns(false);
        return;
      }
      const utt   = new SpeechSynthesisUtterance(chunks[idx]);
      utt.rate    = _prefs.rate;
      utt.pitch   = _prefs.pitch;
      utt.volume  = _prefs.volume;
      if (voice) utt.voice = voice;
      utt.onend   = () => { idx++; next(); };
      utt.onerror = () => { _browserSpeaking = false; _updateSpeakBtns(false); };
      speechSynthesis.speak(utt);
    }
    next();
  }

  function _pickBrowserVoice() {
    if (!_browserTTSAvail) return null;
    const voices = speechSynthesis.getVoices();
    if (_prefs.voiceName) {
      const m = voices.find(v => v.name === _prefs.voiceName);
      if (m) return m;
    }
    for (const lang of ['en-NG','en-GB','en-US','en-AU']) {
      const v = voices.find(v => v.lang.startsWith(lang));
      if (v) return v;
    }
    return voices.find(v => v.lang.startsWith('en')) || null;
  }

  function _cleanText(raw) {
    return raw
      .replace(/```[\s\S]*?```/g, ' code block. ')
      .replace(/`([^`\n]{1,120})`/g, '$1')
      .replace(/\*{1,3}(.+?)\*{1,3}/g, '$1')
      .replace(/#{1,6}\s+(.+)$/gm, '$1. ')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/^[-*>]\s+/gm, '. ')
      .replace(/\|/g, ' ')
      .replace(/\bAPI\b/g, 'A P I').replace(/\bXP\b/g, 'experience points')
      .replace(/\bOOP\b/g, 'object oriented programming')
      .replace(/\bML\b/g, 'machine learning').replace(/\bAI\b/g, 'A I')
      .replace(/[ \t]{2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
  }

  function _chunkText(text) {
    const sents = text.match(/[^.!?\n]+[.!?\n]*/g) || [text];
    const out = []; let cur = '';
    for (const s of sents) {
      if ((cur+s).length > _MAX_CHUNK && cur) { out.push(cur.trim()); cur = s; }
      else cur += s;
    }
    if (cur.trim()) out.push(cur.trim());
    return out.filter(Boolean);
  }

  /* ─── 🔊 Speak button on AI message bubbles ─────────────────────────── */
  function _updateSpeakBtns(active) {
    document.querySelectorAll('.' + SPEAK_BTN_CLASS).forEach(btn => {
      const icon  = btn.querySelector('.stv-icon');
      const label = btn.querySelector('.stv-label');
      if (icon)  icon.textContent  = active ? '⏹' : '🔊';
      if (label) label.textContent = active ? 'Stop' : 'Listen';
      btn.classList.toggle('stv-speaking', active);
    });
  }

  function attachSpeakButton(container, text) {
    if (!container || container.querySelector('.'+SPEAK_BTN_CLASS)) return;
    const btn = document.createElement('button');
    btn.className = SPEAK_BTN_CLASS + ' stv-btn';
    btn.type      = 'button';
    btn.title     = 'Listen to this response';
    btn.innerHTML = '<span class="stv-icon">🔊</span><span class="stv-label">Listen</span>';
    btn.addEventListener('click', e => {
      e.stopPropagation();
      if (_playing || _browserSpeaking) {
        _stopPlayback();
      } else {
        if (_prefs.geminiVoice) {
          _geminiSpeak(text);
        } else {
          _browserSpeak(text);
        }
      }
    });
    container.appendChild(btn);
  }

  function onNewResponse(bubbleEl, rawText) {
    if (bubbleEl) attachSpeakButton(bubbleEl, rawText);
    if (_prefs.autoSpeak && rawText) {
      setTimeout(() => {
        if (_prefs.geminiVoice) _geminiSpeak(rawText);
        else _browserSpeak(rawText);
      }, 200);
    }
  }

  /* ─── Mic button wiring ──────────────────────────────────────────────── */
  function toggleMic() {
    if (_processing) return;
    if (_playing)    { _stopPlayback(); return; }
    if (_recording)  { _stopRecording(); return; }
    _startRecording();
  }

  function _wireMicBtn() {
    const btn = _micBtn();
    if (!btn) return;
    // Check MediaRecorder support
    if (!window.MediaRecorder || !navigator.mediaDevices) {
      btn.style.display = 'none';
      return;
    }
    btn.type = 'button';
    btn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="22"/>
        <line x1="8"  y1="22" x2="16" y2="22"/>
      </svg>`;
    btn.addEventListener('click', toggleMic);
    _setBtnState('idle');
  }

  /* ─── DOM injection (mic + settings trigger + status) ───────────────── */
  function _injectChatControls() {
    const row   = document.getElementById('message-row');
    const input = document.getElementById(INPUT_ID);
    if (!row || !input) return;

    if (!document.getElementById(MIC_BTN_ID)) {
      const mic = document.createElement('button');
      mic.id    = MIC_BTN_ID;
      mic.type  = 'button';
      const sendBtn = document.getElementById('send-btn');
      sendBtn ? row.insertBefore(mic, sendBtn) : row.appendChild(mic);
    }

    if (!document.getElementById('stv-settings-trigger')) {
      const trigger = document.createElement('button');
      trigger.id        = 'stv-settings-trigger';
      trigger.type      = 'button';
      trigger.title     = 'Voice settings';
      trigger.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round">
        <line x1="9" y1="8" x2="9" y2="16"/>
        <line x1="13" y1="5" x2="13" y2="19"/>
        <line x1="17" y1="8" x2="17" y2="16"/>
        <line x1="5" y1="12" x2="5" y2="12"/>
        <line x1="21" y1="12" x2="21" y2="12"/>
      </svg>`;
      trigger.style.cssText = 'background:transparent;border:none;color:var(--text-muted,#475569);cursor:pointer;padding:0 6px;display:flex;align-items:center;flex-shrink:0;transition:color .18s';
      trigger.addEventListener('click', toggleSettings);
      const sendBtn = document.getElementById('send-btn');
      const mic = document.getElementById(MIC_BTN_ID);
      if (sendBtn) row.insertBefore(trigger, sendBtn);
      else if (mic && mic.parentNode) mic.parentNode.insertBefore(trigger, mic.nextSibling);
    }

    if (!document.getElementById(VOICE_STATUS_ID)) {
      const status = document.createElement('div');
      status.id = VOICE_STATUS_ID;
      if (row.parentNode) row.parentNode.insertBefore(status, row.nextSibling);
    }
  }

  /* ─── Settings panel ─────────────────────────────────────────────────── */
  let _settingsOpen = false;

  function _buildSettingsPanel() {
    if (document.getElementById('stv-settings-panel')) return;
    const panel = document.createElement('div');
    panel.id        = 'stv-settings-panel';
    panel.className = 'stv-settings-panel';
    panel.setAttribute('role','dialog');
    panel.setAttribute('aria-label','Voice settings');
    panel.style.display = 'none';

    const GEMINI_VOICES = ['Aoede','Kore','Charon','Puck','Fenrir','Leda','Orus','Zephyr'];
    panel.innerHTML = `
      <div class="stv-settings-header">
        <span>🎙 Voice Settings <span style="font-size:.68rem;color:#6ee7b7;margin-left:4px">✦ Gemini</span></span>
        <button class="stv-close-btn" id="stv-close-settings" aria-label="Close">✕</button>
      </div>
      <div class="stv-settings-body">
        <label class="stv-row">
          <span>Gemini voice</span>
          <input type="checkbox" id="stv-gemini-voice" ${_prefs.geminiVoice ? 'checked' : ''} />
        </label>
        <label class="stv-row">
          <span>Sir. Tega's voice</span>
          <select id="stv-gemini-voice-select" class="stv-select">
            ${GEMINI_VOICES.map(v => `<option value="${v}" ${v===_prefs.voice?'selected':''}>${v}</option>`).join('')}
          </select>
        </label>
        <label class="stv-row">
          <span>Auto-speak responses</span>
          <input type="checkbox" id="stv-auto" ${_prefs.autoSpeak ? 'checked' : ''} />
        </label>
        <div class="stv-row stv-test-row">
          <button id="stv-test-btn" class="stv-test-speak-btn" type="button">🔊 Test Sir. Tega's voice</button>
        </div>
      </div>`;

    document.body.appendChild(panel);

    document.getElementById('stv-close-settings').addEventListener('click', closeSettings);
    document.getElementById('stv-gemini-voice').addEventListener('change', e => {
      _prefs.geminiVoice = e.target.checked; _save();
    });
    document.getElementById('stv-gemini-voice-select').addEventListener('change', e => {
      _prefs.voice = e.target.value; _save();
    });
    document.getElementById('stv-auto').addEventListener('change', e => {
      _prefs.autoSpeak = e.target.checked; _save();
    });
    document.getElementById('stv-test-btn').addEventListener('click', () => {
      const h = new Date().getHours();
      const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
      const msg = `${g}! I am Sir. Tega, your Python and AI tutor. Powered by Gemini. Ask me anything!`;
      if (_prefs.geminiVoice) _geminiSpeak(msg);
      else _browserSpeak(msg);
    });

    document.addEventListener('click', e => {
      if (_settingsOpen && !panel.contains(e.target) && !e.target.closest('#stv-settings-trigger')) {
        closeSettings();
      }
    }, true);
  }

  function openSettings()   { _buildSettingsPanel(); const p=document.getElementById('stv-settings-panel'); if(p){p.style.display='block';_settingsOpen=true;} }
  function closeSettings()  { const p=document.getElementById('stv-settings-panel'); if(p){p.style.display='none';_settingsOpen=false;} }
  function toggleSettings() { _settingsOpen ? closeSettings() : openSettings(); }

  /* ─── Toast ──────────────────────────────────────────────────────────── */
  function _toast(msg, type) {
    let el = document.getElementById('stv-toast');
    if (!el) { el = document.createElement('div'); el.id='stv-toast'; document.body.appendChild(el); }
    el.textContent = msg;
    el.className   = 'stv-toast stv-toast-' + (type||'info');
    el.style.display = 'block';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.style.display='none'; }, 3400);
  }

  /* ─── CSS ─────────────────────────────────────────────────────────────── */
  function _injectStyles() {
    if (document.getElementById('stv-styles')) return;
    const s = document.createElement('style');
    s.id = 'stv-styles';
    s.textContent = `
      /* Mic button states */
      #mic-btn { background:transparent;border:none;cursor:pointer;color:var(--text-muted,#475569);
        display:flex;align-items:center;padding:0 8px;flex-shrink:0;transition:color .18s; }
      #mic-btn:hover { color:var(--accent,#3b82f6); }
      #mic-btn.stv-mic-listening { color:#ef4444;animation:stv-pulse 1s ease-in-out infinite; }
      #mic-btn.stv-mic-processing { color:#f59e0b;animation:stv-spin 1s linear infinite; }
      #mic-btn.stv-mic-playing { color:#10b981; }

      @keyframes stv-pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
      @keyframes stv-spin  { to{transform:rotate(360deg)} }

      /* Voice status */
      #voice-status { font-size:.76rem;padding:2px 12px;min-height:18px;transition:opacity .2s; }
      #voice-status.stv-status-listening  { color:#ef4444; }
      #voice-status.stv-status-processing { color:#f59e0b; }
      #voice-status.stv-status-speaking   { color:#10b981; }
      #voice-status.stv-status-info       { color:#93c5fd; }

      /* 🔊 Listen buttons on AI bubbles */
      .sir-tega-speak-btn.stv-btn {
        display:inline-flex;align-items:center;gap:4px;padding:3px 10px;margin-top:8px;
        font-size:.74rem;background:rgba(59,130,246,.1);color:#93c5fd;
        border:1px solid rgba(59,130,246,.25);border-radius:20px;
        cursor:pointer;transition:background .18s,transform .1s;user-select:none;
      }
      .sir-tega-speak-btn.stv-btn:hover { background:rgba(59,130,246,.2);transform:scale(1.04); }
      .sir-tega-speak-btn.stv-speaking {
        background:rgba(239,68,68,.12);color:#fca5a5;border-color:rgba(239,68,68,.3);
        animation:stv-pulse 1.2s ease-in-out infinite;
      }

      /* Settings panel */
      .stv-settings-panel {
        position:fixed;bottom:80px;right:16px;width:300px;
        background:#0d1120;border:1px solid rgba(59,130,246,.22);
        border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.65);
        z-index:1001;font-family:-apple-system,'Inter',sans-serif;overflow:hidden;
      }
      .stv-settings-header {
        display:flex;justify-content:space-between;align-items:center;
        padding:11px 15px;background:rgba(37,99,235,.1);
        font-weight:600;font-size:.87rem;color:#93c5fd;
        border-bottom:1px solid rgba(59,130,246,.12);
      }
      .stv-close-btn { background:none;border:none;cursor:pointer;color:#64748b;font-size:.95rem;padding:0 2px; }
      .stv-close-btn:hover { color:#f87171; }
      .stv-settings-body { padding:13px 15px;display:flex;flex-direction:column;gap:11px; }
      .stv-row { display:flex;justify-content:space-between;align-items:center;font-size:.82rem;color:#cbd5e1;gap:10px; }
      .stv-row span { flex:1; }
      .stv-row input[type="checkbox"] { width:17px;height:17px;cursor:pointer;accent-color:#3b82f6; }
      .stv-select { background:#111827;color:#e2e8f0;border:1px solid rgba(255,255,255,.1);
        border-radius:6px;padding:4px 6px;font-size:.78rem;flex:1.4;cursor:pointer; }
      .stv-test-row { justify-content:center;margin-top:3px; }
      .stv-test-speak-btn { background:rgba(59,130,246,.13);color:#93c5fd;
        border:1px solid rgba(59,130,246,.28);border-radius:8px;
        padding:6px 16px;font-size:.82rem;cursor:pointer;transition:background .15s; }
      .stv-test-speak-btn:hover { background:rgba(59,130,246,.26); }

      /* Toast */
      .stv-toast { position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
        padding:8px 18px;border-radius:22px;font-size:.82rem;z-index:2001;
        pointer-events:none;max-width:82vw;text-align:center;
        box-shadow:0 4px 14px rgba(0,0,0,.45); }
      .stv-toast-info { background:#1e3a5f;color:#93c5fd;border:1px solid #2563eb; }
      .stv-toast-warn { background:#422006;color:#fcd34d;border:1px solid #d97706; }
      .stv-toast-ok   { background:#064e3b;color:#6ee7b7;border:1px solid #059669; }
    `;
    document.head.appendChild(s);
  }

  /* ─── Init ───────────────────────────────────────────────────────────── */
  function init(options) {
    _apiBase    = (options && options.apiBase)    || location.origin;
    _token      = (options && options.token)      || '';
    _learnerId  = (options && options.learnerId)  || '';
    _level      = (options && options.level)      || 'beginner';
    _voice      = (options && options.voice)      || 'Aoede';
    if (options && options.onReply) global.SirTegaVoice._onReply = options.onReply;
    if (options && typeof options.autoSpeak !== 'undefined') _prefs.autoSpeak = options.autoSpeak;
    _load();
    _injectStyles();
    _injectChatControls();
    _wireMicBtn();
    if (_browserTTSAvail) {
      speechSynthesis.getVoices();
      speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
    }
    document.documentElement.setAttribute('data-sir-tega-voice', 'gemini');
  }

  /* ─── Public API ─────────────────────────────────────────────────────── */
  global.SirTegaVoice = {
    init,
    // Voice chat (full Gemini pipeline via mic)
    toggleMic,
    isMicActive:  () => _recording,
    isProcessing: () => _processing,
    isPlaying:    () => _playing,
    stopPlayback: _stopPlayback,
    // TTS for existing text
    speak:        (text) => { if (_prefs.geminiVoice) _geminiSpeak(text); else _browserSpeak(text); },
    stop:         _stopPlayback,
    toggle:       (text) => { if (_playing||_browserSpeaking) _stopPlayback(); else { if (_prefs.geminiVoice) _geminiSpeak(text); else _browserSpeak(text); } },
    isSpeaking:   () => _playing || _browserSpeaking,
    // Bubble helpers
    attachSpeakButton,
    onNewResponse,
    // Settings
    openSettings,
    closeSettings,
    toggleSettings,
    isSupported:  () => !!(window.MediaRecorder && navigator.mediaDevices),
    // Overrideable callback — host app wires this to render reply text
    _onReply:     null,
  };

}(window));
