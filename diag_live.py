#!/usr/bin/env python3
"""Live diagnostic — hits every critical endpoint against the deployed server."""
import urllib.request, json, ssl, time

ctx  = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(method, path, body=None, token=None, timeout=25):
    url     = BASE + path
    headers = {"Content-Type": "application/json", "User-Agent": "DiagBot/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            b = r.read().decode()
            try:
                return r.status, json.loads(b)
            except Exception:
                return r.status, b[:300]
    except urllib.error.HTTPError as e:
        b = e.read().decode()
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, b[:200]
    except Exception as e:
        return 0, str(e)[:120]

results = []

# ── 1. Core health ────────────────────────────────────────────────────────────
results.append(("health",           *hit("GET", "/health")))
results.append(("ping",             *hit("GET", "/ping")))
results.append(("auth_config",      *hit("GET", "/auth/config")))
results.append(("supabase_status",  *hit("GET", "/supabase/status")))

# ── 2. Auth flow ──────────────────────────────────────────────────────────────
results.append(("signup", *hit("POST", "/auth/signup", {
    "email": "diagtest001@mypytutor.test",
    "name": "Diag Test User",
    "password": "Test1234!"
})))

sign = hit("POST", "/auth/signin", {
    "email": "diagtest001@mypytutor.test",
    "password": "Test1234!"
})
results.append(("signin", *sign))
token = sign[1].get("token", "") if isinstance(sign[1], dict) else ""

results.append(("auth_me",    *hit("GET", "/auth/me", token=token)))
results.append(("progress",   *hit("GET", "/progress/diagtest001", token=token)))

# ── 3. LLM endpoints ──────────────────────────────────────────────────────────
results.append(("chat", *hit("POST", "/chat", {
    "message": "What is a Python variable?",
    "learner_id": "diagtest001",
    "level": "beginner",
    "history": []
}, token=token, timeout=40)))

results.append(("quiz_generate", *hit("POST", "/quiz/generate", {
    "learner_id": "diagtest001",
    "topic": "Python variables",
    "level": "beginner"
}, token=token, timeout=30)))

results.append(("exercise_gen", *hit("POST", "/exercise/generate", None, token=token)))

# ── 4. Courses ────────────────────────────────────────────────────────────────
results.append(("courses_catalog",  *hit("GET", "/courses/catalog")))
results.append(("courses_beginner", *hit("GET", "/courses?level=beginner")))
results.append(("course_start", *hit("POST", "/course/start", {
    "learner_id": "diagtest001",
    "course_name": "python-fundamentals"
}, token=token, timeout=30)))

# ── 5. Payments ───────────────────────────────────────────────────────────────
results.append(("bank_details",     *hit("GET", "/payments/bank-details")))
results.append(("payment_metadata", *hit("GET", "/payments/metadata/diagtest001", token=token)))

# ── 6. Referrals & Coupons ────────────────────────────────────────────────────
results.append(("referral_get",     *hit("GET", "/referral/diagtest001", token=token)))
results.append(("coupon_validate",  *hit("POST", "/coupons/validate", {"code": "NONE", "plan": "any"})))

# ── 7. TTS ────────────────────────────────────────────────────────────────────
results.append(("tts_prepare", *hit("POST", "/tts/prepare", {
    "text": "Hello world. This is a **test** with `code` and ## heading."
})))
results.append(("tts_voices",  *hit("GET", "/tts/voices")))

# ── 8. Feedback ───────────────────────────────────────────────────────────────
results.append(("feedback_msg", *hit("POST", "/feedback/message", {
    "learner_id": "diagtest001",
    "rating": "good",
    "intent": "concept",
    "topic": "python",
    "comment": "great"
})))

# ── 9. Certificates ───────────────────────────────────────────────────────────
results.append(("cert_basic",    *hit("GET", "/certificate/basic?learner_id=diagtest001&name=DiagTest", token=token)))
results.append(("verify_fake",   *hit("GET", "/verify/faketest123")))

# ── 10. Conversations ─────────────────────────────────────────────────────────
results.append(("conversations", *hit("GET", "/conversations/diagtest001", token=token)))

# ── 11. Invoices ──────────────────────────────────────────────────────────────
results.append(("invoices",      *hit("GET", "/invoices/diagtest001", token=token)))

# ── 12. Assignments ───────────────────────────────────────────────────────────
results.append(("assignments",   *hit("GET", "/assignments/diagtest001", token=token)))

# ── PRINT RESULTS ─────────────────────────────────────────────────────────────
print()
print("=" * 72)
print("  MYPYTUTOR LIVE DIAGNOSTIC — " + BASE)
print("=" * 72)
print(f"  {'ENDPOINT':<22} {'STATUS':<8} DETAIL")
print("-" * 72)

issues = []
for name, status, data in results:
    if 200 <= status < 300:
        icon = "✅"
    elif status in (400, 401, 402, 403, 404, 422):
        icon = "⚠️ "
        issues.append((name, status, data))
    else:
        icon = "❌"
        issues.append((name, status, data))

    detail = ""
    if isinstance(data, dict):
        if "error" in data:    detail = f"error: {data['error']}"
        elif "ok" in data:     detail = f"ok={data['ok']}"
        elif "status" in data: detail = f"status={data['status']}"
        elif "content" in data:detail = f"content: {str(data['content'])[:50]}"
        elif "courses" in data:detail = f"{len(data['courses'])} courses"
        elif "topics" in data: detail = f"{len(data['topics'])} topics"
        elif "text" in data:   detail = f"text: {data['text'][:40]}"
        else:                  detail = str(data)[:60]
    else:
        detail = str(data)[:60]

    print(f"  {icon} {name:<22} [{status}]  {detail}")

print("=" * 72)
print(f"\n  PASSED: {sum(1 for n,s,d in results if 200<=s<300)}/{len(results)}")
if issues:
    print(f"\n  ISSUES ({len(issues)}):")
    for name, status, data in issues:
        print(f"    [{status}] {name}: {str(data)[:100]}")
print()
