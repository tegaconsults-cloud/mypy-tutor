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
    app  = _app_url()
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
        "<img src='" + app + "/static/icons/mypytutor_logo.jpg' alt='MyPy Tutor'"
        " width='56' height='56' style='display:block;width:56px;height:56px;object-fit:cover;'/>"
        "</div>"
        "<span style='font-family:Segoe UI,Arial,sans-serif;'>"
        "<span style='font-size:1.4rem;font-weight:900;color:" + GOLD + ";letter-spacing:0.04em;'>MYPY</span>"
        "<span style='font-size:1.4rem;font-weight:900;color:#fff;'> TUTOR</span>"
        "</span></div></td></tr></table>"
        "<p style='color:rgba(255,255,255,0.65);font-size:0.72rem;margin:8px 0 0;"
        "letter-spacing:0.1em;text-transform:uppercase;'>Learn Python. Build the Future.</p>"
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
        "&ldquo;Learn Smarter. Code Better. Build the Future.&rdquo;</p>"
        "<a href='" + app + "' style='color:#90c4ff;font-size:0.72rem;text-decoration:none;'>"
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
    app   = _app_url()
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
            "Sir. Tega is your AI Python tutor. Start learning at:\n" + app + "\n\n"
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
    app   = _app_url()
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
    first       = name.split()[0] if name else "Learner"
    app         = _app_url()
    verify_url  = app + "/verify/" + cert_id
    cert_url    = (app + "/certificate/" + cert_level
                   + "?name=" + name.replace(" ", "%20") + "&admin_view=false")
    label       = cert_level.title()
    details = (
        "<strong>Certificate Details</strong><br/>"
        "&#127885;&nbsp;Level: <strong>" + label + "</strong><br/>"
        "&#128218;&nbsp;Certificate ID: <code style='background:#e2e8f0;padding:2px 6px;"
        "border-radius:4px;'>" + cert_id + "</code><br/>"
        "&#9989;&nbsp;Issuer: Teamsamikoko Global Academy (Reg No: 3508656)<br/>"
        "&#128279;&nbsp;Verify: <a href='" + verify_url + "'>" + verify_url + "</a>"
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
          "font-size:0.95rem;padding:14px 36px;border-radius:10px;margin-right:10px;'>"
          "&#127891; View Certificate</a>"
          "<a href='" + verify_url + "' style='display:inline-block;background:" + PRIMARY + ";"
          "color:#fff;text-decoration:none;font-weight:700;font-size:0.95rem;"
          "padding:14px 36px;border-radius:10px;'>&#9989; Verify Online</a></div>"
        + "<p style='color:#64748b;font-size:0.85rem;'>Well done on this achievement!<br/>"
          "<strong style='color:" + PRIMARY + ";'>The MyPy Tutor Team</strong></p>"
    )
    html = _shell(body, "Your " + label + " Python Certificate is ready!")
    text = ("Dear " + first + ",\n\nYour " + label + " Certificate (ID: " + cert_id
            + ") is ready.\nView: " + cert_url + "\nVerify: " + verify_url
            + "\n\nIssued by Teamsamikoko Global Academy - Reg No: 3508656\n\n-- MyPy Tutor Team")
    _dispatch_async(email, "Your " + label + " Certificate is Ready!", html, text, "certificate")

# ── 6. Payment receipt ────────────────────────────────────────────────────────
def send_payment_receipt_email(name: str, email: str, amount: float,
                                plan: str, payment_id: str,
                                currency: str = "NGN") -> None:
    first = name.split()[0] if name else "Learner"
    app   = _app_url()
    from datetime import datetime as _dt
    date_str = _dt.utcnow().strftime("%d %B %Y")
    plan_labels = {
        "tier1": "Pro Learner - NGN 5,000/month",
        "tier2": "Career Builder - NGN 10,000/month",
        "tier3": "Elite - NGN 20,000/month",
        "basic-cert": "Basic Certificate - NGN 30,000",
        "adv-cert":   "Advanced Certificate - NGN 60,000",
        "exec-cert":  "Executive Certificate - NGN 100,000",
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
    app   = _app_url()
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
    app   = _app_url()
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
    app   = _app_url()
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
    app   = _app_url()
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
    first = name.split()[0] if name else "Learner"
    app   = _app_url()
    body  = (
        "<p style='color:#1e293b;margin:0 0 16px;'>Hi <strong>" + first + "</strong>,</p>"
        + body_html
        + _hr()
        + _cta("&#128640; Open MyPy Tutor", app)
        + "<p style='color:#94a3b8;font-size:0.78rem;margin:16px 0 0;'>Sent to: " + target_label + "</p>"
    )
    html = _shell(body, subject)
    text = "Hi " + first + ",\n\n" + subject + "\n\nOpen at: " + app + "\n\n-- MyPy Tutor Team"
    _dispatch_async(email, subject, html, text, "announcement")


def send_bulk_announcement(subject: str, body_html: str, body_text: str,
                            recipients: list, target_label: str = "All Users") -> int:
    """
    recipients: list of (email, name) tuples.
    Returns number of threads dispatched.
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
    app     = _app_url()
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
