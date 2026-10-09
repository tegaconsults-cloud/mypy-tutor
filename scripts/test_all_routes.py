"""
Comprehensive live test — all routes and page redirects.
Tests: auth, chat, quiz, assignment, payment, certificates,
       voice TTS, redirect routes, admin dashboard.
"""
import urllib.request, urllib.error, json, sys, base64

BASE   = "https://mypytutor.onrender.com"
FRONT  = "https://mypytutor.com.ng"

EMAIL  = "tegaconsults@gmail.com"
PASS   = "tegaconsults@gmail.com"

RESULTS = []

def req(method, path, body=None, token=None, admin_token=None,
        follow_redirects=False, timeout=30):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:       h["Authorization"]  = "Bearer " + token
    if admin_token: h["X-Admin-Token"]  = admin_token
    rq = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        # follow_redirects uses default opener; no-follow uses no_redirects
        if follow_redirects:
            with urllib.request.urlopen(rq, timeout=timeout) as r:
                ct = r.headers.get("Content-Type", "")
                raw = r.read()
                return r.status, r.url, json.loads(raw) if "json" in ct else {"_html": len(raw)}
        else:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
            opener.addheaders = list(h.items())
            class NoRedirect(urllib.request.HTTPErrorProcessor):
                def http_response(self, req, response):
                    return response
                https_response = http_response
            opener2 = urllib.request.build_opener(NoRedirect)
            for k, v in h.items():
                rq.add_unredirected_header(k, v)
            with opener2.open(rq, timeout=timeout) as r:
                ct = r.headers.get("Content-Type", "")
                raw = r.read()
                loc = r.headers.get("Location", "")
                return r.status, loc, json.loads(raw) if "json" in ct else {"_html": len(raw)}
    except urllib.error.HTTPError as e:
        try: return e.code, e.headers.get("Location",""), json.loads(e.read())
        except: return e.code, "", {}
    except Exception as ex:
        return 0, "", {"error": str(ex)}

def check(name, passed, note=""):
    sym = "PASS" if passed else "FAIL"
    RESULTS.append((sym, name, note))
    print(f"  [{sym}] {name}" + (f"  — {note}" if note else ""))

# ── 1. Auth ──────────────────────────────────────────────────────────────────
print("\n── AUTH ──────────────────────────────────────────────────────")
s, _, d = req("POST", "/auth/signin", {"email": EMAIL, "password": PASS})
TOKEN   = d.get("token", "")
LEARNER = d.get("learner_id", "")
check("POST /auth/signin",        s == 200 and bool(TOKEN), f"learner={LEARNER}")
check("JWT token returned",       bool(TOKEN))
check("learner_id returned",      bool(LEARNER))

s, _, d2 = req("GET", "/auth/me", token=TOKEN)
check("GET /auth/me",             s == 200 and d2.get("email") == EMAIL, d2.get("email",""))

# ── 2. Chat ───────────────────────────────────────────────────────────────────
print("\n── CHAT ──────────────────────────────────────────────────────")
s, _, d = req("POST", "/chat", {"message":"Say hello in 3 words.","learner_id":LEARNER,"level":"beginner","history":[]}, token=TOKEN)
check("POST /chat",               s == 200 and bool(d.get("content")) and not d.get("transient_error"),
      (d.get("content","")[:50] if d.get("content") else d.get("error","")[:50]))

# ── 3. Quiz ───────────────────────────────────────────────────────────────────
print("\n── QUIZ ──────────────────────────────────────────────────────")
s, _, d = req("POST", "/quiz/generate", {"learner_id":LEARNER,"topic":"Python lists","level":"beginner"}, token=TOKEN)
opts = d.get("options", [])
check("POST /quiz/generate",      s == 200 and len(opts) == 4, f"{len(opts)} options")
bad_opts = [o for o in opts if "```" in o]
check("Quiz options clean (no code fences)", len(bad_opts) == 0, f"{len(bad_opts)} bad")

if opts:
    q = d.get("question","")
    s, _, d2 = req("POST", "/quiz/answer", {"learner_id":LEARNER,"topic":"Python lists","level":"beginner","question":q,"answer":opts[0],"correct_answer":"A"}, token=TOKEN)
    exp = d2.get("explanation","")
    check("POST /quiz/answer",    s == 200 and bool(exp), exp[:60])
    check("Explanation clean",    not exp.startswith("CORRECT:"), exp[:40])

# ── 4. Assignment ──────────────────────────────────────────────────────────────
print("\n── ASSIGNMENT ────────────────────────────────────────────────")
s, _, d = req("POST", f"/assignments/generate?learner_id={LEARNER}&topic=Python+functions", token=TOKEN)
AID = d.get("assignment_id","")
check("POST /assignments/generate", s == 200 and bool(AID), AID)

if AID:
    s, _, d = req("GET", f"/assignments/{LEARNER}", token=TOKEN)
    check("GET /assignments/{learner_id}", s == 200, f"total={d.get('total')}")

    s, _, d = req("POST", f"/assignments/{AID}/submit", {"learner_id":LEARNER,"submission":"def add(a,b): return a+b"}, token=TOKEN)
    check("POST /assignments/{id}/submit", s == 200 and d.get("ok"))

# ── 5. Payment routes ──────────────────────────────────────────────────────────
print("\n── PAYMENT ROUTES ────────────────────────────────────────────")

# /payment should 302 → frontend
s, loc, _ = req("GET", "/payment?plan=tier1&amount=30000")
check("GET /payment redirects to frontend", s in (301,302) and "mypytutor.com.ng" in loc, f"{s} → {loc}")

# /terms should 302 → frontend
s, loc, _ = req("GET", "/terms")
check("GET /terms redirects to frontend",   s in (301,302) and "mypytutor.com.ng" in loc, f"{s} → {loc}")

# /privacy should 302 → frontend
s, loc, _ = req("GET", "/privacy")
check("GET /privacy redirects to frontend", s in (301,302) and "mypytutor.com.ng" in loc, f"{s} → {loc}")

# /payment/callback should serve success page
s, _, d = req("GET", "/payment/callback?reference=TEST123", follow_redirects=True)
check("GET /payment/callback",              s == 200, f"html_len={d.get('_html',0)}")

# Paystack initialize
s, _, d = req("POST", "/payments/paystack/initialize", {"learner_id":LEARNER,"amount_ngn":2000,"plan":"Prompt Starter Plan","course_name":"","coupon_code":""}, token=TOKEN)
check("POST /payments/paystack/initialize", s == 200 and bool(d.get("authorization_url")),
      (d.get("authorization_url","")[:60] if d.get("authorization_url") else d.get("error","")[:60]))

# Bank details
s, _, d = req("GET", "/payments/bank-details")
check("GET /payments/bank-details",         s == 200 and bool(d.get("account_number")), d.get("account_number",""))

# ── 6. TTS speak ──────────────────────────────────────────────────────────────
print("\n── VOICE / TTS ───────────────────────────────────────────────")
s, _, d = req("POST", "/tts/speak", {"text":"Hello from Sir Tega!","voice":"Aoede"}, token=TOKEN)
has_audio = bool(d.get("audio_b64",""))
tts_err   = d.get("tts_error","")
check("POST /tts/speak",                    s == 200, f"audio={has_audio} err={tts_err[:60] if tts_err else 'none'}")
if has_audio:
    wav = base64.b64decode(d["audio_b64"])
    check("TTS returns valid WAV",          wav[:4] == b"RIFF", f"header={wav[:4]}")

# ── 7. Certificate routes ──────────────────────────────────────────────────────
print("\n── CERTIFICATE ROUTES ────────────────────────────────────────")
s, _, d = req("GET", f"/certificate/basic?learner_id={LEARNER}&name=Test+User")
check("GET /certificate/basic",             s in (200, 402), f"status={s}")   # 402 = locked (expected for free tier)

# /verify with a known cert ID from earlier tests if any
s, _, d = req("GET", "/verify/TGA-4D8032D93E70")
check("GET /verify/{cert_id}",              s in (200, 404), f"status={s}")

# ── 8. Admin dashboard ────────────────────────────────────────────────────────
print("\n── ADMIN ─────────────────────────────────────────────────────")
with open(".env") as f:
    lines = f.read().splitlines()
apw = next((l.split("=",1)[1].strip() for l in lines if l.startswith("ADMIN_PASSWORD=")), "")
if apw:
    s, _, d = req("POST", "/admin/login", {"email":"tega.com.ng@gmail.com","password":apw})
    ATOK = d.get("token","")
    check("POST /admin/login",              s == 200 and bool(ATOK))
    if ATOK:
        s, _, d = req("GET", "/admin/dashboard", admin_token=ATOK, timeout=25)
        total = d.get("users",{}).get("total",0)
        check("GET /admin/dashboard",       s == 200 and total > 0, f"total_users={total} db_ok={d.get('db_ok')}")
else:
    check("Admin login",                    False, "ADMIN_PASSWORD not in .env (set on Render)")

# ── 9. Route integrity checks ──────────────────────────────────────────────────
print("\n── ROUTE INTEGRITY ───────────────────────────────────────────")
s, _, _ = req("GET", "/health")
check("GET /health",                        s == 200)

s, _, _ = req("GET", "/")
check("GET /",                              s == 200)

s, _, _ = req("GET", "/admin.html", follow_redirects=True)
check("GET /admin.html",                    s == 200)

s, _, _ = req("GET", "/voice", follow_redirects=True)
check("GET /voice (integration guide)",     s == 200)

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
passed = sum(1 for r in RESULTS if r[0] == "PASS")
failed = sum(1 for r in RESULTS if r[0] == "FAIL")
print(f"RESULT: {passed} passed  |  {failed} failed  |  {len(RESULTS)} total")
if failed:
    print("\nFailed tests:")
    for sym, name, note in RESULTS:
        if sym == "FAIL":
            print(f"  ✗ {name}  — {note}")
print()
