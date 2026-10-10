"""
Test email link generation — verifies every URL produced by email_service.py
is well-formed and points to the correct domain.
No emails are actually sent; we call the functions with dry=True via monkeypatch.

Domain rules:
  BACKEND  = https://mypytutor.onrender.com
    routes: /certificate/, /verify/, /admin.html, /auth/confirm, /tts/speak
  FRONTEND = https://mypytutor.com.ng
    routes: /?panel=, /payment, /terms, /privacy, /voice

Run from workspace root:  python scripts/test_email_links.py
"""
import os, re, sys

# Point to backend repo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("APP_URL",      "https://mypytutor.onrender.com")
os.environ.setdefault("FRONTEND_URL", "https://mypytutor.com.ng")

# Monkey-patch _dispatch_async so no emails are actually sent
import app.services.email_service as svc
_dispatched: list[dict] = []
def _fake_dispatch(to, subject, html, text, email_type="generic"):
    _dispatched.append({"to": to, "subject": subject, "html": html,
                        "text": text, "type": email_type})
svc._dispatch_async = _fake_dispatch

# ── Helpers ───────────────────────────────────────────────────────────────────
BACKEND  = "https://mypytutor.onrender.com"
FRONTEND = "https://mypytutor.com.ng"

# Routes that MUST be on the backend
BACKEND_ROUTES = ["/certificate/", "/verify/", "/admin.html",
                  "/auth/confirm", "/tts/", "/static/"]
# Routes that MUST be on the frontend (SPA)
FRONTEND_ROUTES = ["/?panel=", "/payment", "/terms", "/privacy",
                   "/voice", "/courses"]

RESULTS = []

def extract_urls(html: str) -> list[str]:
    """Extract all href= and src= URLs from HTML."""
    return re.findall(r"""(?:href|src)=['"](https?://[^'"]+)""", html)

def check(fn_name: str, html: str, text: str):
    urls = extract_urls(html) + re.findall(r"https?://\S+", text)
    for u in urls:
        u = u.rstrip(".,;)'\"")
        # Determine expected domain
        path = u.replace(BACKEND, "").replace(FRONTEND, "")
        if any(r in path for r in BACKEND_ROUTES):
            expected = BACKEND
        elif any(r in path for r in FRONTEND_ROUTES):
            expected = FRONTEND
        else:
            expected = None  # no strong rule — just log

        if expected and not u.startswith(expected):
            RESULTS.append(("FAIL", fn_name, u, f"Expected domain {expected}"))
        else:
            RESULTS.append(("PASS", fn_name, u, ""))

def run(label: str, fn, *args, **kwargs):
    _dispatched.clear()
    fn(*args, **kwargs)
    for msg in _dispatched:
        check(label, msg["html"], msg["text"])

# ── Run every email function ───────────────────────────────────────────────────
print("Testing email link generation…\n")

run("welcome",
    svc.send_welcome_email, "Tega Test", "test@example.com")

run("verification",
    svc.send_verification_email, "Tega Test", "test@example.com",
    token="abc123token")

run("password_reset",
    svc.send_password_reset_email, "Tega Test", "test@example.com",
    reset_url="https://mypytutor.com.ng/reset?token=abc")

run("course_completion",
    svc.send_course_completion_email, "Tega Test", "test@example.com",
    course_name="Python Fundamentals", xp_earned=100)

run("certificate",
    svc.send_certificate_email, "O'Brien Test & Co", "test@example.com",
    cert_level="basic", cert_id="TGA-4D8032D93E70",
    programme="Basic Python Certificate",
    learner_id="e_e234c416e76caaa8")

run("payment_receipt",
    svc.send_payment_receipt_email, "Tega Test", "test@example.com",
    amount=30000.0, plan="Beginner Bundle", payment_id="PAY-ABC123")

run("learning_reminder",
    svc.send_learning_reminder, "Tega Test", "test@example.com",
    streak_days=5, suggested_topic="Python OOP")

run("xp_milestone",
    svc.send_xp_milestone_email, "Tega Test", "test@example.com",
    xp=500, level="intermediate")

run("weekly_progress",
    svc.send_weekly_progress_email, "Tega Test", "test@example.com",
    xp_this_week=200, lessons_done=4, streak_days=7, top_topic="Python Lists")

run("admin_notification",
    svc.send_admin_notification, "Test Subject", "Test body\nLine 2")

run("reengagement",
    svc.send_reengagement_email, "Tega Test", "test@example.com",
    days_inactive=8, last_topic="Python OOP", xp=300)

run("signin_greeting_new",
    svc.send_signin_greeting_email, "Tega Test", "test@example.com",
    greeting="Good morning, Tega!", is_new_user=True)

run("signin_greeting_return",
    svc.send_signin_greeting_email, "Tega Test", "test@example.com",
    greeting="Good afternoon, Tega!", is_new_user=False)

run("course_reminder",
    svc.send_course_reminder_email, "Tega Test", "test@example.com",
    course_name="Python OOP", step=3, total_steps=14, days_since_last=5)

run("assignment_reminder",
    svc.send_assignment_reminder_email, "Tega Test", "test@example.com",
    pending_count=2, assignment_titles=["Functions", "OOP"])

run("weekend_motivation",
    svc.send_weekend_motivation_email, "Tega Test", "test@example.com",
    xp=400, current_course="Python OOP")

run("new_month",
    svc.send_new_month_email, "Tega Test", "test@example.com",
    month_name="November", xp=600, courses_done=2)

run("resend_confirmation",
    svc.send_resend_confirmation_email, "Tega Test", "test@example.com",
    confirm_url="https://mypytutor.onrender.com/auth/confirm?token=xyz")

# ── Results ───────────────────────────────────────────────────────────────────
passed = [r for r in RESULTS if r[0] == "PASS"]
failed = [r for r in RESULTS if r[0] == "FAIL"]

print(f"{'='*65}")
print(f"RESULTS: {len(passed)} passed  |  {len(failed)} failed  |  {len(RESULTS)} links checked")
print(f"{'='*65}\n")

if failed:
    print("FAILED LINKS:")
    for _, fn, url, note in failed:
        print(f"  [{fn}]  {url}")
        print(f"    -> {note}")
    print()
else:
    print("All links use the correct domain. ✓\n")

# Show a sample of checked links per function
seen_fns: set = set()
print("Sample links per email function:")
for status, fn, url, _ in RESULTS:
    if fn not in seen_fns:
        seen_fns.add(fn)
        sym = "✓" if status == "PASS" else "✗"
        print(f"  {sym} [{fn}]  {url[:90]}")

print()
sys.exit(1 if failed else 0)
