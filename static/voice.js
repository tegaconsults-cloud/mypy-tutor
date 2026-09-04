/**
 * SirTegaVoice — Voice feature for MyPy Tutor
 * ============================================
 *
 * How it works:
 *  - The mic button (#mic-btn) lives INSIDE the chat input row (#message-row),
 *    placed between #message-input and #send-btn by the frontend HTML.
 *  - Tapping the mic starts speech recognition (en-NG Nigerian English first).
 *  - Recognised speech fills #message-input in real time (interim results).
 *  - When the user stops speaking, the text stays in the input so they can
 *    review and edit before hitting send — exactly like ChatGPT voice input.
 *  - Sir. Tega's responses are read aloud when autoSpeak is on, or when
 *    the user taps the 🔊 Listen button on any AI message bubble.
 *
 * Setup (called by the chat page after DOM is ready):
 *   SirTegaVoice.init({
 *     apiBase:    window.location.origin,
 *     autoSpeak:  false,
 *   });
 *
 * After every AI response:
 *   SirTegaVoice.onNewResponse(messageBubbleEl, responseText);
 */

(function (global) {
  'use strict';

  /* ─── Constants ──────────────────────────────────────────────────────────── */
  const STORAGE_KEY   = 'mpt_voice_prefs';
  const API_TIMEOUT   = 8000;
  const MAX_CHUNK_LEN = 220;   // chars per utterance chunk (iOS TTS limit workaround)

  /* ─── IDs / selectors expected in the chat HTML ─────────────────────────── */
  const MIC_BTN_ID       = 'mic-btn';          // button inside #message-row
  const INPUT_ID         = 'message-input';    // the chat textarea
  const VOICE_STATUS_ID  = 'voice-status';     // small status text shown below input
  const SPEAK_BTN_CLASS  = 'sir-tega-speak-btn';

  /* ─── State ──────────────────────────────────────────────────────────────── */
  let _apiBase      = '';
  let _speaking     = false;
  let _recognising  = false;
  let _recognition  = null;
  let _voices       = [];
  let _settingsOpen = false;

  let _prefs = {
    enabled:   true,    // master TTS on/off
    autoSpeak: false,   // auto-read AI responses
    rate:      1.0,
    pitch:     1.0,
    volume:    1.0,
    voiceName: '',
  };

  /* ─── Persistence ────────────────────────────────────────────────────────── */
  function _loadPrefs() {
    try { Object.assign(_prefs, JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')); }
    catch (_) { /* ignore */ }
  }
  function _savePrefs() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_prefs)); } catch (_) { /* */ }
  }

  /* ─── Helpers ────────────────────────────────────────────────────────────── */
  function _input()      { return document.getElementById(INPUT_ID); }
  function _micBtn()     { return document.getElementById(MIC_BTN_ID); }
  function _statusEl()   { return document.getElementById(VOICE_STATUS_ID); }

  function _setStatus(text) {
    const el = _statusEl();
    if (!el) return;
    if (text) { el.textContent = text; el.classList.add('visible'); }
    else       { el.textContent = '';  el.classList.remove('visible'); }
  }

  /* ─── Voices ─────────────────────────────────────────────────────────────── */
  function _loadVoices() {
    if (!('speechSynthesis' in window)) return;
    _voices = speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => { _voices = speechSynthesis.getVoices(); };
  }

  function _pickVoice() {
    if (!_voices.length) return null;
    if (_prefs.voiceName) {
      const match = _voices.find(v => v.name === _prefs.voiceName);
      if (match) return match;
    }
    for (const lang of ['en-NG', 'en-GB', 'en-US', 'en-AU']) {
      const v = _voices.find(v => v.lang.startsWith(lang));
      if (v) return v;
    }
    return _voices.find(v => v.lang.startsWith('en')) || _voices[0];
  }

  /* ─── Text cleaning ──────────────────────────────────────────────────────── */
  function _cleanText(raw) {
    return raw
      .replace(/```[\s\S]*?```/g, ' code block. ')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/_{1,3}(.+?)_{1,3}/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/^[>\-•*+]\s+/gm, '. ')
      .replace(/^\d+\.\s+/gm, '. ')
      .replace(/\|/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]{2,}/g, ' ')
      .trim();
  }

  function _chunkText(text) {
    const sentences = text.match(/[^.!?\n]+[.!?\n]*/g) || [text];
    const chunks = [];
    let current = '';
    for (const s of sentences) {
      if ((current + s).length > MAX_CHUNK_LEN && current) {
        chunks.push(current.trim());
        current = s;
      } else {
        current += s;
      }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks.filter(Boolean);
  }

  async function _prepareText(raw) {
    if (raw.length < 600) return _cleanText(raw);
    try {
      const ctrl  = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), API_TIMEOUT);
      const res   = await fetch(`${_apiBase}/tts/prepare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: raw }),
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (res.ok) { const d = await res.json(); return d.text || _cleanText(raw); }
    } catch (_) { /* fall through */ }
    return _cleanText(raw);
  }

  /* ─── TTS ────────────────────────────────────────────────────────────────── */
  function _stopAll() {
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    _speaking = false;
    _updateSpeakBtns(false);
  }

  async function speak(rawText) {
    if (!('speechSynthesis' in window) || !_prefs.enabled || !rawText?.trim()) return;
    _stopAll();
    _speaking = true;
    _updateSpeakBtns(true);

    const cleaned = await _prepareText(rawText);
    const chunks  = _chunkText(cleaned);
    const voice   = _pickVoice();
    let idx = 0;

    function next() {
      if (idx >= chunks.length) { _speaking = false; _updateSpeakBtns(false); return; }
      const utt   = new SpeechSynthesisUtterance(chunks[idx]);
      utt.rate    = _prefs.rate;
      utt.pitch   = _prefs.pitch;
      utt.volume  = _prefs.volume;
      if (voice) utt.voice = voice;
      utt.onend   = () => { idx++; next(); };
      utt.onerror = (e) => {
        if (e.error !== 'interrupted') console.warn('[SirTegaVoice] TTS error:', e.error);
        _speaking = false;
        _updateSpeakBtns(false);
      };
      speechSynthesis.speak(utt);
    }
    next();
  }

  function stop()          { _stopAll(); }
  function toggle(text)    { _speaking ? stop() : speak(text); }
  function isSpeaking()    { return _speaking; }

  function _updateSpeakBtns(active) {
    document.querySelectorAll(`.${SPEAK_BTN_CLASS}`).forEach(btn => {
      const icon  = btn.querySelector('.stv-icon');
      const label = btn.querySelector('.stv-label');
      if (icon)  icon.textContent  = active ? '⏹' : '🔊';
      if (label) label.textContent = active ? 'Stop' : 'Listen';
      btn.classList.toggle('stv-speaking', active);
      btn.title = active ? 'Stop speaking' : 'Listen to this response';
    });
  }

  /* Attach a 🔊 Listen button to an AI message bubble */
  function attachSpeakButton(container, text) {
    if (!('speechSynthesis' in window)) return;
    if (!container || container.querySelector(`.${SPEAK_BTN_CLASS}`)) return;

    const btn = document.createElement('button');
    btn.className = `${SPEAK_BTN_CLASS} stv-btn`;
    btn.type      = 'button';
    btn.title     = 'Listen to this response';
    btn.innerHTML = `<span class="stv-icon">🔊</span><span class="stv-label">Listen</span>`;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Stop all other speak buttons
      document.querySelectorAll(`.${SPEAK_BTN_CLASS}`).forEach(b => {
        if (b !== btn) { b.classList.remove('stv-speaking'); }
      });
      toggle(text);
    });

    container.appendChild(btn);
  }

  /* Called on every new AI response — attach button + auto-speak if enabled */
  function onNewResponse(bubbleEl, rawText) {
    if (bubbleEl) attachSpeakButton(bubbleEl, rawText);
    if (_prefs.enabled && _prefs.autoSpeak) {
      setTimeout(() => speak(rawText), 200);
    }
  }

  /* ─── Speech Recognition (STT) ─────────────────────────────────────────── */
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition || null;

  function isMicActive() { return _recognising; }

  function toggleMic() {
    if (!SpeechRecognition) {
      _showToast('Voice input is not supported in this browser.', 'warn');
      return;
    }
    if (_recognising) { _recognition && _recognition.stop(); return; }
    _startMic();
  }

  function _startMic() {
    const inputEl = _input();
    if (!inputEl) return;

    _recognition = new SpeechRecognition();
    _recognition.lang            = 'en-NG';
    _recognition.continuous      = false;
    _recognition.interimResults  = true;
    _recognition.maxAlternatives = 1;

    const btn = _micBtn();

    _recognition.onstart = () => {
      _recognising = true;
      if (btn) btn.classList.add('listening');
      _setStatus('Listening… speak now');
      // Stop any playing TTS so mic picks up cleanly
      _stopAll();
    };

    _recognition.onresult = (e) => {
      let interim = '';
      let final   = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t;
        else interim += t;
      }
      // Show transcript in the input in real time
      inputEl.value = final || interim;
      // Trigger React/Vue/etc. input event so the framework sees the value change
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      // Grow the textarea if needed
      inputEl.style.height = 'auto';
      inputEl.style.height = Math.min(inputEl.scrollHeight, 150) + 'px';
    };

    _recognition.onend = () => {
      _recognising = false;
      if (btn) btn.classList.remove('listening');
      _setStatus('');

      const val = inputEl.value.trim();
      if (val) {
        inputEl.focus();
        inputEl.setSelectionRange(val.length, val.length);
        _showToast('✓ Ready — review and tap Send', 'info');
      }
    };

    _recognition.onerror = (e) => {
      _recognising = false;
      if (btn) btn.classList.remove('listening');
      _setStatus('');

      const msgs = {
        'not-allowed':   'Microphone access denied. Allow microphone in your browser settings.',
        'no-speech':     'No speech detected. Please try again.',
        'audio-capture': 'No microphone found. Please connect a microphone.',
        'network':       'Network error during voice recognition. Check your connection.',
        'aborted':       '',
      };
      const msg = msgs[e.error] || `Voice error: ${e.error}`;
      if (msg) _showToast(msg, 'warn');
    };

    try { _recognition.start(); }
    catch (err) { console.warn('[SirTegaVoice] mic start error:', err); }
  }

  /* ─── Wire the #mic-btn in the chat input row ─────────────────────────── */
  function _wireMicBtn() {
    const btn = _micBtn();
    if (!btn) return;

    if (!SpeechRecognition) {
      // Hide mic button if browser doesn't support STT
      btn.style.display = 'none';
      return;
    }

    btn.title       = 'Speak your question (click to start, click again to stop)';
    btn.innerHTML   = '🎤';
    btn.setAttribute('aria-label', 'Voice input');
    btn.setAttribute('type', 'button');

    btn.addEventListener('click', toggleMic);
  }

  /* ─── Settings Panel ──────────────────────────────────────────────────── */
  function _buildSettingsPanel() {
    if (document.getElementById('stv-settings-panel')) return;

    const panel = document.createElement('div');
    panel.id        = 'stv-settings-panel';
    panel.className = 'stv-settings-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Voice settings');
    panel.style.display = 'none';

    panel.innerHTML = `
      <div class="stv-settings-header">
        <span>🎙 Voice Settings</span>
        <button class="stv-close-btn" id="stv-close-settings" aria-label="Close">✕</button>
      </div>
      <div class="stv-settings-body">
        <label class="stv-row">
          <span>Voice enabled</span>
          <input type="checkbox" id="stv-enabled" ${_prefs.enabled ? 'checked' : ''} />
        </label>
        <label class="stv-row">
          <span>Auto-read responses</span>
          <input type="checkbox" id="stv-auto" ${_prefs.autoSpeak ? 'checked' : ''} />
        </label>
        <label class="stv-row">
          <span>Voice</span>
          <select id="stv-voice-select" class="stv-select"></select>
        </label>
        <label class="stv-row">
          <span>Speed <span id="stv-rate-val">${_prefs.rate.toFixed(1)}×</span></span>
          <input type="range" id="stv-rate" min="0.5" max="2" step="0.1" value="${_prefs.rate}" />
        </label>
        <label class="stv-row">
          <span>Pitch <span id="stv-pitch-val">${_prefs.pitch.toFixed(1)}</span></span>
          <input type="range" id="stv-pitch" min="0.5" max="2" step="0.1" value="${_prefs.pitch}" />
        </label>
        <label class="stv-row">
          <span>Volume <span id="stv-vol-val">${Math.round(_prefs.volume * 100)}%</span></span>
          <input type="range" id="stv-vol" min="0" max="1" step="0.05" value="${_prefs.volume}" />
        </label>
        <div class="stv-row stv-test-row">
          <button id="stv-test-btn" class="stv-test-speak-btn" type="button">🔊 Test voice</button>
        </div>
      </div>
    `;

    document.body.appendChild(panel);
    _populateVoiceSelect();
    speechSynthesis.onvoiceschanged = () => { _loadVoices(); _populateVoiceSelect(); };

    document.getElementById('stv-close-settings').addEventListener('click', closeSettings);
    document.getElementById('stv-enabled').addEventListener('change', e => { _prefs.enabled = e.target.checked; _savePrefs(); if (!_prefs.enabled) stop(); });
    document.getElementById('stv-auto').addEventListener('change',    e => { _prefs.autoSpeak = e.target.checked; _savePrefs(); });
    document.getElementById('stv-voice-select').addEventListener('change', e => { _prefs.voiceName = e.target.value; _savePrefs(); });
    document.getElementById('stv-rate').addEventListener('input',  e => { _prefs.rate  = parseFloat(e.target.value); document.getElementById('stv-rate-val').textContent  = _prefs.rate.toFixed(1)+'×'; _savePrefs(); });
    document.getElementById('stv-pitch').addEventListener('input', e => { _prefs.pitch = parseFloat(e.target.value); document.getElementById('stv-pitch-val').textContent = _prefs.pitch.toFixed(1);     _savePrefs(); });
    document.getElementById('stv-vol').addEventListener('input',   e => { _prefs.volume= parseFloat(e.target.value); document.getElementById('stv-vol-val').textContent   = Math.round(_prefs.volume*100)+'%'; _savePrefs(); });
    document.getElementById('stv-test-btn').addEventListener('click', () => {
      const h = new Date().getHours();
      const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
      speak(`${g}! I am Sir. Tega, your Python and AI tutor. Ask me anything!`);
    });

    document.addEventListener('click', (e) => {
      if (_settingsOpen && !panel.contains(e.target) && !e.target.closest('#stv-settings-trigger')) {
        closeSettings();
      }
    }, true);
  }

  function _populateVoiceSelect() {
    const sel = document.getElementById('stv-voice-select');
    if (!sel) return;
    const voices = speechSynthesis.getVoices();
    const enVoices = voices.filter(v => v.lang.startsWith('en'));
    const otherVoices = voices.filter(v => !v.lang.startsWith('en'));
    sel.innerHTML =
      '<option value="">Browser default</option>' +
      enVoices.map(v => `<option value="${v.name}" ${v.name === _prefs.voiceName ? 'selected' : ''}>${v.name} (${v.lang})</option>`).join('') +
      (otherVoices.length ? `<optgroup label="Other">${otherVoices.map(v => `<option value="${v.name}" ${v.name === _prefs.voiceName ? 'selected' : ''}>${v.name} (${v.lang})</option>`).join('')}</optgroup>` : '');
  }

  function openSettings()   { _buildSettingsPanel(); const p = document.getElementById('stv-settings-panel'); if (p) { p.style.display = 'block'; _settingsOpen = true; } }
  function closeSettings()  { const p = document.getElementById('stv-settings-panel'); if (p) { p.style.display = 'none'; _settingsOpen = false; } }
  function toggleSettings() { _settingsOpen ? closeSettings() : openSettings(); }

  /* ─── Settings trigger — small caret/chevron next to mic button ─────────── */
  function _buildSettingsTrigger() {
    // Look for the trigger element the chat HTML places next to #mic-btn
    // If it already exists (id="stv-settings-trigger"), wire it up
    const existing = document.getElementById('stv-settings-trigger');
    if (existing) { existing.addEventListener('click', toggleSettings); return; }

    // Otherwise create a tiny chevron pill right after the mic button
    const micBtn = _micBtn();
    if (!micBtn || !micBtn.parentNode) return;

    const trigger = document.createElement('button');
    trigger.id        = 'stv-settings-trigger';
    trigger.type      = 'button';
    trigger.title     = 'Voice settings';
    trigger.innerHTML = '⌄';
    trigger.setAttribute('aria-label', 'Open voice settings');
    trigger.style.cssText = [
      'background:transparent',
      'border:none',
      'color:var(--text-muted,#475569)',
      'font-size:0.9rem',
      'cursor:pointer',
      'padding:0 4px',
      'line-height:46px',
      'transition:color 0.18s',
      'flex-shrink:0',
    ].join(';');
    trigger.addEventListener('mouseenter', () => { trigger.style.color = 'var(--accent,#3b82f6)'; });
    trigger.addEventListener('mouseleave', () => { trigger.style.color = 'var(--text-muted,#475569)'; });
    trigger.addEventListener('click', toggleSettings);

    micBtn.parentNode.insertBefore(trigger, micBtn.nextSibling);
  }

  /* ─── Toast notification ──────────────────────────────────────────────── */
  function _showToast(msg, type = 'info') {
    let toast = document.getElementById('stv-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'stv-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className   = `stv-toast stv-toast-${type}`;
    toast.style.display = 'block';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.display = 'none'; }, 3200);
  }

  /* ─── CSS ─────────────────────────────────────────────────────────────── */
  function _injectStyles() {
    if (document.getElementById('stv-styles')) return;
    const s = document.createElement('style');
    s.id = 'stv-styles';
    s.textContent = `
      /* Speak button on AI message bubbles */
      .sir-tega-speak-btn.stv-btn {
        display:inline-flex;align-items:center;gap:4px;
        padding:3px 10px;margin-top:8px;font-size:.74rem;font-family:inherit;
        background:rgba(59,130,246,.1);color:#93c5fd;
        border:1px solid rgba(59,130,246,.25);border-radius:20px;
        cursor:pointer;transition:background .18s,transform .1s;user-select:none;
      }
      .sir-tega-speak-btn.stv-btn:hover { background:rgba(59,130,246,.2);transform:scale(1.04); }
      .sir-tega-speak-btn.stv-speaking  {
        background:rgba(239,68,68,.12);color:#fca5a5;border-color:rgba(239,68,68,.3);
        animation:stv-pulse 1.2s ease-in-out infinite;
      }
      @keyframes stv-pulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.3)}50%{box-shadow:0 0 0 6px rgba(239,68,68,0)}}

      /* Settings panel */
      .stv-settings-panel{
        position:fixed;bottom:80px;right:16px;width:294px;
        background:#0d1120;border:1px solid rgba(59,130,246,.22);
        border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.65);
        z-index:1001;font-family:-apple-system,'Inter',sans-serif;overflow:hidden;
      }
      .stv-settings-header{
        display:flex;justify-content:space-between;align-items:center;
        padding:11px 15px;background:rgba(37,99,235,.1);
        font-weight:600;font-size:.87rem;color:#93c5fd;
        border-bottom:1px solid rgba(59,130,246,.12);
      }
      .stv-close-btn{background:none;border:none;cursor:pointer;color:#64748b;font-size:.95rem;padding:0 2px;line-height:1;}
      .stv-close-btn:hover{color:#f87171;}
      .stv-settings-body{padding:13px 15px;display:flex;flex-direction:column;gap:11px;}
      .stv-row{display:flex;justify-content:space-between;align-items:center;font-size:.82rem;color:#cbd5e1;gap:10px;}
      .stv-row span{flex:1;}
      .stv-row input[type="range"]{flex:1.2;accent-color:#3b82f6;cursor:pointer;}
      .stv-row input[type="checkbox"]{width:17px;height:17px;cursor:pointer;accent-color:#3b82f6;}
      .stv-select{background:#111827;color:#e2e8f0;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:4px 6px;font-size:.78rem;flex:1.4;cursor:pointer;}
      .stv-test-row{justify-content:center;margin-top:3px;}
      .stv-test-speak-btn{background:rgba(59,130,246,.13);color:#93c5fd;border:1px solid rgba(59,130,246,.28);border-radius:8px;padding:6px 16px;font-size:.82rem;cursor:pointer;transition:background .15s;}
      .stv-test-speak-btn:hover{background:rgba(59,130,246,.26);}

      /* Toast */
      .stv-toast{
        position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
        padding:8px 18px;border-radius:22px;font-size:.82rem;
        z-index:2001;pointer-events:none;max-width:82vw;text-align:center;
        box-shadow:0 4px 14px rgba(0,0,0,.45);font-family:inherit;
      }
      .stv-toast-info{background:#1e3a5f;color:#93c5fd;border:1px solid #2563eb;}
      .stv-toast-warn{background:#422006;color:#fcd34d;border:1px solid #d97706;}
      .stv-toast-ok  {background:#064e3b;color:#6ee7b7;border:1px solid #059669;}
    `;
    document.head.appendChild(s);
  }

  /* ─── Init ────────────────────────────────────────────────────────────── */
  function init(options) {
    _apiBase = (options && options.apiBase) || location.origin;
    if (options && options.autoSpeak !== undefined) _prefs.autoSpeak = options.autoSpeak;
    _loadPrefs();
    _loadVoices();
    _injectStyles();
    _wireMicBtn();
    _buildSettingsTrigger();
    document.documentElement.setAttribute('data-sir-tega-voice', '1');
  }

  /* ─── Public API ──────────────────────────────────────────────────────── */
  global.SirTegaVoice = {
    init,
    speak,
    stop,
    toggle,
    toggleMic,
    openSettings,
    closeSettings,
    toggleSettings,
    attachSpeakButton,
    onNewResponse,
    isSupported:  () => 'speechSynthesis' in window,
    isSpeaking,
    isMicActive,
  };

}(window));
