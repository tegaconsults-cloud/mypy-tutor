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
# In-memory stores
# ---------------------------------------------------------------------------

# { email -> UserEmailAccount }
_pending:   dict[str, dict] = {}   # awaiting confirmation
_confirmed: dict[str, dict] = {}   # confirmed users
# { learner_id -> UserEmailAccount }
_by_id:     dict[str, dict] = {}


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

    # Send welcome email
    _send_welcome(user_data["name"], email)

    return True, f"Email confirmed! Welcome to MyPy Tutor, {user_data['name']} 🎉"


def _send_welcome(name: str, email: str) -> None:
    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#0f1117;color:#e2e8f0;padding:32px;">
  <div style="max-width:520px;margin:0 auto;background:#1a202c;border-radius:16px;padding:32px;border:1px solid #2d3748;">
    <h1 style="color:#63b3ed;">🐍 Welcome to MyPy Tutor!</h1>
    <p style="color:#a0aec0;line-height:1.6;margin-top:12px;">
      Hi <strong style="color:#e2e8f0;">{name}</strong>, your account is confirmed and ready to go!
    </p>
    <p style="color:#a0aec0;line-height:1.6;margin-top:8px;">
      Start chatting, take quizzes, enrol in courses, and track your Python journey.
    </p>
    <a href="{APP_URL}"
       style="display:inline-block;margin-top:20px;background:#276749;color:#68d391;
              padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:bold;">
      🚀 Start Learning
    </a>
    <hr style="border:none;border-top:1px solid #2d3748;margin:20px 0;">
    <p style="color:#4a5568;font-size:0.75rem;">MyPy Tutor · Teamsamikoko Global Academy</p>
  </div>
</body>
</html>
"""
    text_body = (
        f"Hi {name},\n\nYour MyPy Tutor account is confirmed!\n"
        f"Start learning at: {APP_URL}\n\n— MyPy Tutor Team"
    )
    _send_email(email, "Welcome to MyPy Tutor! 🐍", html_body, text_body)


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
