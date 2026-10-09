import { useState, useEffect } from 'react';
import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

// ── Shared style helpers ────────────────────────────────────────────────────
const C = {
  bg:       '#07090f',
  surface:  '#0d1120',
  card:     '#111827',
  text:     '#f1f5f9',
  muted:    '#64748b',
  sub:      '#94a3b8',
  accent:   '#3b82f6',
  green:    '#10b981',
  blueText: '#93c5fd',
  gold:     '#fcd34d',
  codeTxt:  '#86efac',
  codePre:  '#e2e8f0',
};

const pre: React.CSSProperties = {
  background: C.card,
  border: '1px solid rgba(59,130,246,.2)',
  borderRadius: 10,
  padding: '18px 20px',
  overflowX: 'auto',
  margin: '10px 0 20px',
  fontSize: '.82rem',
  lineHeight: 1.65,
  color: C.codePre,
  fontFamily: "'Fira Code','Cascadia Code',monospace",
};

const h2: React.CSSProperties = {
  fontSize: '1.15rem',
  color: '#e2e8f0',
  margin: '32px 0 10px',
  paddingBottom: 6,
  borderBottom: '1px solid rgba(255,255,255,.07)',
};

const h3: React.CSSProperties = {
  fontSize: '.95rem',
  color: C.blueText,
  margin: '20px 0 8px',
};

const p: React.CSSProperties = { color: C.sub, marginBottom: 12, fontSize: '.9rem' };

function Tag({ variant }: { variant: 'new' | 'req' | 'opt' }) {
  const map = {
    new: { bg: 'rgba(16,185,129,.15)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,.3)', label: 'NEW' },
    req: { bg: 'rgba(239,68,68,.12)',  color: '#fca5a5', border: '1px solid rgba(239,68,68,.25)',  label: 'REQ' },
    opt: { bg: 'rgba(59,130,246,.12)', color: C.blueText, border: '1px solid rgba(59,130,246,.25)', label: 'OPT' },
  }[variant];
  return <span style={{ display: 'inline-block', padding: '2px 9px', borderRadius: 12, fontSize: '.72rem', fontWeight: 600, letterSpacing: '.04em', background: map.bg, color: map.color, border: map.border }}>{map.label}</span>;
}

function ApiRow({ method, path, desc, tag }: { method: 'POST' | 'GET'; path: string; desc: string; tag?: 'new' | 'req' | 'opt' }) {
  const isPost = method === 'POST';
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', margin: '6px 0' }}>
      <span style={{ fontSize: '.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: 6, background: isPost ? 'rgba(59,130,246,.15)' : 'rgba(16,185,129,.15)', color: isPost ? C.blueText : '#6ee7b7' }}>{method}</span>
      <span style={{ fontFamily: 'monospace', fontSize: '.85rem', color: '#e2e8f0' }}>{path}</span>
      <span style={{ color: C.sub, fontSize: '.82rem' }}>— {desc} {tag && <Tag variant={tag} />}</span>
    </div>
  );
}

function FlowStep({ num, children }: { num: number; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, margin: '8px 0', color: C.sub }}>
      <div style={{ background: 'rgba(59,130,246,.2)', color: C.blueText, borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.72rem', fontWeight: 700, flexShrink: 0, marginTop: 2 }}>{num}</div>
      <span>{children}</span>
    </div>
  );
}

export default function VoiceGuidePage() {
  const [demoStatus, setDemoStatus] = useState('');
  const [demoBtnTxt, setDemoBtnTxt] = useState('🔊 Hear Sir. Tega (Gemini)');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioEl,    setAudioEl]    = useState<HTMLAudioElement | null>(null);

  // Inject voice.js script once
  useEffect(() => {
    const id = 'sir-tega-voice-script';
    if (document.getElementById(id)) return;
    const s = document.createElement('script');
    s.id  = id;
    s.src = `${API}/static/voice.js`;
    document.body.appendChild(s);
  }, []);

  async function demoSpeak() {
    // If already speaking, stop
    if (isSpeaking) {
      audioEl?.pause();
      setAudioEl(null);
      setIsSpeaking(false);
      setDemoBtnTxt('🔊 Hear Sir. Tega (Gemini)');
      setDemoStatus('');
      return;
    }

    const h   = new Date().getHours();
    const tod = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening';
    const msg = `Good ${tod}! I am Sir. Tega, your personal Python and AI tutor, now powered by Google Gemini. I can hear your voice, understand your questions, and speak back to you in real time. Ask me anything about Python, data science, or machine learning — let us start learning together!`;

    setDemoBtnTxt('⏹ Stop'); setDemoStatus('Generating Gemini audio…');

    try {
      const r = await fetch(`${API}/tts/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: msg, voice: 'Aoede' }),
      });
      const d = await r.json() as { audio_b64?: string; tts_error?: string };
      if (!d.audio_b64) throw new Error(d.tts_error || 'No audio returned');
      const audio = new Audio('data:audio/wav;base64,' + d.audio_b64);
      setAudioEl(audio); setIsSpeaking(true); setDemoStatus('Sir. Tega is speaking…');
      audio.onended = () => { setIsSpeaking(false); setDemoBtnTxt('🔊 Hear Sir. Tega (Gemini)'); setDemoStatus(''); };
      audio.play();
    } catch (e: unknown) {
      setDemoStatus('Error: ' + (e instanceof Error ? e.message : 'Could not load audio.'));
      setIsSpeaking(false); setDemoBtnTxt('🔊 Hear Sir. Tega (Gemini)');
    }
  }

  return (
    <div style={{ background: C.bg, color: C.text, minHeight: '100vh', padding: '40px 20px', maxWidth: 860, margin: '0 auto', fontFamily: "'Inter',-apple-system,BlinkMacSystemFont,sans-serif", lineHeight: 1.7 }}>

      <h1 style={{ fontSize: '1.7rem', color: C.blueText, marginBottom: 6 }}>🎙 Sir. Tega Voice — Gemini Integration Guide</h1>
      <p style={{ ...p, color: C.muted, marginBottom: 4 }}>Powered by <strong style={{ color: '#6ee7b7' }}>Google Gemini</strong> — full end-to-end voice pipeline.</p>
      <p style={{ fontSize: '.78rem', color: '#4a5568', marginBottom: 32 }}>Updated: October 2026</p>

      {/* ── How it works ── */}
      <h2 style={h2}>How it works</h2>
      <div style={{ background: C.card, border: '1px solid rgba(59,130,246,.18)', borderRadius: 12, padding: '20px 24px', margin: '16px 0', fontSize: '.88rem' }}>
        <FlowStep num={1}><strong style={{ color: '#e2e8f0' }}>Student taps 🎤</strong> — MediaRecorder captures microphone audio (WebM/Opus)</FlowStep>
        <div style={{ color: 'rgba(59,130,246,.4)', textAlign: 'center', margin: '2px 0 2px 30px' }}>↓</div>
        <FlowStep num={2}>Audio blob → base64 → <code>POST /voice/chat</code> with JWT auth</FlowStep>
        <div style={{ color: 'rgba(59,130,246,.4)', textAlign: 'center', margin: '2px 0 2px 30px' }}>↓</div>
        <FlowStep num={3}><strong style={{ color: '#6ee7b7' }}>Gemini STT</strong> (<code>gemini-2.0-flash</code>) — transcribes speech to text</FlowStep>
        <div style={{ color: 'rgba(59,130,246,.4)', textAlign: 'center', margin: '2px 0 2px 30px' }}>↓</div>
        <FlowStep num={4}><strong style={{ color: C.blueText }}>Sir. Tega LLM</strong> (Groq → Gemini cascade) — generates reply</FlowStep>
        <div style={{ color: 'rgba(59,130,246,.4)', textAlign: 'center', margin: '2px 0 2px 30px' }}>↓</div>
        <FlowStep num={5}><strong style={{ color: C.gold }}>Gemini TTS</strong> (<code>gemini-2.5-flash-preview-tts</code>) — synthesises natural audio</FlowStep>
        <div style={{ color: 'rgba(59,130,246,.4)', textAlign: 'center', margin: '2px 0 2px 30px' }}>↓</div>
        <FlowStep num={6}>Base64 WAV returned → browser plays audio, transcript + reply shown in chat</FlowStep>
      </div>

      <div style={{ background: 'rgba(251,191,36,.07)', borderLeft: '3px solid #f59e0b', borderRadius: '0 8px 8px 0', padding: '12px 16px', margin: '12px 0', fontSize: '.84rem', color: C.gold }}>
        ⚡ <strong>Fallback:</strong> If Gemini TTS fails, browser Web Speech API is used. If Gemini STT fails, user can still type. The voice feature always degrades gracefully.
      </div>

      {/* ── Backend endpoints ── */}
      <h2 style={h2}>Backend endpoints</h2>
      <ApiRow method="POST" path="/voice/chat"  desc="full pipeline: audio in → transcript + WAV audio out" tag="new" />
      <ApiRow method="POST" path="/tts/speak"   desc="text → Gemini TTS → WAV audio (for 🔊 Listen button)" tag="new" />
      <ApiRow method="POST" path="/tts/prepare" desc="strip markdown, return clean speakable text (browser TTS helper)" />

      <h3 style={h3}>POST /voice/chat — Request</h3>
      <pre style={pre}>{`POST /voice/chat
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "audio_b64":  "<base64-encoded WebM audio>",  // required
  "mime_type":  "audio/webm",                   // optional
  "learner_id": "e_xxxxx",                      // optional
  "level":      "beginner",                     // optional
  "voice":      "Aoede"                         // optional Gemini TTS voice
}

// Response:
{
  "transcript":  "What is a list in Python?",
  "reply_text":  "A list in Python is an ordered...",
  "audio_b64":   "<base64 WAV>",
  "mime_type":   "audio/wav"
}`}</pre>

      <h3 style={h3}>POST /tts/speak — Request</h3>
      <pre style={pre}>{`POST /tts/speak
Authorization: Bearer <jwt>
Content-Type: application/json

{ "text": "A list in Python is...", "voice": "Aoede" }

// Response:
{ "audio_b64": "<base64 WAV>", "mime_type": "audio/wav", "char_count": 42 }`}</pre>

      <h3 style={h3}>Available Gemini TTS voices</h3>
      <pre style={pre}>{`Aoede   — warm, clear female (recommended — default)
Kore    — expressive female
Charon  — deep male
Puck    — energetic male
Fenrir  — bold male
Leda    — bright female
Orus    — neutral male
Zephyr  — light, airy`}</pre>

      {/* ── Integration steps ── */}
      <h2 style={h2}>Step 1 — Load the script</h2>
      <pre style={pre}>{`<script src="https://mypytutor.onrender.com/static/voice.js"></script>`}</pre>

      <h2 style={h2}>Step 2 — Initialise</h2>
      <pre style={pre}>{`SirTegaVoice.init({
  apiBase:   'https://mypytutor.onrender.com',
  level:     'beginner',
  voice:     'Aoede',
  autoSpeak: false,

  onReply: function(transcript, replyText) {
    appendChatBubble('user',      transcript);
    appendChatBubble('assistant', replyText);
  },
});`}</pre>

      <h2 style={h2}>Step 3 — Wire 🔊 buttons to AI message bubbles</h2>
      <pre style={pre}>{`// After rendering an AI response bubble:
const bubble = document.createElement('div');
bubble.className = 'message assistant';
bubble.innerHTML = marked.parse(responseText);
chatContainer.appendChild(bubble);

SirTegaVoice.onNewResponse(bubble, responseText);`}</pre>

      <h2 style={h2}>Full public API</h2>
      <pre style={pre}>{`SirTegaVoice.init(options)             // initialise (call once)
SirTegaVoice.toggleMic()              // start/stop recording
SirTegaVoice.isMicActive()            // → true while recording
SirTegaVoice.isProcessing()           // → true while Gemini is working
SirTegaVoice.isPlaying()              // → true while audio plays
SirTegaVoice.stopPlayback()           // stop any current audio
SirTegaVoice.speak(text)              // Gemini TTS (fallback: browser TTS)
SirTegaVoice.stop()                   // stop speech
SirTegaVoice.isSpeaking()             // → boolean
SirTegaVoice.onNewResponse(el, text)  // attach 🔊 button + auto-speak
SirTegaVoice.attachSpeakButton(el, text)
SirTegaVoice.openSettings()
SirTegaVoice.closeSettings()
SirTegaVoice.toggleSettings()
SirTegaVoice._onReply = function(transcript, replyText) { ... }
SirTegaVoice.isSupported()            // → boolean (needs MediaRecorder)`}</pre>

      <h2 style={h2}>Browser support</h2>
      <ul style={{ marginLeft: 20, marginBottom: 12 }}>
        {[
          ['✓', 'Chrome / Edge / Brave — full Gemini voice pipeline'],
          ['✓', 'Safari 14.1+ (macOS / iOS) — works via MediaRecorder + Gemini'],
          ['✓', 'Android Chrome — full pipeline'],
          ['✓', 'Firefox — MediaRecorder works; Gemini pipeline fully supported'],
          ['⚠', 'Very old browsers (pre-2020) — mic button hidden automatically'],
        ].map(([sym, text]) => (
          <li key={text} style={{ color: C.sub, fontSize: '.88rem', marginBottom: 4 }}>
            <span style={{ color: sym === '✓' ? C.green : C.gold }}>{sym}</span> {text}
          </li>
        ))}
      </ul>

      {/* ── Live demo ── */}
      <h2 style={h2}>Live demo</h2>
      <p style={p}>Click below to hear Sir. Tega introduce himself via Gemini TTS:</p>
      <button onClick={demoSpeak}
        style={{ background: 'rgba(59,130,246,.15)', color: C.blueText, border: '1px solid rgba(59,130,246,.3)', borderRadius: 8, padding: '10px 20px', fontSize: '.9rem', cursor: 'pointer', marginBottom: 8, fontFamily: 'inherit' }}>
        {demoBtnTxt}
      </button>
      {demoStatus && <div style={{ fontSize: '.8rem', color: C.muted, marginTop: 6 }}>{demoStatus}</div>}

    </div>
  );
}
