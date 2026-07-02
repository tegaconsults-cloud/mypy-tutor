"""
Email sign-up + confirmation for MyPy Tutor.

Uses Python stdlib smtplib + Gmail SMTP — no extra packages, free tier safe.

Required env vars (set in Render dashboard):
    EMAIL_HOST      smtp.gmail.com
    EMAIL_PORT      587
    EMAIL_USER      your-gmail@gmail.com
    EMAIL_PASS      your-gmail-app-password   (NOT your normal password — use App Passwords)
    EMAIL_FROM      MyPy Tutor <your-gmail@gmail.com>
    APP_URL         https://mypy-tutor.onrender.com

To create a Gmail App Password:
    Google Account → Security → 2-Step Verification → App passwords
"""

import os
import time
import secrets
import logging
import smtplib
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMAIL_HOST    = os.getenv("EMAIL_HOST",   "smtp.gmail.com")
EMAIL_PORT    = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER    = os.getenv("EMAIL_USER",   "")
EMAIL_PASS    = os.getenv("EMAIL_PASS",   "")
EMAIL_FROM    = os.getenv("EMAIL_FROM",   "MyPy Tutor <noreply@mypytutor.com>")
APP_URL       = os.getenv("APP_URL",      "https://mypytutor.onrender.com")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production-32-chars-min")

_token_serializer = URLSafeTimedSerializer(SESSION_SECRET)
CONFIRM_MAX_AGE   = 60 * 60 * 24   # 24 hours

# ---------------------------------------------------------------------------
# In-memory stores (backed by SQLite via db.py)
# ---------------------------------------------------------------------------

# { email -> dict } — populated from SQLite on first access
_pending:   dict[str, dict] = {}   # awaiting confirmation (not in SQLite yet)
_confirmed: dict[str, dict] = {}   # confirmed users (cached from SQLite)
_by_id:     dict[str, dict] = {}   # { learner_id -> user_dict }


def _load_confirmed_from_db() -> None:
    """Load confirmed accounts from SQLite into memory on startup."""
    try:
        from app.db import get_all_confirmed_emails
        for row in get_all_confirmed_emails():
            email = row["email"]
            lid   = row["learner_id"]
            user  = {"name": row["name"], "email": email,
                     "learner_id": lid, "password_hash": row["password_hash"],
                     "token": row.get("token", "")}
            _confirmed[email] = user
            _by_id[lid] = user
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("DB load failed: %s", e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_learner_id(email: str) -> str:
    """Stable learner_id derived from email (prefix 'e_' to distinguish from Google)."""
    h = hashlib.sha256(email.lower().encode()).hexdigest()[:16]
    return f"e_{h}"


def _send_email(to: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success."""
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("Email not configured — skipping send to %s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_FROM
        msg["To"]      = to
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to, msg.as_string())
        logger.info("Email sent to %s", to)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


# ---------------------------------------------------------------------------
# Registration flow
# ---------------------------------------------------------------------------

def register_email(email: str, name: str, password_hash: str) -> tuple[bool, str]:
    """
    Start the email registration flow.
    Returns (success, message).
    """
    email = email.lower().strip()
    learner_id = _make_learner_id(email)

    if email in _confirmed:
        return False, "An account with this email already exists. Please sign in."

    # Generate confirmation token
    token = _token_serializer.dumps(email, salt="email-confirm")

    _pending[email] = {
        "name":          name,
        "email":         email,
        "learner_id":    learner_id,
        "password_hash": password_hash,
        "token":         token,
        "created_at":    time.time(),
    }

    confirm_url = f"{APP_URL}/auth/confirm?token={token}"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#0f1117;color:#e2e8f0;padding:32px;">
  <div style="max-width:520px;margin:0 auto;background:#1a202c;border-radius:16px;padding:32px;border:1px solid #2d3748;">
    <h1 style="color:#63b3ed;font-size:1.4rem;margin-bottom:8px;">🐍 MyPy Tutor</h1>
    <h2 style="color:#e2e8f0;font-size:1.1rem;margin-bottom:16px;">Confirm your email address</h2>
    <p style="color:#a0aec0;line-height:1.6;">Hi <strong style="color:#e2e8f0;">{name}</strong>,</p>
    <p style="color:#a0aec0;line-height:1.6;margin-top:8px;">
      Thanks for signing up! Click the button below to confirm your email and activate your account.
    </p>
    <a href="{confirm_url}"
       style="display:inline-block;margin-top:24px;background:#3182ce;color:#fff;
              padding:12px 28px;border-radius:10px;text-decoration:none;
              font-weight:bold;font-size:0.95rem;">
      ✅ Confirm Email Address
    </a>
    <p style="color:#4a5568;font-size:0.78rem;margin-top:24px;line-height:1.5;">
      This link expires in 24 hours. If you didn't create an account, you can safely ignore this email.
    </p>
    <hr style="border:none;border-top:1px solid #2d3748;margin:20px 0;">
    <p style="color:#4a5568;font-size:0.75rem;">
      MyPy Tutor · Teamsamikoko Global Academy
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Hi {name},\n\n"
        f"Confirm your MyPy Tutor account by visiting:\n{confirm_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"— MyPy Tutor Team"
    )

    sent = _send_email(email, "Confirm your MyPy Tutor account", html_body, text_body)

    if not sent:
        if not EMAIL_USER or not EMAIL_PASS:
            # Neither email credentials set — dev/test mode, auto-confirm
            logger.warning("DEV MODE: auto-confirming %s (email not configured)", email)
            return confirm_email_token(token)
        else:
            # Credentials configured but send failed — still create the account
            # but inform user the email may have failed
            logger.error("Email send failed for %s — account created but confirmation may not have arrived", email)
            return True, (
                f"✅ Account created for {email}! "
                "We tried to send a confirmation email — if it doesn't arrive within a few minutes, "
                "please contact support or try signing in directly."
            )

    return True, (
        f"✅ Confirmation email sent to {email}! "
        "Please check your inbox (and spam folder) and click the link to activate your account."
    )


def confirm_email_token(token: str) -> tuple[bool, str]:
    """
    Confirm an email token.
    Returns (success, message).
    On success, moves user from _pending to _confirmed.
    """
    try:
        email = _token_serializer.loads(token, salt="email-confirm", max_age=CONFIRM_MAX_AGE)
    except SignatureExpired:
        return False, "Confirmation link has expired. Please sign up again."
    except BadSignature:
        return False, "Invalid confirmation link."

    email = email.lower().strip()

    if email in _confirmed:
        return True, "Email already confirmed. You can sign in."

    user_data = _pending.get(email)
    if not user_data:
        return False, "No pending registration found for this email."

    _confirmed[email]              = user_data
    _by_id[user_data["learner_id"]] = user_data
    del _pending[email]

    # Persist to SQLite
    try:
        from app.db import save_email_account, confirm_email_db
        save_email_account(
            email=email,
            name=user_data["name"],
            learner_id=user_data["learner_id"],
            password_hash=user_data["password_hash"],
            token=user_data.get("token", ""),
            confirmed=True,
        )
    except Exception as exc:
        logger.warning("DB save failed for confirmed user: %s", exc)

    # Send welcome email
    _send_welcome(user_data["name"], email)

    return True, f"Email confirmed! Welcome to MyPy Tutor, {user_data['name']} 🎉"


def _send_welcome(name: str, email: str) -> None:
    first_name = name.split()[0] if name else "Learner"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0d2b6e 0%,#1a3f9a 100%);border-radius:14px 14px 0 0;padding:32px 40px;text-align:center;">
    <div style="font-size:2.2rem;margin-bottom:6px;">🐍</div>
    <h1 style="color:#ffffff;font-size:1.5rem;margin:0;letter-spacing:0.04em;">MyPy Tutor</h1>
    <p style="color:rgba(255,255,255,0.7);font-size:0.75rem;margin:6px 0 0;letter-spacing:0.12em;text-transform:uppercase;">Powered by TeamTega Technologies Limited</p>
  </td></tr>

  <!-- Body -->
  <tr><td style="background:#ffffff;padding:36px 40px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">

    <p style="font-size:1rem;color:#1a202c;margin:0 0 16px;">Dear <strong>{first_name}</strong>,</p>
    <h2 style="color:#0d2b6e;font-size:1.3rem;margin:0 0 12px;">Welcome to MyPy Tutor!</h2>

    <p style="color:#4a5568;line-height:1.7;margin:0 0 14px;">
      We're excited to have you join a growing community of learners who are mastering Python through personalized, AI-powered learning.
    </p>
    <p style="color:#4a5568;line-height:1.7;margin:0 0 20px;">
      MyPy Tutor is more than an online Python course — it's an intelligent learning platform designed to help you build real-world programming skills at your own pace. Whether you're taking your first steps into coding or advancing into artificial intelligence, data science, databases, or automation, MyPy Tutor is here to guide you every step of the way.
    </p>

    <!-- What to expect -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8faff;border-radius:10px;border:1px solid #e2e8f0;padding:20px 24px;margin-bottom:20px;">
    <tr><td>
      <h3 style="color:#0d2b6e;font-size:0.95rem;margin:0 0 14px;letter-spacing:0.04em;">What You Can Expect</h3>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>🤖 Sir. Tega AI Tutor</strong> — Your personal AI instructor that explains concepts clearly, answers your questions, debugs your code, and adapts lessons to your learning needs.</p>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>📚 Structured Learning</strong> — Access comprehensive Python courses covering everything from the fundamentals to advanced topics.</p>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>📈 Personalized Progress Tracking</strong> — Your learning history, achievements, and knowledge gaps are securely stored so you can continue exactly where you left off.</p>
      <p style="margin:0;color:#2d3748;line-height:1.6;"><strong>🏆 Professional Certification</strong> — Complete your learning journey and earn verifiable certificates issued by Teamsamikoko Global Academy.</p>
    </td></tr>
    </table>

    <!-- About TSA -->
    <h3 style="color:#0d2b6e;font-size:0.92rem;margin:0 0 8px;">About Teamsamikoko Global Academy</h3>
    <p style="color:#4a5568;line-height:1.7;font-size:0.88rem;margin:0 0 16px;">
      Teamsamikoko Global Academy is a registered educational institution committed to equipping individuals with practical digital, technical, entrepreneurial, and professional skills needed to thrive in today's world. Our mission is to make high-quality technology education accessible, affordable, and impactful while preparing learners for global opportunities through practical training and recognized certifications.
    </p>

    <!-- About TTL -->
    <h3 style="color:#0d2b6e;font-size:0.92rem;margin:0 0 8px;">About TeamTega Technologies Limited</h3>
    <p style="color:#4a5568;line-height:1.7;font-size:0.88rem;margin:0 0 16px;">
      TeamTega Technologies Limited is the technology company behind the MyPy Tutor platform. We specialize in building innovative software solutions powered by Artificial Intelligence, automation, cloud technologies, and modern web development. Our goal is to develop intelligent digital products that transform education, businesses, healthcare, and public services across Africa and beyond.
    </p>

    <p style="color:#4a5568;line-height:1.7;font-size:0.88rem;margin:0 0 20px;">
      Together, Teamsamikoko Global Academy and TeamTega Technologies Limited combine educational excellence with cutting-edge technology to create a smarter and more personalized learning experience.
    </p>

    <!-- Get started -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7ff;border-radius:10px;border-left:4px solid #0d2b6e;padding:18px 22px;margin-bottom:24px;">
    <tr><td>
      <h3 style="color:#0d2b6e;font-size:0.92rem;margin:0 0 10px;">Get Started Today</h3>
      <p style="color:#2d3748;margin:0 0 6px;line-height:1.6;font-size:0.88rem;">✅ Complete your profile</p>
      <p style="color:#2d3748;margin:0 0 6px;line-height:1.6;font-size:0.88rem;">✅ Start with your recommended Python course</p>
      <p style="color:#2d3748;margin:0 0 6px;line-height:1.6;font-size:0.88rem;">✅ Ask Sir. Tega questions whenever you need help</p>
      <p style="color:#2d3748;margin:0 0 6px;line-height:1.6;font-size:0.88rem;">✅ Practice consistently using the exercises and coding challenges</p>
      <p style="color:#2d3748;margin:0;line-height:1.6;font-size:0.88rem;">✅ Track your progress and unlock certificates as you advance</p>
    </td></tr>
    </table>

    <p style="color:#4a5568;line-height:1.7;font-size:0.88rem;margin:0 0 20px;">
      Learning Python is one of the best investments you can make for your future, and we're honoured to be part of your journey. Thank you for choosing MyPy Tutor. We wish you success as you learn, build, and innovate.
    </p>

    <!-- CTA Button -->
    <div style="text-align:center;margin:24px 0;">
      <a href="{APP_URL}" style="display:inline-block;background:linear-gradient(135deg,#0d2b6e,#1a3f9a);color:#ffffff;text-decoration:none;font-weight:bold;font-size:0.95rem;padding:14px 36px;border-radius:8px;letter-spacing:0.04em;box-shadow:0 4px 14px rgba(13,43,110,0.3);">
        🚀 Start Learning Now
      </a>
    </div>

    <p style="color:#718096;font-size:0.85rem;line-height:1.6;margin:0;">
      Warm regards,<br/>
      <strong style="color:#0d2b6e;">The MyPy Tutor Team</strong>
    </p>

  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#0d2b6e;border-radius:0 0 14px 14px;padding:20px 40px;text-align:center;">
    <p style="color:rgba(255,255,255,0.9);font-size:0.78rem;margin:0 0 6px;font-weight:600;">Powered by TeamTega Technologies Limited</p>
    <p style="color:rgba(255,255,255,0.7);font-size:0.72rem;margin:0 0 6px;">Certified by Teamsamikoko Global Academy · Reg No: 3508656</p>
    <p style="color:rgba(255,255,255,0.55);font-size:0.7rem;margin:0 0 8px;font-style:italic;">"Learn Smarter. Code Better. Build the Future."</p>
    <a href="{APP_URL}" style="color:#90c4ff;font-size:0.72rem;">{APP_URL.replace('https://','')}</a>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    text_body = f"""Dear {first_name},

Welcome to MyPy Tutor!

We're excited to have you join a growing community of learners mastering Python through personalized, AI-powered learning.

What You Can Expect:
- Sir. Tega AI Tutor: Your personal AI instructor
- Structured Learning: Comprehensive Python courses
- Progress Tracking: Your history stored securely
- Professional Certification: Certificates from Teamsamikoko Global Academy

Get Started Today:
1. Complete your profile
2. Start with your recommended Python course
3. Ask Sir. Tega questions whenever you need help
4. Practice with exercises and coding challenges
5. Track progress and unlock certificates

Start learning at: {APP_URL}

Warm regards,
The MyPy Tutor Team
Powered by TeamTega Technologies Limited
Certified by Teamsamikoko Global Academy
"Learn Smarter. Code Better. Build the Future."
"""
    _send_email(
        email,
        f"Welcome to MyPy Tutor, {first_name}! Your learning journey begins 🐍",
        html_body,
        text_body
    )


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------

import hashlib as _hashlib


def hash_password(password: str) -> str:
    """Simple SHA-256 hash — good enough for in-memory MVP, use bcrypt for production."""
    return _hashlib.sha256(password.encode()).hexdigest()


def sign_in_email(email: str, password: str) -> tuple[bool, Optional[dict], str]:
    """
    Attempt email/password sign-in.
    Returns (success, user_data, message).
    """
    email = email.lower().strip()
    if email in _pending and email not in _confirmed:
        return False, None, "Please confirm your email before signing in."

    user = _confirmed.get(email)
    if not user:
        return False, None, "No account found with this email. Please sign up."

    if user["password_hash"] != hash_password(password):
        return False, None, "Incorrect password."

    return True, user, "Signed in successfully."


def get_email_user_by_id(learner_id: str) -> Optional[dict]:
    return _by_id.get(learner_id)
