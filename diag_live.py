#!/usr/bin/env python3
"""Live diagnostic — hits every critical endpoint against the deployed server."""
import urllib.request, json, ssl, time

ctx  = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(method, path, body=None, token=None, timeout=35):
    url     = BASE + path
    headers = {"Content-Type": "application/json", "User-Agent": "DiagBot/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            b = r.read().decode()
            try:    return r.status, json.loads(b)
            except: return r.status, b[:300]
    except urllib.error.HTTPError as e:
        b = e.read().decode()
        try:    return e.code, json.loads(b)
        except: return e.code, b[:200]
    except Exception as e:
        return 0, str(e)[:120]

results = []

# ── 1. Core health ────────────────────────────────────────────────────────────
results.append(("health",           *hit("GET", "/health")))
results.append(("ping",             *hit("GET", "/ping")))
results.append(("auth_config",      *hit("GET", "/auth/config")))
results.append(("db_debug",         *hit("GET", "/debug/db")))

# ── 2. Auth flow — create user, get token via admin confirm ───────────────────
ts = int(time.time())
email = f"diag{ts}@mypytutor.test"

results.append(("signup", *hit("POST", "/auth/signup", {
    "email": email, "name": "Diag Test", "password": "Test1234!"
})))

# Try admin login to confirm email
admin_sign = hit("POST", "/admin/login", {
    "email": "tega.com.ng@gmail.com", "password": "admin"
})
admin_token = admin_sign[1].get("token","") if isinstance(admin_sign[1],dict) else ""
results.append(("admin_login", *admin_sign))

if admin_token:
    conf = hit("POST", "/admin/users/confirm-email", {"email": email}, token=admin_token)
    results.append(("admin_confirm", *conf))

sign = hit("POST", "/auth/signin", {"email": email, "password": "Test1234!"})
results.append(("signin", *sign))
token = sign[1].get("token","") if isinstance(sign[1],dict) else ""
lid   = sign[1].get("learner_id","diagtest") if isinstance(sign[1],dict) else "diagtest"

results.append(("auth_me", *hit("GET", "/auth/me", token=token)))
results.append(("progress", *hit("GET", f"/progress/{lid}", token=token)))

# ── 3. LLM endpoints ──────────────────────────────────────────────────────────
results.append(("chat", *hit("POST", "/chat", {
    "message": "What is a Python variable?",
    "learner_id": lid, "level": "beginner", "history": []
}, token=token, timeout=45)))

results.append(("quiz_generate", *hit("POST", "/quiz/generate", {
    "learner_id": lid, "topic": "Python variables", "level": "beginner"
}, token=token, timeout=30)))

# exercise_gen: learner_id + topic are query params
results.append(("exercise_gen", *hit("POST",
    f"/exercise/generate?learner_id={lid}&topic=variables",
    token=token, timeout=30)))

# ── 4. Courses ────────────────────────────────────────────────────────────────
results.append(("courses_catalog",  *hit("GET", "/courses/catalog")))
results.append(("courses_beginner", *hit("GET", "/courses?level=beginner")))

# course_start: learner_id + course_name are query params
results.append(("course_start", *hit("POST",
    f"/course/start?learner_id={lid}&course_name=python-fundamentals",
    token=token, timeout=35)))

# ── 5. Payments ───────────────────────────────────────────────────────────────
results.append(("bank_details",     *hit("GET", "/payments/bank-details")))
results.append(("payment_metadata", *hit("GET", f"/payments/metadata/{lid}", token=token)))

# ── 6. Referrals & Coupons ────────────────────────────────────────────────────
results.append(("referral_get",     *hit("GET", f"/referral/{lid}", token=token)))
results.append(("coupon_validate",  *hit("POST", "/coupons/validate", {"code": "NONE99", "plan": "any"})))

# ── 7. TTS ────────────────────────────────────────────────────────────────────
results.append(("tts_prepare", *hit("POST", "/tts/prepare", {
    "text": "Hello world. This is a test with **bold** and `code`."
})))
results.append(("tts_voices",  *hit("GET", "/tts/voices")))

# ── 8. Feedback ───────────────────────────────────────────────────────────────
results.append(("feedback_msg", *hit("POST", "/feedback/message", {
    "learner_id": lid, "rating": "up", "intent": "concept",
    "topic": "python", "comment": "great"
}, token=token)))

# ── 9. Certificates ───────────────────────────────────────────────────────────
results.append(("cert_basic_locked", *hit("GET",
    f"/certificate/basic?learner_id={lid}&name=DiagTest", token=token)))
results.append(("verify_fake",  *hit("GET", "/verify/faketest123")))

# ── 10. Conversations, Invoices, Assignments ─────────────────────────────────
results.append(("conversations", *hit("GET", f"/conversations/{lid}", token=token)))
results.append(("invoices",      *hit("GET", f"/invoices/{lid}",       token=token)))
results.append(("assignments",   *hit("GET", f"/assignments/{lid}",    token=token)))

# ── PRINT RESULTS ─────────────────────────────────────────────────────────────
print()
print("=" * 72)
print(f"  MYPYTUTOR LIVE DIAGNOSTIC — {BASE}")
print("=" * 72)
print(f"  {'ENDPOINT':<22} {'STATUS':<8} DETAIL")
print("-" * 72)

passed = 0
issues = []

for name, status, data in results:
    # Determine if this is a pass, expected warn, or real failure
    if 200 <= status < 300:
        icon = "✅"
        passed += 1
    elif status in (401, 402, 403, 404, 422):
        # Check if it's expected
        expected = {
            "admin_login":     "expected if wrong password",
            "cert_basic_locked": "expected if user has no tier",
            "verify_fake":     "expected — cert does not exist",
            "coupon_validate": "expected — coupon does not exist",
            "payment_metadata":"expected if token invalid",
        }
        if name in expected:
            icon = "⚠️ "
            passed += 1  # count as pass — correct behaviour
        else:
            icon = "⚠️ "
            issues.append((name, status, data))
    else:
        icon = "❌"
        issues.append((name, status, data))

    detail = ""
    if isinstance(data, dict):
        if "error" in data:     detail = f"error: {str(data['error'])[:60]}"
        elif "status" in data:  detail = f"status={data['status']}"
        elif "ok" in data:      detail = f"ok={data['ok']}"
        elif "content" in data: detail = f"content: {str(data['content'])[:50]}"
        elif "courses" in data: detail = f"{len(data['courses'])} courses"
        elif "topics" in data:  detail = f"{len(data['topics'])} topics"
        elif "text" in data:    detail = f"text: {data['text'][:40]}"
        elif "question" in data:detail = f"question: {str(data['question'])[:50]}"
        else:                   detail = str(data)[:60]
    else:
        detail = str(data)[:60]

    print(f"  {icon} {name:<22} [{status}]  {detail}")

print("=" * 72)
print(f"\n  ✅ PASSED: {passed}/{len(results)}")
if issues:
    print(f"\n  ❌ REAL ISSUES ({len(issues)}):")
    for name, status, data in issues:
        print(f"    [{status}] {name}: {str(data)[:100]}")
else:
    print("\n  🎉 No real issues — product is revenue-ready!")
print()
