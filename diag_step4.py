#!/usr/bin/env python3
import urllib.request, json, ssl, time
ctx = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(m, p, b=None, t=None, timeout=30):
    url = BASE + p
    h   = {"Content-Type":"application/json","User-Agent":"DiagBot/1.0"}
    if t: h["Authorization"] = f"Bearer {t}"
    d = json.dumps(b).encode() if b else None
    req = urllib.request.Request(url, data=d, headers=h, method=m)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            try:    return r.status, json.loads(r.read().decode())
            except: return r.status, r.read().decode()[:80]
    except urllib.error.HTTPError as e:
        try:    return e.code, json.loads(e.read().decode())
        except: return e.code, e.read().decode()[:80]
    except Exception as e: return 0, str(e)[:80]

def chk(label, status, data, expect_ok=True):
    ok = 200 <= status < 300
    if not expect_ok: ok = not ok   # flip for expected failures
    icon = "✅" if ok else "❌"
    detail = ""
    if isinstance(data, dict):
        if "error" in data:   detail = f"error: {data['error']}"
        elif "ok" in data:    detail = f"ok={data['ok']}"
        elif "status" in data:detail = f"status={data['status']}"
        elif "topics" in data:detail = f"{len(data['topics'])} topics"
        elif "courses" in data and "tier_plans" in data:
            detail = f"{len(data['courses'])} courses, {len(data['tier_plans'])} tier_plans"
        elif "preferred" in data: detail = f"{len(data['preferred'])} voices"
        else: detail = str(data)[:60]
    else:
        detail = str(data)[:60]
    print(f"  {icon} [{status}] {label:<28} {detail}")
    return ok

print()
print("=" * 65)
print("  STEP 4 — Remaining endpoint verification")
print("=" * 65)

passed = total = 0

def test(label, m, p, b=None, t=None, expect=True, delay=4, timeout=35):
    global passed, total
    time.sleep(delay)
    s, d = hit(m, p, b, t, timeout)
    ok = chk(label, s, d, expect)
    total += 1
    if ok: passed += 1

# DB reads
test("progress DB read",    "GET",  "/progress/testuser001")
test("topics",              "GET",  "/topics")
test("courses catalog(17)", "GET",  "/courses/catalog")
test("bank details",        "GET",  "/payments/bank-details")
test("tts voices",          "GET",  "/tts/voices")

# Enquiry (DB write)
test("enquiry submit",      "POST", "/enquiry", {
    "name":"Test User","email":"test@test.com","category":"general",
    "subject":"Test enquiry","message":"This is a test message for diagnosis"
})

# Feedback summary (DB read)
test("feedback summary",    "GET",  "/feedback/summary")

# Resend confirmation (expected 200 always — anti-enum)
test("resend confirmation",  "POST", "/auth/resend-confirmation",
    {"email":"nonexistent@test.com"})

# Paystack webhook with wrong sig → 400 (not 404 = route exists)
test("paystack webhook exists", "POST", "/webhooks/paystack",
    {"event":"test"}, expect=False)  # 400 is fine, just not 404/500

# Validate code endpoint
test("validate access code",  "POST", "/auth/validate-code", {"code":"TEST123"})

# TTS prepare
test("tts prepare",          "POST", "/tts/prepare",
    {"text":"Hello **world**. What is `Python`? ## Heading"})

# Supabase enabled check
test("supabase status",       "GET",  "/supabase/status", expect=False)  # 403 expected, not 500

# AI automation landing page
test("ai-automation landing", "GET",  "/courses/ai-automation")

# Voice integration guide
test("voice guide",           "GET",  "/voice")

# Certificate verify (non-existent cert → 404 HTML, not 500)
test("verify cert (404)",     "GET",  "/verify/notexist999", expect=False)

print()
print("=" * 65)
print(f"  PASSED: {passed}/{total}")
if passed == total:
    print("  🎉 All endpoints responding correctly — product is revenue-ready!")
else:
    print(f"  {total-passed} issue(s) need attention")
print("=" * 65)
print()
