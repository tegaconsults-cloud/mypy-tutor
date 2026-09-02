/**
 * SirTegaVoice — Voice feature for MyPy Tutor
 * ============================================
 * Provides:
 *   1. Text-to-Speech (TTS)  — Sir. Tega reads responses aloud
 *   2. Speech-to-Text (STT)  — user speaks questions into the chat input
 *   3. Voice settings panel  — voice picker, speed, pitch, auto-speak toggle
 *
 * Usage (include once in your HTML, after the page has loaded):
 *   <script src="/static/voice.js"></script>
 *
 * Then attach to your chat UI by calling:
 *   SirTegaVoice.init({
 *     apiBase:        'https://mypytutor.onrender.com', // or window.location.origin
 *     inputSelector:  '#chat-input',                   // your message input field
 *     micBtnId:       'voice-mic-btn',                 // mic button id (created if missing)
 *     speakBtnClass:  'sir-tega-speak-btn',            // class added to every speak button
 *     autoSpeak:      false,                           // auto-read AI responses?
 *   });
 *
 * To speak a message programmatically:
 *   SirTegaVoice.speak(text);
 *
 * To stop speaking:
 *   SirTegaVoice.stop();
 */

(function (global) {
  'use strict';

  /* ─── Constants ─────────────────────────────────────────────────────────── */
  const STORAGE_KEY   = 'mpt_voice_prefs';
  const API_TIMEOUT   = 8000;   // ms before TTS prepare request times out
  const MAX_CHUNK_LEN = 200;    // chars per utterance chunk (avoids iOS 15 cut-off bug)

  /* ─── State ──────────────────────────────────────────────────────────────── */
  let _cfg = {
    apiBase:       '',
    inputSelector: '#chat-input',
    micBtnId:      'voice-mic-btn',
    speakBtnClass: 'sir-tega-speak-btn',
    autoSpeak:     false,
  };

  let _prefs = {
    enabled:   true,   // TTS on/off master switch
    autoSpeak: false,  // auto-read every AI response
    rate:      1.0,    // speech rate  (0.5 – 2.0)
    pitch:     1.0,    // speech pitch (0.5 – 2.0)
    voiceName: '',     // '' = browser default
    volume:    1.0,    // 0 – 1
  };

  let _voices       = [];   // available voices, populated async
  let _speaking     = false;
  let _recognising  = false;
  let _recognition  = null;
  let _utterances   = [];   // queue of SpeechSynthesisUtterance objects
  let _settingsOpen = false;

  /* ─── Persistence ────────────────────────────────────────────────────────── */
  function _loadPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) Object.assign(_prefs, JSON.parse(raw));
    } catch (_) {}
    _prefs.autoSpeak = _cfg.autoSpeak || _prefs.autoSpeak;
  }

  function _savePrefs() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_prefs)); } catch (_) {}
  }

  /* ─── Voice loader ───────────────────────────────────────────────────────── */
  function _loadVoices() {
    if (!('speechSynthesis' in window)) return;
    const load = () => {
      _voices = speechSynthesis.getVoices();
    };
    load();
    speechSynthesis.onvoiceschanged = load;
  }

  function _pickVoice() {
    if (!_voices.length) return null;
    if (_prefs.voiceName) {
      const match = _voices.find(v => v.name === _prefs.voiceName);
      if (match) return match;
    }
    // Prefer: Nigerian English > any English (en-NG, en-GB, en-US) > first
    const preferred = ['en-NG', 'en-GB', 'en-US', 'en-AU'];
    for (const lang of preferred) {
      const v = _voices.find(v => v.lang.startsWith(lang));
      if (v) return v;
    }
    return _voices.find(v => v.lang.startsWith('en')) || _voices[0];
  }

  /* ─── Text cleaning (client-side fast path, server call for long text) ───── */
  function _cleanText(raw) {
    return raw
      .replace(/```[\s\S]*?```/g, ' code block. ')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[>\-•*+]\s/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]{2,}/g, ' ')
      .trim();
  }

  /* Split long text into sentence-sized chunks to work around browser TTS bugs */
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

  /* ─── TTS Core ───────────────────────────────────────────────────────────── */
  async function _prepareText(rawText) {
    // Short text: clean client-side (avoids network round-trip)
    if (rawText.length < 800) return _cleanText(rawText);

    // Long text: ask backend to clean (handles edge cases)
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), API_TIMEOUT);
      const res = await fetch(`${_cfg.apiBase}/tts/prepare`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ text: rawText }),
        signal:  controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        return data.text || _cleanText(rawText);
      }
    } catch (_) { /* fall through */ }
    return _cleanText(rawText);
  }

  function _stopAll() {
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    _utterances = [];
    _speaking   = false;
    _updateSpeakButtons(false);
  }

  async function speak(rawText) {
    if (!('speechSynthesis' in window) || !_prefs.enabled) return;
    if (!rawText || !rawText.trim()) return;

    _stopAll();
    _speaking = true;
    _updateSpeakButtons(true);

    const cleaned = await _prepareText(rawText);
    const chunks  = _chunkText(cleaned);

    const voice = _pickVoice();
    let idx = 0;

    function speakChunk() {
      if (idx >= chunks.length) {
        _speaking = false;
        _updateSpeakButtons(false);
        return;
      }
      const utt = new SpeechSynthesisUtterance(chunks[idx]);
      utt.rate   = _prefs.rate;
      utt.pitch  = _prefs.pitch;
      utt.volume = _prefs.volume;
      if (voice) utt.voice = voice;

      utt.onend = () => {
        idx++;
        speakChunk();
      };
      utt.onerror = (e) => {
        // 'interrupted' fires when we cancel mid-speech — not a real error
        if (e.error !== 'interrupted') {
          console.warn('[SirTegaVoice] utterance error:', e.error);
        }
        _speaking = false;
        _updateSpeakButtons(false);
      };

      _utterances.push(utt);
      speechSynthesis.speak(utt);
    }

    speakChunk();
  }

  function stop() {
    _stopAll();
  }

  function toggle(rawText) {
    if (_speaking) {
      stop();
    } else {
      speak(rawText);
    }
  }

  /* ─── Button state sync ──────────────────────────────────────────────────── */
  function _updateSpeakButtons(isSpeaking) {
    document.querySelectorAll(`.${_cfg.speakBtnClass}`).forEach(btn => {
      btn.dataset.speaking = isSpeaking ? '1' : '0';
      // Update icon/label if the button uses them
      const icon = btn.querySelector('.stv-icon');
      if (icon) icon.textContent = isSpeaking ? '⏹' : '🔊';
      const label = btn.querySelector('.stv-label');
      if (label) label.textContent = isSpeaking ? 'Stop' : 'Listen';
      if (isSpeaking) {
        btn.classList.add('stv-speaking');
        btn.title = 'Stop speaking';
      } else {
        btn.classList.remove('stv-speaking');
        btn.title = 'Listen to this response';
      }
    });
  }

  /**
   * Create a speak button and attach it to a DOM element containing an AI response.
   * Call this every time a new AI message is added to the chat.
   *
   * @param {HTMLElement} container  The message bubble / card element
   * @param {string}      text       The raw AI response text (markdown OK)
   */
  function attachSpeakButton(container, text) {
    if (!('speechSynthesis' in window)) return;
    if (container.querySelector(`.${_cfg.speakBtnClass}`)) return; // already attached

    const btn = document.createElement('button');
    btn.className = `${_cfg.speakBtnClass} stv-btn`;
    btn.dataset.speaking = '0';
    btn.title = 'Listen to this response';
    btn.innerHTML = `<span class="stv-icon">🔊</span><span class="stv-label">Listen</span>`;
    btn.setAttribute('aria-label', 'Listen to this response');
    btn.setAttribute('type', 'button');

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Stop all other speak buttons first
      document.querySelectorAll(`.${_cfg.speakBtnClass}`).forEach(b => {
        if (b !== btn) { b.dataset.speaking = '0'; b.classList.remove('stv-speaking'); }
      });
      toggle(text);
    });

    container.appendChild(btn);
  }

  /* ─── Speech Recognition (STT) ───────────────────────────────────────────── */
  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition ||
    null;

  function _buildMicButton() {
    const existingBtn = document.getElementById(_cfg.micBtnId);
    if (existingBtn) return existingBtn;

    const input = document.querySelector(_cfg.inputSelector);
    if (!input || !SpeechRecognition) return null;

    const btn = document.createElement('button');
    btn.id        = _cfg.micBtnId;
    btn.type      = 'button';
    btn.className = 'stv-mic-btn';
    btn.title     = 'Speak your question';
    btn.innerHTML = '🎤';
    btn.setAttribute('aria-label', 'Voice input — click to speak');

    // Insert mic button next to the input field
    if (input.parentNode) {
      input.parentNode.insertBefore(btn, input.nextSibling);
    }

    btn.addEventListener('click', toggleMic);
    return btn;
  }

  function toggleMic() {
    if (!SpeechRecognition) {
      _showToast('Voice input is not supported in this browser.', 'warn');
      return;
    }
    if (_recognising) {
      _recognition && _recognition.stop();
      return;
    }
    _startMic();
  }

  function _startMic() {
    const input = document.querySelector(_cfg.inputSelector);
    if (!input) return;

    _recognition = new SpeechRecognition();
    _recognition.lang            = 'en-NG'; // Nigerian English first
    _recognition.continuous      = false;
    _recognition.interimResults  = true;
    _recognition.maxAlternatives = 1;

    const micBtn = document.getElementById(_cfg.micBtnId);

    _recognition.onstart = () => {
      _recognising = true;
      if (micBtn) { micBtn.classList.add('stv-listening'); micBtn.innerHTML = '🔴'; micBtn.title = 'Listening… click to stop'; }
      _showToast('Listening… speak your question', 'info');
    };

    _recognition.onresult = (e) => {
      let interim = '';
      let final   = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t;
        else interim += t;
      }
      // Show interim results in the input as a preview
      input.value = final || interim;
      // Trigger input event so any framework / char counter updates
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };

    _recognition.onend = () => {
      _recognising = false;
      if (micBtn) { micBtn.classList.remove('stv-listening'); micBtn.innerHTML = '🎤'; micBtn.title = 'Speak your question'; }
      // If input has text, focus it so user can review / edit before sending
      const val = input.value.trim();
      if (val) {
        input.focus();
        input.setSelectionRange(val.length, val.length);
      }
    };

    _recognition.onerror = (e) => {
      _recognising = false;
      if (micBtn) { micBtn.classList.remove('stv-listening'); micBtn.innerHTML = '🎤'; }
      const msgs = {
        'not-allowed':      'Microphone access was denied. Please allow microphone in browser settings.',
        'no-speech':        'No speech detected. Please try again.',
        'audio-capture':    'No microphone found. Please connect a microphone.',
        'network':          'Network error during speech recognition. Check your connection.',
        'aborted':          '', // user stopped — silent
      };
      const msg = msgs[e.error] || `Speech error: ${e.error}`;
      if (msg) _showToast(msg, 'warn');
    };

    try {
      _recognition.start();
    } catch (err) {
      console.warn('[SirTegaVoice] mic start error:', err);
    }
  }

  /* ─── Settings Panel ─────────────────────────────────────────────────────── */
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
        <button class="stv-close-btn" id="stv-close-settings" aria-label="Close voice settings">✕</button>
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
          <input type="range" id="stv-rate" min="0.5" max="2.0" step="0.1" value="${_prefs.rate}" />
        </label>
        <label class="stv-row">
          <span>Pitch <span id="stv-pitch-val">${_prefs.pitch.toFixed(1)}</span></span>
          <input type="range" id="stv-pitch" min="0.5" max="2.0" step="0.1" value="${_prefs.pitch}" />
        </label>
        <label class="stv-row">
          <span>Volume <span id="stv-vol-val">${Math.round(_prefs.volume * 100)}%</span></span>
          <input type="range" id="stv-vol" min="0" max="1" step="0.05" value="${_prefs.volume}" />
        </label>
        <div class="stv-row stv-test-row">
          <button id="stv-test-btn" class="stv-btn stv-test-speak-btn" type="button">
            🔊 Test voice
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(panel);

    // Populate voice selector
    _populateVoiceSelect();
    speechSynthesis.onvoiceschanged = () => { _loadVoices(); _populateVoiceSelect(); };

    // Event listeners
    document.getElementById('stv-close-settings').addEventListener('click', closeSettings);
    document.getElementById('stv-enabled').addEventListener('change', e => {
      _prefs.enabled = e.target.checked; _savePrefs();
      if (!_prefs.enabled) stop();
    });
    document.getElementById('stv-auto').addEventListener('change', e => {
      _prefs.autoSpeak = e.target.checked; _savePrefs();
    });
    document.getElementById('stv-voice-select').addEventListener('change', e => {
      _prefs.voiceName = e.target.value; _savePrefs();
    });
    document.getElementById('stv-rate').addEventListener('input', e => {
      _prefs.rate = parseFloat(e.target.value);
      document.getElementById('stv-rate-val').textContent = _prefs.rate.toFixed(1) + '×';
      _savePrefs();
    });
    document.getElementById('stv-pitch').addEventListener('input', e => {
      _prefs.pitch = parseFloat(e.target.value);
      document.getElementById('stv-pitch-val').textContent = _prefs.pitch.toFixed(1);
      _savePrefs();
    });
    document.getElementById('stv-vol').addEventListener('input', e => {
      _prefs.volume = parseFloat(e.target.value);
      document.getElementById('stv-vol-val').textContent = Math.round(_prefs.volume * 100) + '%';
      _savePrefs();
    });
    document.getElementById('stv-test-btn').addEventListener('click', () => {
      const hour = new Date().getHours();
      const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
      speak(`${greeting}! I am Sir. Tega, your Python tutor. How can I help you learn today?`);
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
      if (_settingsOpen && !panel.contains(e.target) && !e.target.closest('#stv-settings-btn')) {
        closeSettings();
      }
    }, true);
  }

  function _populateVoiceSelect() {
    const sel = document.getElementById('stv-voice-select');
    if (!sel) return;
    const current = _prefs.voiceName;
    const voices  = speechSynthesis.getVoices();
    sel.innerHTML = '<option value="">Browser default</option>' +
      voices
        .filter(v => v.lang.startsWith('en'))
        .map(v => `<option value="${v.name}" ${v.name === current ? 'selected' : ''}>${v.name} (${v.lang})</option>`)
        .join('');
    // Also add all other languages (collapsed)
    const others = voices.filter(v => !v.lang.startsWith('en'));
    if (others.length) {
      sel.innerHTML += '<optgroup label="Other languages">' +
        others.map(v => `<option value="${v.name}" ${v.name === current ? 'selected' : ''}>${v.name} (${v.lang})</option>`).join('') +
        '</optgroup>';
    }
  }

  function openSettings() {
    _buildSettingsPanel();
    const panel = document.getElementById('stv-settings-panel');
    if (panel) { panel.style.display = 'block'; _settingsOpen = true; }
  }

  function closeSettings() {
    const panel = document.getElementById('stv-settings-panel');
    if (panel) { panel.style.display = 'none'; _settingsOpen = false; }
  }

  function toggleSettings() {
    _settingsOpen ? closeSettings() : openSettings();
  }

  /* ─── Settings button (floating) ────────────────────────────────────────── */
  function _buildSettingsButton() {
    if (document.getElementById('stv-settings-btn')) return;
    if (!('speechSynthesis' in window)) return;

    const btn = document.createElement('button');
    btn.id        = 'stv-settings-btn';
    btn.className = 'stv-settings-trigger';
    btn.type      = 'button';
    btn.title     = 'Voice settings';
    btn.innerHTML = '🎙';
    btn.setAttribute('aria-label', 'Open voice settings');
    btn.addEventListener('click', toggleSettings);
    document.body.appendChild(btn);
  }

  /* ─── Toast notification ─────────────────────────────────────────────────── */
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
    toast._timer = setTimeout(() => { toast.style.display = 'none'; }, 3500);
  }

  /* ─── CSS injection ──────────────────────────────────────────────────────── */
  function _injectStyles() {
    if (document.getElementById('stv-styles')) return;
    const style = document.createElement('style');
    style.id = 'stv-styles';
    style.textContent = `
      /* ── Speak button on AI message bubbles ── */
      .sir-tega-speak-btn.stv-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        margin-top: 8px;
        font-size: .74rem;
        font-family: inherit;
        background: rgba(59,130,246,.12);
        color: #93c5fd;
        border: 1px solid rgba(59,130,246,.28);
        border-radius: 20px;
        cursor: pointer;
        transition: background .18s, transform .1s;
        user-select: none;
      }
      .sir-tega-speak-btn.stv-btn:hover {
        background: rgba(59,130,246,.22);
        transform: scale(1.04);
      }
      .sir-tega-speak-btn.stv-speaking {
        background: rgba(239,68,68,.15);
        color: #fca5a5;
        border-color: rgba(239,68,68,.35);
        animation: stv-pulse 1.2s ease-in-out infinite;
      }
      @keyframes stv-pulse {
        0%,100%{ box-shadow: 0 0 0 0 rgba(239,68,68,.3); }
        50%    { box-shadow: 0 0 0 6px rgba(239,68,68,.0); }
      }

      /* ── Mic button ── */
      .stv-mic-btn {
        padding: 6px 10px;
        font-size: 1.1rem;
        background: transparent;
        border: 1px solid rgba(255,255,255,.15);
        border-radius: 8px;
        cursor: pointer;
        color: #94a3b8;
        transition: color .15s, border-color .15s;
        line-height: 1;
      }
      .stv-mic-btn:hover { color: #60a5fa; border-color: rgba(96,165,250,.4); }
      .stv-mic-btn.stv-listening {
        color: #f87171;
        border-color: rgba(248,113,113,.5);
        animation: stv-pulse 0.8s ease-in-out infinite;
      }

      /* ── Floating settings trigger ── */
      #stv-settings-btn {
        position: fixed;
        bottom: 80px;
        right: 20px;
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background: rgba(17,24,39,.9);
        border: 1px solid rgba(59,130,246,.35);
        color: #93c5fd;
        font-size: 1.1rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,.4);
        transition: transform .15s, box-shadow .15s;
        z-index: 999;
      }
      #stv-settings-btn:hover { transform: scale(1.08); box-shadow: 0 6px 20px rgba(0,0,0,.5); }

      /* ── Settings panel ── */
      .stv-settings-panel {
        position: fixed;
        bottom: 132px;
        right: 20px;
        width: 300px;
        background: #0d1120;
        border: 1px solid rgba(59,130,246,.25);
        border-radius: 14px;
        box-shadow: 0 8px 32px rgba(0,0,0,.6);
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
        overflow: hidden;
      }
      .stv-settings-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: rgba(37,99,235,.12);
        font-weight: 600;
        font-size: .88rem;
        color: #93c5fd;
        border-bottom: 1px solid rgba(59,130,246,.15);
      }
      .stv-close-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: #64748b;
        font-size: 1rem;
        padding: 0 2px;
        line-height: 1;
      }
      .stv-close-btn:hover { color: #f87171; }
      .stv-settings-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
      .stv-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: .82rem;
        color: #cbd5e1;
        gap: 10px;
      }
      .stv-row span { flex: 1; }
      .stv-row input[type="range"] {
        flex: 1.2;
        accent-color: #3b82f6;
        cursor: pointer;
      }
      .stv-row input[type="checkbox"] {
        width: 18px; height: 18px; cursor: pointer; accent-color: #3b82f6;
      }
      .stv-select {
        background: #111827; color: #e2e8f0;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 6px; padding: 4px 6px;
        font-size: .78rem; flex: 1.5; cursor: pointer;
      }
      .stv-test-row { justify-content: center; margin-top: 4px; }
      .stv-test-speak-btn {
        background: rgba(59,130,246,.15);
        color: #93c5fd;
        border: 1px solid rgba(59,130,246,.3);
        border-radius: 8px;
        padding: 6px 16px;
        font-size: .82rem;
        cursor: pointer;
        transition: background .15s;
      }
      .stv-test-speak-btn:hover { background: rgba(59,130,246,.28); }

      /* ── Toast ── */
      .stv-toast {
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        padding: 9px 20px;
        border-radius: 24px;
        font-size: .83rem;
        font-family: inherit;
        z-index: 2000;
        pointer-events: none;
        max-width: 80vw;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,.4);
      }
      .stv-toast-info  { background: #1e3a5f; color: #93c5fd; border: 1px solid #2563eb; }
      .stv-toast-warn  { background: #422006; color: #fcd34d; border: 1px solid #d97706; }
      .stv-toast-ok    { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
    `;
    document.head.appendChild(style);
  }

  /* ─── Public API ─────────────────────────────────────────────────────────── */

  /**
   * Initialise the voice module. Call once after DOM is ready.
   * @param {object} options  See top-of-file docs for all options.
   */
  function init(options) {
    Object.assign(_cfg, options || {});
    _loadPrefs();
    _loadVoices();
    _injectStyles();
    _buildSettingsButton();
    _buildMicButton();

    // Mark that voice is available for the chat UI
    document.documentElement.setAttribute('data-sir-tega-voice', '1');
  }

  /**
   * Called by the chat UI whenever a new AI response arrives.
   * Attaches a speak button AND auto-speaks if the user enabled it.
   *
   * @param {HTMLElement} bubbleEl  The AI message DOM element
   * @param {string}      rawText   The raw AI response text
   */
  function onNewResponse(bubbleEl, rawText) {
    if (bubbleEl) attachSpeakButton(bubbleEl, rawText);
    if (_prefs.enabled && _prefs.autoSpeak) {
      // Small delay so the bubble is fully rendered
      setTimeout(() => speak(rawText), 300);
    }
  }

  // Expose on window
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
    isSupported: () => 'speechSynthesis' in window,
    isSpeaking:  () => _speaking,
    isMicActive: () => _recognising,
  };

}(window));
