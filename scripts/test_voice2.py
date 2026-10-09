"""Voice pipeline live test."""
import urllib.request, urllib.error, json, base64, struct, io, math, sys

BASE = "https://mypytutor.onrender.com"

def api(method, path, body=None, token=None, timeout=55):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {"error": str(e)}
    except Exception as ex:
        return 0, {"error": str(ex)}

def make_wav(silent=False, freq=440, sr=16000, dur_ms=1000):
    n = int(sr * dur_ms / 1000)
    if silent:
        pcm = b"\x00\x00" * n
    else:
        pcm = b"".join(struct.pack("<h", int(8000 * math.sin(2*math.pi*freq*i/sr)))
                       for i in range(n))
    buf = io.BytesIO()
    buf.write(b"RIFF"); buf.write(struct.pack("<I", 36+len(pcm)))
    buf.write(b"WAVE"); buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16)); buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<H", 1)); buf.write(struct.pack("<I", sr))
    buf.write(struct.pack("<I", sr*2)); buf.write(struct.pack("<H", 2))
    buf.write(struct.pack("<H", 16)); buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm))); buf.write(pcm)
    return buf.getvalue()

# ── 1. Auth ──────────────────────────────────────────────────────────────────
print("="*55 + "\n1. SIGNIN")
s, d = api("POST", "/auth/signin",
    {"email": "tegaconsults@gmail.com", "password": "tegaconsults@gmail.com"})
TOKEN  = d.get("token", "")
LEARNER = d.get("learner_id", "")
print("  status:", s, "  token:", bool(TOKEN), "  learner:", LEARNER)
if not TOKEN:
    print("ABORT: signin failed:", d); sys.exit(1)

# ── 2. TTS speak ─────────────────────────────────────────────────────────────
print("\n" + "="*55 + "\n2. POST /tts/speak — text to WAV audio")
s, d = api("POST", "/tts/speak",
    {"text": "Hello! I am Sir. Tega.", "voice": "Aoede"}, token=TOKEN)
print("  status:", s)
ab = d.get("audio_b64", "")
if ab:
    wav = base64.b64decode(ab)
    print("  audio_b64 len:", len(ab))
    print("  WAV bytes:", len(wav), " header:", wav[:4], " valid:", wav[:4] == b"RIFF")
    print("  char_count:", d.get("char_count"), " mime:", d.get("mime_type"))
else:
    print("  NO AUDIO — error:", str(d.get("detail", d.get("error", d)))[:150])

# ── 3. TTS speak no auth ─────────────────────────────────────────────────────
print("\n" + "="*55 + "\n3. POST /tts/speak — no auth token")
s, d = api("POST", "/tts/speak", {"text": "Hello", "voice": "Aoede"})
print("  status:", s, " audio:", bool(d.get("audio_b64")),
      " detail:", str(d.get("detail", ""))[:80])

# ── 4. /voice/chat — missing audio ───────────────────────────────────────────
print("\n" + "="*55 + "\n4. POST /voice/chat — missing audio_b64")
s, d = api("POST", "/voice/chat", {"mime_type": "audio/wav"}, token=TOKEN)
print("  status:", s, " detail:", str(d.get("detail", ""))[:80])

# ── 5. /voice/chat — silent WAV (should 422 on empty transcript) ─────────────
print("\n" + "="*55 + "\n5. POST /voice/chat — silent WAV (1 sec, no speech)")
b64 = base64.b64encode(make_wav(silent=True)).decode()
s, d = api("POST", "/voice/chat",
    {"audio_b64": b64, "mime_type": "audio/wav",
     "learner_id": LEARNER, "level": "beginner", "voice": "Aoede"},
    token=TOKEN, timeout=55)
print("  status:", s)
print("  transcript:", repr(str(d.get("transcript", ""))[:80]))
print("  detail:", str(d.get("detail", ""))[:80])

# ── 6. /voice/chat — tone WAV (Gemini should detect non-speech) ──────────────
print("\n" + "="*55 + "\n6. POST /voice/chat — 440Hz tone WAV")
b64 = base64.b64encode(make_wav(silent=False)).decode()
s, d = api("POST", "/voice/chat",
    {"audio_b64": b64, "mime_type": "audio/wav",
     "learner_id": LEARNER, "level": "beginner", "voice": "Aoede"},
    token=TOKEN, timeout=60)
print("  status:", s)
print("  transcript:", repr(str(d.get("transcript", ""))[:100]))
print("  reply_text:", str(d.get("reply_text", ""))[:100])
print("  audio_b64:", "present (" + str(len(d.get("audio_b64", ""))) + " chars)"
      if d.get("audio_b64") else "MISSING")
print("  detail:", str(d.get("detail", ""))[:100])

# ── 7. /voice/chat — no auth ─────────────────────────────────────────────────
print("\n" + "="*55 + "\n7. POST /voice/chat — no auth (should 401)")
s, d = api("POST", "/voice/chat",
    {"audio_b64": base64.b64encode(b"test").decode(), "mime_type": "audio/wav"})
print("  status:", s, " detail:", str(d.get("detail", ""))[:60])

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("DIAGNOSIS COMPLETE\n")
