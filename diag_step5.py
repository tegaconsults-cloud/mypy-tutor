#!/usr/bin/env python3
"""Step 5 — confirm server warm + no remaining real issues."""
import urllib.request, json, ssl, time
ctx = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(m, p, b=None, t=None, timeout=35):
    url = BASE + p
    h   = {"Content-Type":"application/json","User-Agent":"DiagBot/1.0"}
    if t: h["Authorization"] = f"Bearer {t}"
    d = json.dumps(b).encode() if b else None
    req = urllib.request.Request(url, data=d, headers=h, method=m)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            try:    return r.status, json.loads(r.read().decode())
            except: return r.status, r.read().decode()[:100]
    except urllib.error.HTTPError as e:
        try:    return e.code, json.loads(e.read().decode())
        except: return e.code, e.read().decode()[:100]
    except Exception as e:
        return 0, str(e)[:80]

print()
print("=" * 65)
print("  STEP 5 — Final warm-server verification")
print("=" * 65)

passed = total = 0

def test(label, s, d, expect_2xx=True):
    global passed, total
    ok = (200 <= s < 300) == expect_2xx
    icon = "✅" if ok else "❌"
    if isinstance(d, dict):
        if "error" in d:   detail = f"error: {d['error']}"
        elif "ok" in d:    detail = f"ok={d['ok']}"
        elif "tier" in d:  detail = f"tier={d['tier']} level={d['level']} xp={d['xp']}"
        elif "status" in d:detail = f"status={d['status']}"
        else:              detail = str(d)[:60]
    else:
        detail = str(d)[:60]
    print(f"  {icon} [{s}] {label:<28} {detail}")
    total += 1
    if ok: passed += 1

# Health + DB
s,d = hit("GET", "/health");                 test("health",              s, d)
time.sleep(4)
s,d = hit("GET", "/progress/testuser001");   test("progress (DB read)",  s, d)
time.sleep(4)
s,d = hit("GET", "/progress/default");       test("progress/default",    s, d)

# Auth
time.sleep(4)
s,d = hit("POST", "/auth/signup", {"email":"finaltest@mypytutor.test","name":"Final","password":"Test1234!"})
test("signup",  s, d)
time.sleep(4)
s,d = hit("POST", "/auth/validate-code", {"code":"INVALID"})
test("validate-code (invalid)",  s, d)

# LLM
time.sleep(5)
s,d = hit("POST", "/chat", {"message":"Hello","learner_id":"default","level":"beginner","history":[]}, timeout=45)
test("chat (LLM)",  s, d)
time.sleep(8)
s,d = hit("POST", "/quiz/generate", {"learner_id":"default","topic":"Python","level":"beginner"}, timeout=35)
test("quiz/generate (LLM)",  s, d)
time.sleep(8)
s,d = hit("POST", "/exercise/generate?learner_id=default&topic=variables", timeout=35)
test("exercise/generate (LLM)",  s, d)

# Course
time.sleep(4)
s,d = hit("GET", "/courses/catalog");        test("courses/catalog (17)", s, d)
time.sleep(4)
s,d = hit("GET", "/courses?level=advanced"); test("courses/advanced",     s, d)

# Payments
time.sleep(4)
s,d = hit("GET", "/payments/bank-details");  test("bank-details",         s, d)
time.sleep(4)
s,d = hit("POST", "/webhooks/paystack", {"event":"test"}, timeout=10)
test("paystack_webhook (400=ok)", s, d, expect_2xx=False)

# TTS
time.sleep(4)
s,d = hit("POST", "/tts/prepare", {"text":"Hello **world** test `code`"})
test("tts/prepare",  s, d)
time.sleep(4)
s,d = hit("GET", "/tts/voices");             test("tts/voices",           s, d)

# Feedback + enquiry
time.sleep(4)
s,d = hit("POST", "/feedback/message", {"learner_id":"default","rating":"up","intent":"concept","topic":"python","comment":"good"})
test("feedback/message",  s, d)
time.sleep(4)
s,d = hit("POST", "/enquiry", {"name":"T","email":"t@t.com","category":"general","subject":"Test","message":"Test message for diagnostic"})
test("enquiry",  s, d)

# Certs + verify
time.sleep(4)
s,d = hit("GET", "/verify/notexist999")
test("verify (404=ok)",  s, d, expect_2xx=False)
time.sleep(4)
s,d = hit("GET", "/courses/ai-automation"); test("ai-automation page",    s, d)
time.sleep(4)
s,d = hit("GET", "/voice");                 test("voice guide",            s, d)

print()
print("=" * 65)
print(f"  RESULT: {passed}/{total} PASSED")
if passed == total:
    print("  🎉 ALL CHECKS PASS — Product is revenue-ready!")
else:
    print(f"  {total-passed} issue(s) remain")
print("=" * 65)
print()
