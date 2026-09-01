"""
app/services/email_service.py  — Enterprise email service for MyPy Tutor.

Provider chain:  Resend (primary)  ->  Gmail SMTP (fallback)
All sends are non-blocking (background thread).

Env vars:
  RESEND_API_KEY    re_...
  EMAIL_FROM        MyPy Tutor <noreply@mypytutor.com.ng>
  SUPPORT_EMAIL     support@mypytutor.com.ng
  APP_URL           https://mypytutor.onrender.com
  FRONTEND_URL      https://mypytutor.com.ng
  ADMIN_EMAIL       admin inbox for admin_notification()
  EMAIL_USER / EMAIL_PASS  — Gmail SMTP fallback
"""
from __future__ import annotations
import os, time, logging, threading
logger = logging.getLogger(__name__)

# ── config helpers ─────────────────────────────────────────────────────────
def _e(k: str, d: str = "") -> str:         return os.getenv(k, d)
def _app_url() -> str:                      return _e("APP_URL", "https://mypytutor.onrender.com")
def _frontend_url() -> str:                 return _e("FRONTEND_URL", _app_url())
def _from_address() -> str:                 return _e("EMAIL_FROM", "MyPy Tutor <noreply@mypytutor.com.ng>")
def _support_email() -> str:                return _e("SUPPORT_EMAIL", "support@mypytutor.com.ng")
def _resend_key() -> str:                   return _e("RESEND_API_KEY", "")

PRIMARY   = "#0D47A1"
SECONDARY = "#1565E8"
GOLD      = "#E0A300"
NAVY      = "#082B6B"

# ── structured log ─────────────────────────────────────────────────────────
def _log(*, to: str, email_type: str, success: bool,
         attempt: int = 1, reason: str = "", provider: str = "resend") -> None:
    lvl = logging.INFO if success else logging.WARNING
    ok  = "sent" if success else f"FAILED(attempt={attempt})"
    logger.log(lvl, "[email] type=%s to=%s provider=%s status=%s%s",
               email_type, to, provider, ok, f" reason={reason}" if reason else "")

# ── low-level providers ─────────────────────────────────────────────────────
def _send_via_resend(to: str, subject: str, html: str, text: str) -> bool:
    api_key = _resend_key()
    if not api_key:
        return False
    try:
        import httpx
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json={"from": _from_address(), "to": [to], "subject": subject,
                  "html": html, "text": text, "reply_to": _support_email()},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True
        logger.warning("[email] Resend API %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as exc:
        logger.warning("[email] Resend request failed: %s", exc)
        return False


def _send_via_smtp(to: str, subject: str, html: str, text: str) -> bool:
    try:
        from app.email_auth import _send_email as _smtp
        return _smtp(to, subject, html, text)
    except Exception as exc:
        logger.warning("[email] SMTP fallback failed: %s", exc)
        return False


# ── retry / dispatch ────────────────────────────────────────────────────────
_MAX_RETRIES  = 3
_RETRY_DELAYS = (2, 5, 10)


def _dispatch(to: str, subject: str, html: str, text: str,
              email_type: str = "generic") -> bool:
    """Retry-aware delivery: Resend x3 -> SMTP x1. Never raises."""
    if _resend_key():
        for attempt in range(1, _MAX_RETRIES + 1):
            ok = _send_via_resend(to, subject, html, text)
            _log(to=to, email_type=email_type, success=ok, attempt=attempt, provider="resend")
            if ok:
                return True
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAYS[attempt - 1])
        logger.warning("[email] Resend failed %d attempts for %s — SMTP fallback", _MAX_RETRIES, to)

    ok = _send_via_smtp(to, subject, html, text)
    _log(to=to, email_type=email_type, success=ok, provider="smtp")
    return ok


def _dispatch_async(to: str, subject: str, html: str, text: str,
                    email_type: str = "generic") -> None:
    """Fire-and-forget in a non-daemon thread."""
    threading.Thread(
        target=_dispatch, args=(to, subject, html, text, email_type),
        daemon=False, name="email-" + email_type + "-" + to[:20],
    ).start()

# ── HTML shell ──────────────────────────────────────────────────────────────
def _shell(body_html: str, preview: str = "") -> str:
    api  = _app_url()       # backend — serves logo image and API endpoints
    site = _frontend_url()  # custom domain — all user-facing links
    supp = _support_email()
    pv   = ('<div style="display:none;max-height:0;overflow:hidden;">' + preview + "</div>") if preview else ""
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'/>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>"
        "<title>MyPy Tutor</title>" + pv + "</head>"
        "<body style='margin:0;padding:0;background:#f0f4fa;"
        "font-family:Segoe UI,Arial,Helvetica,sans-serif;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'"
        " style='background:#f0f4fa;padding:32px 16px;'><tr><td align='center'>"
        "<table width='600' cellpadding='0' cellspacing='0'"
        " style='max-width:600px;width:100%;'>"
        # header
        "<tr><td style='background:linear-gradient(135deg," + NAVY + " 0%," + PRIMARY + " 60%,"
        + SECONDARY + " 100%);border-radius:16px 16px 0 0;padding:28px 40px;text-align:center;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr><td style='text-align:center;'>"
        "<div style='display:inline-flex;align-items:center;gap:12px;'>"
        "<div style='width:56px;height:56px;border-radius:50%;overflow:hidden;background:#fff;"
        "border:3px solid rgba(224,163,0,0.5);box-shadow:0 0 20px rgba(13,71,161,0.5);'>"
        "<img src='" + api + "/static/icons/mypytutor_logo.jpg' alt='MyPy Tutor'"
        " width='56' height='56' style='display:block;width:56px;height:56px;object-fit:cover;'/>"
        "</div>"
        "<span style='font-family:Segoe UI,Arial,sans-serif;'>"
        "<span style='font-size:1.4rem;font-weight:900;color:" + GOLD + ";letter-spacing:0.04em;'>MYPY</span>"
        "<span style='font-size:1.4rem;font-weight:900;color:#fff;'> TUTOR</span>"
        "</span></div></td></tr></table>"
        "<p style='color:rgba(255,255,255,0.65);font-size:0.72rem;margin:8px 0 0;"
        "letter-spacing:0.1em;text-transform:uppercase;'>Africa&#39;s Best AI, Python &amp; Machine Learning Tutor</p>"
        "</td></tr>"
        # body
        "<tr><td style='background:#fff;padding:36px 40px;"
        "border-left:1px solid #dde6f5;border-right:1px solid #dde6f5;'>"
        "<div style='color:#1e293b;'>" + body_html + "</div>"
        "</td></tr>"
        # footer
        "<tr><td style='background:" + NAVY + ";border-radius:0 0 16px 16px;"
        "padding:20px 40px;text-align:center;'>"
        "<p style='color:rgba(255,255,255,0.9);font-size:0.8rem;font-weight:700;margin:0 0 4px;'>"
        "TeamTega Technologies Limited</p>"
        "<p style='color:rgba(255,255,255,0.65);font-size:0.72rem;margin:0 0 4px;'>"
        "Teamsamikoko Global Academy &middot; Reg No: 3508656</p>"
        "<p style='color:rgba(255,255,255,0.5);font-size:0.68rem;font-style:italic;margin:0 0 8px;'>"
        "&ldquo;Africa's Best AI, Python &amp; Machine Learning Tutor&rdquo;</p>"
        "<a href='" + site + "' style='color:#90c4ff;font-size:0.72rem;text-decoration:none;'>"
        "mypytutor.com.ng</a> &middot; "
        "<a href='mailto:" + supp + "' style='color:#90c4ff;font-size:0.72rem;text-decoration:none;'>"
        + supp + "</a>"
        "<p style='color:rgba(255,255,255,0.35);font-size:0.65rem;margin:12px 0 0;'>"
        "You are receiving this because you signed up at MyPy Tutor.</p>"
        "</td></tr>"
        "</table></td></tr></table></body></html>"
    )

# ── reusable sub-components ─────────────────────────────────────────────────
def _cta(label: str, url: str, color: str = "#0D47A1") -> str:
    return (
        "<div style='text-align:center;margin:28px 0;'>"
        "<a href='" + url + "' style='display:inline-block;background:" + color + ";"
        "color:#ffffff;text-decoration:none;font-weight:700;font-size:0.95rem;"
        "padding:14px 40px;border-radius:10px;"
        "box-shadow:0 4px 16px rgba(13,71,161,0.35);'>" + label + "</a></div>"
    )

def _box(content: str, bg: str = "#f0f7ff", border: str = "#0D47A1") -> str:
    return (
        "<table width='100%' cellpadding='0' cellspacing='0' style='"
        "background:" + bg + ";border-radius:10px;border-left:4px solid " + border + ";"
        "margin:18px 0;'><tr><td style='padding:18px 22px;color:#1e293b;"
        "font-size:0.88rem;line-height:1.65;'>" + content + "</td></tr></table>"
    )

def _hr() -> str:
    return "<hr style='border:none;border-top:1px solid #e2e8f0;margin:24px 0;'/>"

# ============================================================================
# Public email methods
# ============================================================================

# ── 1. Welcome ───────────────────────────────────────────────────────────────
def send_welcome_email(name: str, email: str) -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    features = (
        "<strong style='color:" + PRIMARY + ";'>What is waiting for you:</strong><br/>"
        "&#129302;&nbsp;<strong>Sir. Tega AI Tutor</strong> &mdash; ask anything, get instant explanations<br/>"
        "&#128218;&nbsp;<strong>16 structured Python courses</strong> &mdash; beginner to executive<br/>"
        "&#128200;&nbsp;<strong>XP &amp; progress tracking</strong> &mdash; know exactly where you stand<br/>"
        "&#127942;&nbsp;<strong>Verifiable certificates</strong> &mdash; issued by Teamsamikoko Global Academy<br/>"
        "&#127919;&nbsp;<strong>Daily quizzes &amp; exercises</strong> &mdash; practice makes perfect"
    )
    body = (
        "<p style='font-size:1rem;color:#1e293b;margin:0 0 16px;'>Dear <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.25rem;margin:0 0 12px;'>Welcome to MyPy Tutor! &#127881;</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "We are thrilled to have you join our growing community of Python learners. "
        "<strong>Sir. Tega</strong> &mdash; your AI tutor &mdash; is ready to teach you Python "
        "from the basics all the way to AI, data science, and machine learning.</p>"
        + _box(features)
        + _cta("&#128640; Start Learning Now", app)
        + "<p style='color:#64748b;font-size:0.85rem;line-height:1.6;margin:0;'>"
          "Warm regards,<br/><strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "Welcome to MyPy Tutor, " + first + "! Start learning Python today.")
    text = ("Dear " + first + ",\n\nWelcome to MyPy Tutor!\n\n"
            "Sir. Tega is your AI, Python and Machine Learning tutor. Start learning at:\n" + app + "\n\n"
            "Warm regards,\nThe MyPy Tutor Team\n"
            "TeamTega Technologies Limited\n"
            "Teamsamikoko Global Academy - Reg No: 3508656\n")
    _dispatch_async(email, "Welcome to MyPy Tutor, " + first + "! &#128013;", html, text, "welcome")


# ── 2. Email verification ─────────────────────────────────────────────────────
def send_verification_email(name: str, email: str, token: str) -> None:
    first       = name.split()[0] if name else "Learner"
    app         = _app_url()
    confirm_url = app + "/auth/confirm?token=" + token
    notice = ("This link expires in <strong>24 hours</strong>. "
              "If you did not create an account, ignore this email.")
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>Confirm your email address</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Thanks for signing up! Click the button below to confirm your email address "
        "and activate your MyPy Tutor account.</p>"
        + _cta("&#9989; Confirm My Email", confirm_url)
        + _box(notice, bg="#fffbeb", border=GOLD)
        + "<p style='color:#64748b;font-size:0.82rem;'>If the button does not work:<br/>"
          "<a href='" + confirm_url + "' style='color:" + SECONDARY + ";word-break:break-all;'>"
          + confirm_url + "</a></p>"
    )
    html = _shell(body, "Confirm your email to activate your MyPy Tutor account.")
    text = ("Hi " + first + ",\n\nConfirm your MyPy Tutor account:\n" + confirm_url
            + "\n\nThis link expires in 24 hours.\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Confirm your MyPy Tutor account", html, text, "verification")


# ── 3. Password reset ─────────────────────────────────────────────────────────
def send_password_reset_email(name: str, email: str, reset_url: str) -> None:
    first  = name.split()[0] if name else "Learner"
    notice = ("This link expires in <strong>1 hour</strong>. "
              "If you did not request a reset, your account remains secure.")
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>Reset your password</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "We received a request to reset the password for your MyPy Tutor account. "
        "Click the button below to choose a new password.</p>"
        + _cta("&#128273; Reset Password", reset_url, color="#DC2626")
        + _box(notice, bg="#fff1f2", border="#DC2626")
        + "<p style='color:#64748b;font-size:0.82rem;'>If the button does not work:<br/>"
          "<a href='" + reset_url + "' style='color:" + SECONDARY + ";word-break:break-all;'>"
          + reset_url + "</a></p>"
    )
    html = _shell(body, "Reset your MyPy Tutor password - link expires in 1 hour.")
    text = ("Hi " + first + ",\n\nReset your MyPy Tutor password:\n" + reset_url
            + "\n\nThis link expires in 1 hour.\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Reset your MyPy Tutor password", html, text, "password_reset")

# ── 4. Course completion ──────────────────────────────────────────────────────
def send_course_completion_email(name: str, email: str, course_name: str,
                                  xp_earned: int = 0) -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    xp_str = ("You earned <strong style='color:" + GOLD + ";'>" + str(xp_earned) + " XP</strong>!"
               if xp_earned else "")
    next_steps = (
        "&#127919;&nbsp;Continue to your next course<br/>"
        "&#127885;&nbsp;Take a quiz to reinforce what you have learned<br/>"
        "&#127891;&nbsp;Check if you have unlocked a certificate"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 8px;'>Course Completed! &#127942;</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Congratulations! You have successfully completed "
        "<strong style='color:" + PRIMARY + ";'>" + course_name + "</strong>. " + xp_str + "</p>"
        + _box("<strong>What is next?</strong><br/>" + next_steps)
        + _cta("&#128218; Continue Learning", app)
        + "<p style='color:#64748b;font-size:0.85rem;'>Keep up the great work!<br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "You completed " + course_name + "! Keep up the great work.")
    text = ("Hi " + first + ",\n\nCongratulations! You completed: " + course_name + ".\n"
            + ("You earned " + str(xp_earned) + " XP!\n" if xp_earned else "")
            + "Continue learning at: " + app + "\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Course Completed: " + course_name, html, text, "course_completion")


# ── 5. Certificate ────────────────────────────────────────────────────────────
def send_certificate_email(name: str, email: str, cert_level: str, cert_id: str) -> None:
    first        = name.split()[0] if name else "Learner"
    # cert view → FRONTEND_URL (custom domain, e.g. mypytutor.com.ng)
    # verify endpoint → APP_URL  (backend API, e.g. mypytutor.onrender.com)
    frontend     = _frontend_url()
    api          = _app_url()
    verify_url   = api + "/verify/" + cert_id
    # Certificate view link goes to the frontend so the user sees the branded site
    cert_url     = (frontend + "/certificate/" + cert_level
                    + "?name=" + name.replace(" ", "%20") + "&admin_view=false")
    label        = cert_level.title()
    details = (
        "<strong>Certificate Details</strong><br/>"
        "&#127885;&nbsp;Level: <strong>" + label + "</strong><br/>"
        "&#128218;&nbsp;Certificate ID: <code style='background:#e2e8f0;padding:2px 6px;"
        "border-radius:4px;'>" + cert_id + "</code><br/>"
        "&#9989;&nbsp;Issuer: Teamsamikoko Global Academy (Reg No: 3508656)<br/>"
        "&#128279;&nbsp;Verify: <a href='" + verify_url + "' style='color:#16A34A;word-break:break-all;'>"
        + verify_url + "</a>"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Dear <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.25rem;margin:0 0 8px;'>"
        "&#127891; Your " + label + " Certificate is Ready!</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Congratulations on completing the <strong>" + label + " Python Programme</strong> at "
        "MyPy Tutor. Your certificate, issued by <strong>Teamsamikoko Global Academy</strong>, "
        "is now available.</p>"
        + _box(details, bg="#f0fdf4", border="#16A34A")
        + "<div style='text-align:center;margin:24px 0;'>"
          "<a href='" + cert_url + "' style='display:inline-block;background:linear-gradient(135deg,"
          + GOLD + "," + "#C98B00" + ");color:#fff;text-decoration:none;font-weight:700;"
          "font-size:0.95rem;padding:14px 36px;border-radius:10px;margin-right:10px;"
          "margin-bottom:10px;'>"
          "&#127891; View Certificate</a>"
          "<a href='" + verify_url + "' style='display:inline-block;background:" + PRIMARY + ";"
          "color:#fff;text-decoration:none;font-weight:700;font-size:0.95rem;"
          "padding:14px 36px;border-radius:10px;margin-bottom:10px;'>&#9989; Verify Online</a></div>"
        + "<p style='color:#64748b;font-size:0.85rem;'>Well done on this achievement!<br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "Your " + label + " Python Certificate is ready!")
    text = ("Dear " + first + ",\n\nYour " + label + " Certificate (ID: " + cert_id
            + ") is ready.\n\nView: " + cert_url
            + "\nVerify: " + verify_url
            + "\n\nIssued by Teamsamikoko Global Academy - Reg No: 3508656\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Your " + label + " Certificate is Ready! &#127891;", html, text, "certificate")

# ── 6. Payment receipt ────────────────────────────────────────────────────────
def send_payment_receipt_email(name: str, email: str, amount: float,
                                plan: str, payment_id: str,
                                currency: str = "NGN") -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    from datetime import datetime as _dt
    date_str = _dt.utcnow().strftime("%d %B %Y")
    plan_labels = {
        # Course bundles — one-time purchases
        "tier1":              "Beginner Bundle (4 courses) — NGN 8,000",
        "tier2":              "Intermediate Bundle (7 courses) — NGN 15,000",
        "tier3":              "Elite Bundle (all 16 courses) — NGN 35,000",
        "beginner bundle":    "Beginner Bundle (4 courses) — NGN 10,000",
        "intermediate bundle":"Intermediate Bundle (7 courses) — NGN 20,000",
        "elite bundle":       "Elite Bundle (all 16 courses) — NGN 45,000",
        # Certificate fees — standalone exam/assessment
        "basic-cert":         "Basic Python Certificate — NGN 30,000",
        "adv-cert":           "Advanced Python Certificate — NGN 60,000",
        "exec-cert":          "Executive Masters Certificate — NGN 100,000",
        # Prompt plans — monthly AI access
        "prompt-starter":     "Prompt Starter (50/day) — NGN 2,000/month",
        "prompt-pro":         "Prompt Pro (200/day) — NGN 5,000/month",
        "prompt-unlimited":   "Prompt Unlimited (no cap) — NGN 10,000/month",
    }
    plan_label = plan_labels.get(plan, plan)
    receipt = (
        "<strong>Receipt</strong><br/>"
        "&#128221;&nbsp;Payment ID: <code style='background:#e2e8f0;padding:2px 6px;"
        "border-radius:4px;'>" + payment_id + "</code><br/>"
        "&#128197;&nbsp;Date: " + date_str + "<br/>"
        "&#128179;&nbsp;Plan: " + plan_label + "<br/>"
        "&#128176;&nbsp;Amount: <strong style='color:#16A34A;'>"
        + currency + " " + "{:,.0f}".format(amount) + "</strong><br/>"
        "&#9989;&nbsp;Status: <strong style='color:#16A34A;'>Confirmed</strong>"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Dear <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>Payment Confirmed &#9989;</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Thank you for your payment. Your subscription to <strong>" + plan_label
        + "</strong> has been confirmed and is now active.</p>"
        + _box(receipt, bg="#f0fdf4", border="#16A34A")
        + _cta("&#128640; Access Your Dashboard", app)
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "Questions? <a href='mailto:" + _support_email() + "'>" + _support_email() + "</a><br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "Payment confirmed - " + currency + " " + "{:,.0f}".format(amount) + " for " + plan_label)
    text = ("Dear " + first + ",\n\nPayment confirmed.\nPayment ID: " + payment_id
            + "\nDate: " + date_str + "\nPlan: " + plan_label
            + "\nAmount: " + currency + " " + "{:,.0f}".format(amount)
            + "\n\nDashboard: " + app + "\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Payment Confirmed - MyPy Tutor", html, text, "payment_receipt")


# ── 7. Subscription notification ─────────────────────────────────────────────
def send_subscription_email(name: str, email: str, event: str,
                             plan: str, details: str = "") -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    emojis = {"upgraded": "&#127881;", "downgraded": "&#11015;", "cancelled": "&#10060;",
               "renewed": "&#9989;", "expiring_soon": "&#9200;"}
    icon  = emojis.get(event, "&#8505;")
    title = event.replace("_", " ").title()
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>"
        + icon + " Subscription " + title + "</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Your MyPy Tutor subscription has been <strong>" + title.lower()
        + "</strong>. Current plan: <strong>" + plan + "</strong>."
        + ("<br/>" + details if details else "") + "</p>"
        + _cta("Manage Subscription", app + "/?panel=pricing")
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "Questions? <a href='mailto:" + _support_email() + "'>" + _support_email() + "</a><br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "MyPy Tutor subscription " + event + ".")
    text = ("Hi " + first + ",\n\nYour subscription has been " + event + ".\nPlan: " + plan
            + ("\n" + details if details else "")
            + "\nManage at: " + app + "/?panel=pricing\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "MyPy Tutor Subscription " + title + " " + icon,
                    html, text, "subscription")

# ── 8. Learning reminder ──────────────────────────────────────────────────────
def send_learning_reminder(name: str, email: str, streak_days: int = 0,
                            suggested_topic: str = "") -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    streak_html = ("<p style='color:" + GOLD + ";font-weight:700;font-size:1.1rem;margin:0 0 12px;'>"
                   "&#128293; " + str(streak_days) + "-day streak &mdash; keep it going!</p>"
                   if streak_days > 1 else "")
    topic_html  = ("<p style='color:#475569;line-height:1.7;margin:0 0 12px;'>"
                   "&#128204; Continue with: <strong>" + suggested_topic + "</strong></p>"
                   if suggested_topic else "")
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        + streak_html
        + "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 8px;'>"
          "Time to learn today! &#128218;</h2>"
          "<p style='color:#475569;line-height:1.7;margin:0 0 12px;'>"
          "Your daily Python learning session is waiting. Even 15 minutes a day builds mastery.</p>"
        + topic_html
        + _cta("&#128218; Continue Learning", app)
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "Your daily Python lesson is waiting - keep your streak alive!")
    text = ("Hi " + first + ",\n\n"
            + ("&#128293; " + str(streak_days) + "-day streak! " if streak_days > 1 else "")
            + "Time to learn today.\n"
            + ("Continue with: " + suggested_topic + "\n" if suggested_topic else "")
            + "Start at: " + app + "\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Your daily Python lesson is waiting!", html, text, "learning_reminder")


# ── 9. XP milestone ───────────────────────────────────────────────────────────
def send_xp_milestone_email(name: str, email: str, xp: int, level: str) -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    stats = ("&#127885;&nbsp;Total XP: <strong style='color:" + GOLD + ";font-size:1.1rem;'>"
             + "{:,}".format(xp) + " XP</strong><br/>"
             "&#128202;&nbsp;Level: <strong>" + level.title() + "</strong>")
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + GOLD + ";font-size:1.25rem;margin:0 0 8px;'>"
        "&#11088; XP Milestone Reached!</h2>"
        + _box(stats, bg="#fffbeb", border=GOLD)
        + "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
          "Outstanding progress! Every XP point brings you closer to mastery and certification.</p>"
        + _cta("View Your Progress", app + "/?panel=progress")
    )
    html = _shell(body, "You have reached " + "{:,}".format(xp) + " XP - amazing progress!")
    text = ("Hi " + first + ",\n\nYou have reached " + "{:,}".format(xp)
            + " XP! Level: " + level.title()
            + "\nView progress: " + app + "/?panel=progress\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "XP Milestone: " + "{:,}".format(xp) + " XP earned!",
                    html, text, "xp_milestone")


# ── 10. Weekly progress ───────────────────────────────────────────────────────
def send_weekly_progress_email(name: str, email: str, xp_this_week: int,
                                lessons_done: int, streak_days: int,
                                top_topic: str = "") -> None:
    first = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    stats = (
        "&#11088;&nbsp;XP this week: <strong style='color:" + GOLD + ";'>"
        + "{:,}".format(xp_this_week) + "</strong><br/>"
        "&#128218;&nbsp;Lessons completed: <strong>" + str(lessons_done) + "</strong><br/>"
        "&#128293;&nbsp;Current streak: <strong>" + str(streak_days) + " days</strong>"
        + ("<br/>&#127919;&nbsp;Top topic: <strong>" + top_topic + "</strong>" if top_topic else "")
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>"
        "&#128202; Your Weekly Python Progress</h2>"
        + _box(stats)
        + _cta("&#128200; View Full Progress", app + "/?panel=progress")
    )
    html = _shell(body, "Weekly recap: " + "{:,}".format(xp_this_week)
                  + " XP, " + str(lessons_done) + " lessons this week!")
    text = ("Hi " + first + ",\n\nWeekly progress:\nXP: " + "{:,}".format(xp_this_week)
            + "\nLessons: " + str(lessons_done) + "\nStreak: " + str(streak_days) + " days"
            + ("\nTop topic: " + top_topic if top_topic else "")
            + "\nFull progress: " + app + "/?panel=progress\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Your weekly Python progress report", html, text, "weekly_progress")

# ── 11. Product announcement ──────────────────────────────────────────────────
def send_product_update_email(name: str, email: str, subject: str,
                               body_html: str, target_label: str = "All Users") -> None:
    first   = name.split()[0] if name else "Learner"
    app   = _frontend_url()
    support = _support_email()
    # CAN-SPAM / GDPR compliant: every bulk email must include an unsubscribe option.
    # We use a mailto: unsubscribe link pointing to support so the team can honour it.
    unsubscribe_line = (
        "<p style='color:#94a3b8;font-size:0.72rem;margin:16px 0 0;'>"
        "Sent to: " + target_label + " &middot; "
        "To unsubscribe from announcements, reply to this email or contact "
        "<a href='mailto:" + support + "?subject=Unsubscribe' "
        "style='color:#90c4ff;'>support</a>.</p>"
    )
    body  = (
        "<p style='color:#1e293b;margin:0 0 16px;'>Hi <strong>" + first + "</strong>,</p>"
        + body_html
        + _hr()
        + _cta("&#128640; Open MyPy Tutor", app)
        + unsubscribe_line
    )
    html = _shell(body, subject)
    text = (
        "Hi " + first + ",\n\n" + subject + "\n\nOpen at: " + app
        + "\n\n-- MyPy Tutor Team"
        + "\n\nTo unsubscribe, email: " + support + " with subject 'Unsubscribe'."
    )
    _dispatch_async(email, subject, html, text, "announcement")


def send_bulk_announcement(subject: str, body_html: str, body_text: str,
                            recipients: list, target_label: str = "All Users") -> int:
    """
    Send a personalised announcement to every recipient in the list.
    recipients: list of (email, name) tuples.
    Returns number of emails dispatched.
    CAN-SPAM / GDPR: every email includes an unsubscribe link via send_product_update_email.
    """
    sent = 0
    for rcpt_email, rcpt_name in recipients:
        if not rcpt_email or "@" not in rcpt_email:
            continue
        first = rcpt_name.split()[0] if rcpt_name else "Learner"
        personalised = body_html.replace("{{name}}", first).replace("{{first_name}}", first)
        send_product_update_email(
            name=rcpt_name, email=rcpt_email,
            subject=subject, body_html=personalised,
            target_label=target_label,
        )
        sent += 1
    return sent


# ── 12. Admin notification ────────────────────────────────────────────────────
def send_admin_notification(subject: str, body: str) -> None:
    """Send an alert to the admin inbox. High priority — non-daemon thread."""
    admin_email = _e("ADMIN_EMAIL", "")
    if not admin_email:
        logger.warning("[email] ADMIN_EMAIL not set — skipping admin notification: %s", subject)
        return
    app     = _frontend_url()
    content = (
        "<h2 style='color:#DC2626;font-size:1.1rem;margin:0 0 12px;'>&#9888; Admin Notification</h2>"
        + _box("<strong>" + subject + "</strong><br/><br/>" + body.replace("\n", "<br/>"),
               bg="#fff1f2", border="#DC2626")
        + _cta("Open Admin Dashboard", app + "/admin.html", color="#DC2626")
    )
    html = _shell(content, "Admin: " + subject)
    text = "Admin Notification\n\n" + subject + "\n\n" + body + "\n\nAdmin panel: " + app + "/admin.html"
    threading.Thread(
        target=_dispatch,
        args=(admin_email, "[MyPyTutor Admin] " + subject, html, text, "admin_notification"),
        daemon=False,
    ).start()

# ── 13. User enquiry / support ticket ────────────────────────────────────────
def send_enquiry_email(name: str, email: str, category: str,
                       subject: str, message: str,
                       learner_id: str = "") -> None:
    """
    Forward a user support enquiry to support@mypytutor.com.ng (which is
    linked to tega.com.ng@gmail.com via Resend routing or Gmail forwarding).
    Also send a confirmation receipt to the user.
    """
    support    = _support_email()   # support@mypytutor.com.ng
    admin_dest = _e("ADMIN_EMAIL", support)   # real inbox: tega.com.ng@gmail.com
    app   = _frontend_url()

    # ── Email to support inbox (admin receives this) ──────────────────────
    admin_body = (
        "<h2 style='color:#0D47A1;font-size:1.1rem;margin:0 0 16px;'>&#128232; New Support Enquiry</h2>"
        + _box(
            "<strong>Category:</strong> " + category + "<br/>"
            "<strong>Subject:</strong> " + subject + "<br/>"
            "<strong>From:</strong> " + name + " &lt;" + email + "&gt;<br/>"
            + ("<strong>Learner ID:</strong> <code style='font-size:.82rem;'>" + learner_id + "</code><br/>" if learner_id and learner_id != "guest" else "")
            + "<strong>Message:</strong><br/>"
            + "<div style='white-space:pre-wrap;margin-top:8px;color:#475569;line-height:1.7;'>" + message + "</div>",
            bg="#f0f7ff", border="#0D47A1"
        )
        + "<p style='color:#64748b;font-size:.82rem;margin-top:16px;'>"
          "Reply directly to this email to respond to the learner.</p>"
    )
    admin_html = _shell(admin_body, f"Support: {category} — {subject}")
    admin_text = (
        f"New Support Enquiry\n\nCategory: {category}\nSubject: {subject}\n"
        f"From: {name} <{email}>\nLearner ID: {learner_id}\n\nMessage:\n{message}"
    )

    # Dispatch to admin — reply-to set to user's email so admin can reply directly
    def _send_to_admin():
        if _resend_key():
            try:
                import httpx
                r = httpx.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": "Bearer " + _resend_key(),
                             "Content-Type": "application/json"},
                    json={
                        "from":     _from_address(),
                        "to":       [admin_dest],
                        "reply_to": email,        # admin replies go to the user
                        "subject":  f"[Support] {category}: {subject}",
                        "html":     admin_html,
                        "text":     admin_text,
                    },
                    timeout=15,
                )
                if r.status_code in (200, 201):
                    return
            except Exception:
                pass
        # SMTP fallback
        _dispatch(admin_dest, f"[Support] {category}: {subject}",
                  admin_html, admin_text, "enquiry_admin")

    threading.Thread(target=_send_to_admin, daemon=False,
                     name="enquiry-admin-" + email[:20]).start()

    # ── Confirmation receipt to the user ─────────────────────────────────
    first = name.split()[0] if name else "Learner"
    receipt_body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>"
        "&#9989; We received your message!</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Our support team will review your enquiry and respond within <strong>24 hours</strong>.</p>"
        + _box(
            "<strong>Category:</strong> " + category + "<br/>"
            "<strong>Subject:</strong> " + subject,
            bg="#f0f7ff", border="#0D47A1"
        )
        + "<p style='color:#64748b;font-size:.82rem;margin-top:16px;'>"
          "Need faster help? Email us directly at "
          "<a href='mailto:" + support + "' style='color:" + PRIMARY + ";'>" + support + "</a></p>"
    )
    receipt_html = _shell(receipt_body, "We received your support request — MyPy Tutor")
    receipt_text = (
        f"Hi {first},\n\nWe received your support request.\n\n"
        f"Category: {category}\nSubject: {subject}\n\n"
        f"We'll respond within 24 hours.\n\n"
        f"Direct email: {support}\n\n-- The MyPy Tutor Support Team"
    )
    _dispatch_async(email, "Your MyPy Tutor support request was received",
                    receipt_html, receipt_text, "enquiry_receipt")


# ── 13. Re-engagement (7-day inactivity) ─────────────────────────────────────
def send_reengagement_email(name: str, email: str, days_inactive: int,
                             last_topic: str = "", xp: int = 0) -> None:
    """
    Send a personalised re-engagement email to a learner who has been inactive
    for 7+ days.  Called by the nightly background job in main.py.
    """
    first    = name.split()[0] if name else "Learner"
    site     = _frontend_url()
    days_str = str(days_inactive)

    streak_loss = (
        "<p style='color:#DC2626;font-weight:700;font-size:0.9rem;margin:0 0 12px;'>"
        "&#9200; You haven't visited in <strong>" + days_str + " days</strong> — "
        "don't let your progress fade!</p>"
    )
    topic_hint = (
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "&#128204; Pick up where you left off: "
        "<strong>" + last_topic + "</strong></p>"
        if last_topic else
        "<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
        "Sir. Tega is ready to teach you something new today.</p>"
    )
    xp_note = (
        "<p style='color:#475569;margin:0 0 16px;'>"
        "You already have <strong style='color:#E0A300;'>" + "{:,}".format(xp) + " XP</strong> — "
        "keep building on that foundation!</p>"
        if xp else ""
    )
    tips = (
        "&#128218;&nbsp;Ask Sir. Tega any Python question<br/>"
        "&#127919;&nbsp;Take a 2-minute quiz to warm up<br/>"
        "&#128200;&nbsp;Check your progress dashboard<br/>"
        "&#127942;&nbsp;Work toward your next certificate"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        + streak_loss
        + "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 12px;'>"
          "&#128013; Sir. Tega misses you!</h2>"
        + topic_hint
        + xp_note
        + _box("<strong>Jump back in:</strong><br/>" + tips)
        + _cta("&#128640; Resume Learning Now", site)
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "Even 10 minutes a day builds mastery.<br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
        + "<p style='color:#94a3b8;font-size:0.7rem;margin-top:16px;'>"
          "To stop receiving reminders, reply to this email with 'unsubscribe'.</p>"
    )
    html = _shell(body, "Sir. Tega misses you! Come back and keep learning Python.")
    text = (
        "Hi " + first + ",\n\n"
        "You haven't visited MyPy Tutor in " + days_str + " days.\n"
        + ("Last topic: " + last_topic + "\n" if last_topic else "")
        + ("Your XP: " + "{:,}".format(xp) + "\n" if xp else "")
        + "\nResume learning: " + site
        + "\n\n-- The MyPy Tutor Team"
    )
    _dispatch_async(email,
                    "Sir. Tega misses you! &#128013; Come back to MyPy Tutor",
                    html, text, "reengagement")


# ── 14. Sign-in / Sign-up greeting email ─────────────────────────────────────
def send_signin_greeting_email(name: str, email: str, greeting: str,
                                is_new_user: bool = False) -> None:
    """
    Warm personalised email sent immediately after sign-in or email confirmation.
    Uses the WAT-aware greeting already computed by the backend.
    New users get onboarding tips; returning users get a motivational nudge.
    """
    first = name.split()[0] if name else "Learner"
    site  = _frontend_url()

    if is_new_user:
        headline = f"&#127881; Welcome to MyPy Tutor, {first}!"
        sub      = (
            "Sir. Tega is ready to be your personal Python and AI tutor. "
            "Here is everything waiting for you:"
        )
        tips = (
            "&#127813;&nbsp;<strong>Ask Sir. Tega anything</strong> — Python, NumPy, Pandas, ML, and more<br/>"
            "&#128218;&nbsp;<strong>16 structured courses</strong> — beginner to executive level<br/>"
            "&#127942;&nbsp;<strong>Earn certificates</strong> — issued by Teamsamikoko Global Academy<br/>"
            "&#127919;&nbsp;<strong>Daily quizzes</strong> — track your progress and close knowledge gaps<br/>"
            "&#128176;&nbsp;<strong>Free to start</strong> — 10 AI prompts per day, no card needed"
        )
        cta_label = "&#128640; Start Learning Now"
        preview   = f"Welcome {first}! Sir. Tega is ready for you."
    else:
        headline = f"&#128013; {greeting}"
        sub      = "Good to see you back! Here is a quick reminder of what to pick up today:"
        tips = (
            "&#128204;&nbsp;Continue where you left off on your current course<br/>"
            "&#127919;&nbsp;Take a 2-minute quiz to warm up your brain<br/>"
            "&#128200;&nbsp;Check your XP and progress dashboard<br/>"
            "&#9997;&#65039;&nbsp;Submit any pending assignments for review"
        )
        cta_label = "&#128218; Continue Learning"
        preview   = f"{greeting} — Your Python journey continues."

    body = (
        f"<p style='color:#1e293b;margin:0 0 8px;'><strong style='font-size:1.1rem;'>{headline}</strong></p>"
        f"<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>{sub}</p>"
        + _box(tips)
        + _cta(cta_label, site)
        + "<p style='color:#64748b;font-size:0.82rem;margin:0;'>"
          "Warm regards,<br/><strong style='color:" + PRIMARY + ";'>Sir. Tega &amp; The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, preview)
    text = (
        f"{greeting}\n\n"
        + ("Welcome to MyPy Tutor! Sir. Tega is your personal Python tutor.\n\n" if is_new_user
           else "Good to see you back!\n\n")
        + "Continue learning at: " + site + "\n\n-- Sir. Tega & The MyPy Tutor Team"
    )
    _dispatch_async(email, headline.replace("&#127881;", "🎉").replace("&#128013;", "🐍"),
                    html, text, "signin_greeting")


# ── 15. Course reminder ───────────────────────────────────────────────────────
def send_course_reminder_email(name: str, email: str, course_name: str,
                                step: int = 0, total_steps: int = 0,
                                days_since_last: int = 0) -> None:
    """
    Remind a learner they have an incomplete course to finish.
    Sent at most once every 4 days per learner by the automation scheduler.
    """
    first       = name.split()[0] if name else "Learner"
    site        = _frontend_url()
    pct         = round((step / total_steps) * 100) if total_steps else 0
    progress_bar = (
        f"<div style='background:#e2e8f0;border-radius:8px;height:12px;margin:10px 0;'>"
        f"<div style='background:linear-gradient(90deg,{PRIMARY},{SECONDARY});"
        f"width:{pct}%;height:12px;border-radius:8px;'></div></div>"
    )
    idle_note = (
        f"<p style='color:#DC2626;font-size:0.88rem;margin:0 0 10px;'>"
        f"&#9200; You haven't touched this course in <strong>{days_since_last} days</strong>.</p>"
        if days_since_last >= 3 else ""
    )
    step_info = (
        f"<strong>Step {step} of {total_steps}</strong> &nbsp;({pct}% complete)<br/>"
        + progress_bar
        if step and total_steps else ""
    )
    details = (
        "&#128218;&nbsp;Course: <strong>" + course_name + "</strong><br/>"
        + step_info
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        + idle_note
        + "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 10px;'>"
          "&#128218; Your course is waiting for you!</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 14px;'>"
        "Sir. Tega is holding your place in <strong>" + course_name + "</strong>. "
        "Just a few more steps and you will have completed it — don't stop now!</p>"
        + _box(details)
        + _cta("&#9654;&#65039; Continue Course", site + "/?panel=courses")
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "You've got this! 💪<br/>"
          "<strong style='color:" + PRIMARY + ";'>Sir. Tega</strong></p>"
    )
    html = _shell(body, f"Your course '{course_name}' is waiting — keep going!")
    text = (
        f"Hi {first},\n\nYou have an incomplete course: {course_name}.\n"
        + (f"Progress: Step {step} of {total_steps} ({pct}%)\n" if step and total_steps else "")
        + f"\nContinue learning: {site}/?panel=courses\n\n-- Sir. Tega & MyPy Tutor Team"
    )
    _dispatch_async(email, f"📚 Your course '{course_name}' is waiting for you!",
                    html, text, "course_reminder")


# ── 16. Assignment reminder ───────────────────────────────────────────────────
def send_assignment_reminder_email(name: str, email: str,
                                    pending_count: int,
                                    assignment_titles: list[str] | None = None) -> None:
    """
    Remind a learner they have pending assignments to submit.
    Sent at most once every 3 days per learner.
    """
    first   = name.split()[0] if name else "Learner"
    site    = _frontend_url()
    titles  = assignment_titles or []
    count   = pending_count or len(titles)

    assignments_html = ""
    if titles:
        items = "".join(
            f"<li style='margin:4px 0;color:#1e293b;'>{t}</li>"
            for t in titles[:5]
        )
        assignments_html = (
            f"<ul style='padding-left:18px;margin:8px 0;'>{items}</ul>"
            + (f"<p style='color:#64748b;font-size:0.82rem;'>...and {count - 5} more</p>"
               if count > 5 else "")
        )

    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:#D97706;font-size:1.2rem;margin:0 0 10px;'>"
        "&#9997;&#65039; You have pending assignments!</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 14px;'>"
        "You have <strong>" + str(count) + " pending assignment"
        + ("s" if count != 1 else "") + "</strong> that need"
        + ("" if count == 1 else "s") + " your submission. "
        "Sir. Tega is ready to review your work and give you detailed feedback.</p>"
        + _box(
            "<strong>Pending assignment" + ("s" if count != 1 else "") + ":</strong>"
            + assignments_html,
            bg="#fffbeb", border="#D97706"
        )
        + _cta("&#9997;&#65039; Submit Assignments", site + "/?panel=assignments",
               color="#D97706")
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "Submitting keeps your learning momentum going!<br/>"
          "<strong style='color:" + PRIMARY + ";'>Sir. Tega</strong></p>"
    )
    html = _shell(body, f"You have {count} pending assignment{'s' if count != 1 else ''} — submit today!")
    text = (
        f"Hi {first},\n\n"
        f"You have {count} pending assignment{'s' if count != 1 else ''} on MyPy Tutor.\n"
        + ("\n".join(f"- {t}" for t in titles[:5]) + "\n" if titles else "")
        + f"\nSubmit your work: {site}/?panel=assignments\n\n-- Sir. Tega & MyPy Tutor Team"
    )
    _dispatch_async(email,
                    f"✏️ {count} pending assignment{'s' if count != 1 else ''} waiting for your submission",
                    html, text, "assignment_reminder")


# ── 17. Weekend motivation ────────────────────────────────────────────────────
def send_weekend_motivation_email(name: str, email: str,
                                   xp: int = 0, current_course: str = "") -> None:
    """
    Motivational email sent on Saturday mornings (WAT) to encourage weekend learning.
    Sent at most once per week per learner.
    """
    first  = name.split()[0] if name else "Learner"
    site   = _frontend_url()
    xp_str = (
        "You are sitting on <strong style='color:" + GOLD + ";'>" + "{:,}".format(xp)
        + " XP</strong> — let's add to that total this weekend!"
        if xp else "The weekend is a great time to build your Python skills!"
    )
    course_hint = (
        "<p style='color:#475569;line-height:1.7;margin:0 0 12px;'>"
        "&#128204; Pick up where you left off: <strong>" + current_course + "</strong></p>"
        if current_course else ""
    )
    weekend_ideas = (
        "&#128218;&nbsp;Complete one course lesson (just 10 minutes!)<br/>"
        "&#127919;&nbsp;Take a quiz and earn some XP<br/>"
        "&#9997;&#65039;&nbsp;Submit a pending assignment<br/>"
        "&#128161;&nbsp;Ask Sir. Tega a Python question you've been curious about"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.2rem;margin:0 0 10px;'>"
        "&#127774; Happy Weekend! Make it count. &#128013;</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 14px;'>" + xp_str + "</p>"
        + course_hint
        + _box("<strong>Weekend learning ideas:</strong><br/>" + weekend_ideas,
               bg="#f0fdf4", border="#16A34A")
        + _cta("&#128640; Learn This Weekend", site)
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "Even one lesson this weekend keeps your momentum going.<br/>"
          "<strong style='color:" + PRIMARY + ";'>Sir. Tega &amp; The MyPy Tutor Team</strong></p>"
        + "<p style='color:#94a3b8;font-size:0.7rem;margin-top:16px;'>"
          "To stop receiving reminders, reply with 'unsubscribe'.</p>"
    )
    html = _shell(body, f"Happy Weekend, {first}! Sir. Tega has a lesson ready for you. 🐍")
    text = (
        f"Happy Weekend, {first}!\n\n{xp_str}\n\n"
        + (f"Continue: {current_course}\n\n" if current_course else "")
        + f"Start learning: {site}\n\n-- Sir. Tega & MyPy Tutor Team"
    )
    _dispatch_async(email,
                    f"🌴 Happy Weekend, {first}! Sir. Tega has a lesson ready for you.",
                    html, text, "weekend_motivation")


# ── 18. New month kickoff ─────────────────────────────────────────────────────
def send_new_month_email(name: str, email: str, month_name: str,
                          xp: int = 0, courses_done: int = 0) -> None:
    """
    Celebratory/motivational email sent on the 1st of every month (WAT).
    Sets goals and celebrates progress from the previous month.
    Sent at most once per month per learner.
    """
    first = name.split()[0] if name else "Learner"
    site  = _frontend_url()

    stats_html = ""
    if xp or courses_done:
        parts = []
        if xp:          parts.append(f"&#11088;&nbsp;<strong style='color:{GOLD};'>{xp:,} XP</strong> earned so far")
        if courses_done: parts.append(f"&#128218;&nbsp;<strong>{courses_done}</strong> course{'s' if courses_done != 1 else ''} completed")
        stats_html = _box("<br/>".join(parts), bg="#fffbeb", border=GOLD)

    goals = (
        "&#128218;&nbsp;Start or complete a new course<br/>"
        "&#127919;&nbsp;Aim for at least 3 quizzes this month<br/>"
        "&#9997;&#65039;&nbsp;Submit all pending assignments<br/>"
        "&#127942;&nbsp;Work toward your next certificate"
    )
    body = (
        "<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>" + first + "</strong>,</p>"
        "<h2 style='color:" + PRIMARY + ";font-size:1.3rem;margin:0 0 10px;'>"
        "&#127882; New month, new goals — Happy " + month_name + "!</h2>"
        "<p style='color:#475569;line-height:1.7;margin:0 0 14px;'>"
        "A brand new month means a fresh opportunity to level up your Python and AI skills. "
        "Sir. Tega is here every step of the way — let's make <strong>" + month_name
        + "</strong> your best learning month yet!</p>"
        + stats_html
        + _box("<strong>Your " + month_name + " goals:</strong><br/>" + goals,
               bg="#f0f7ff", border=PRIMARY)
        + _cta("&#128640; Start " + month_name + " Strong", site)
        + "<p style='color:#64748b;font-size:0.82rem;'>"
          "New month, same great tutor — Sir. Tega is ready for you! 🐍<br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
        + "<p style='color:#94a3b8;font-size:0.7rem;margin-top:16px;'>"
          "To stop receiving these messages, reply with 'unsubscribe'.</p>"
    )
    html = _shell(body, f"Happy {month_name}, {first}! New month, new goals — let's go! 🚀")
    text = (
        f"Happy {month_name}, {first}!\n\n"
        "A new month means a fresh chance to level up your Python skills.\n"
        + (f"Your XP so far: {xp:,}\n" if xp else "")
        + (f"Courses completed: {courses_done}\n" if courses_done else "")
        + f"\nStart learning: {site}\n\n-- Sir. Tega & MyPy Tutor Team"
    )
    _dispatch_async(email,
                    f"🎊 Happy {month_name}! New month, new Python goals — Sir. Tega is ready.",
                    html, text, "new_month")
