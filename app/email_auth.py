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
# Config — all values read lazily at call time so Render env vars are current
# ---------------------------------------------------------------------------

def _cfg(key: str, default: str = "") -> str:
    """Read env var at call time — never at import time — so Render values are current."""
    return os.getenv(key, default)

# Module-level APP_URL — kept as a patchable name for token URL construction.
APP_URL = "https://mypytutor.onrender.com"

def _get_session_secret() -> str:
    return os.getenv("SESSION_SECRET", "change-me-in-production-32-chars-min")

def _get_token_serializer() -> "URLSafeTimedSerializer":
    """Build a fresh serializer at call time so SESSION_SECRET is always current."""
    return URLSafeTimedSerializer(_get_session_secret())

CONFIRM_MAX_AGE = 60 * 60 * 24   # 24 hours

# ---------------------------------------------------------------------------
# In-memory stores (backed by SQLite via db.py)
# ---------------------------------------------------------------------------

# { email -> dict } — populated from SQLite on first access
_pending:   dict[str, dict] = {}   # awaiting confirmation (not in SQLite yet)
_confirmed: dict[str, dict] = {}   # confirmed users (cached from SQLite)
_by_id:     dict[str, dict] = {}   # { learner_id -> user_dict }


def _load_confirmed_from_db() -> None:
    """
    Load confirmed accounts into memory on startup.
    Priority:
      1. SQLite (fast, local — populated from previous runtime)
      2. Supabase (permanent cloud — repopulates SQLite if it was wiped by Render restart)
    """
    loaded = 0
    try:
        from app.db import get_all_confirmed_emails
        for row in get_all_confirmed_emails():
            email = row["email"]
            lid   = row["learner_id"]
            user  = {
                "name":          row["name"],
                "email":         email,
                "learner_id":    lid,
                "password_hash": row["password_hash"],
                "token":         row.get("token", ""),
            }
            _confirmed[email] = user
            _by_id[lid]       = user
            loaded += 1
    except Exception as e:
        logger.warning("SQLite load failed: %s", e)

    if loaded > 0:
        logger.info("Loaded %d confirmed accounts from SQLite", loaded)
        return  # SQLite is intact — no need to hit Supabase

    # SQLite is empty (Render ephemeral restart wiped the disk).
    # Recover from Supabase and repopulate SQLite at the same time.
    logger.info("SQLite empty — recovering email accounts from Supabase…")
    try:
        from app.supabase_client import sb_load_all_email_accounts
        from app.db import save_email_account
        accounts = sb_load_all_email_accounts()
        recovered = 0
        for acct in accounts:
            email = acct.get("email", "").lower()
            lid   = acct.get("learner_id", "")
            name  = acct.get("full_name", "")
            pw    = acct.get("password_hash", "")
            if not email or not lid:
                continue
            user = {
                "name":          name,
                "email":         email,
                "learner_id":    lid,
                "password_hash": pw,
                "token":         "",
            }
            _confirmed[email] = user
            _by_id[lid]       = user
            # Repopulate SQLite so subsequent reads are fast
            try:
                save_email_account(
                    email=email, name=name, learner_id=lid,
                    password_hash=pw, token="", confirmed=True,
                )
            except Exception as db_exc:
                logger.debug("SQLite repopulate failed for %s: %s", email, db_exc)
            recovered += 1
        logger.info("Recovered %d email accounts from Supabase", recovered)
    except Exception as exc:
        logger.warning("Supabase email recovery failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_learner_id(email: str) -> str:
    """Stable learner_id derived from email (prefix 'e_' to distinguish from Google)."""
    h = hashlib.sha256(email.lower().encode()).hexdigest()[:16]
    return f"e_{h}"


def _send_email(to: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Send an email via Gmail SMTP.
    - Reads env vars at call time (not import time) so Render values are current.
    - Runs in the calling thread; wrap in threading.Thread for non-blocking use.
    Returns True on success.
    """
    email_user = _cfg("EMAIL_USER")
    email_pass = _cfg("EMAIL_PASS")
    email_host = _cfg("EMAIL_HOST", "smtp.gmail.com")
    email_port = int(_cfg("EMAIL_PORT", "587"))
    email_from = _cfg("EMAIL_FROM", f"MyPy Tutor <{email_user}>")
    app_url    = _cfg("APP_URL", "https://mypytutor.onrender.com")

    # Patch module-level APP_URL so it stays current for token URLs
    global APP_URL
    if app_url:
        APP_URL = app_url

    if not email_user or not email_pass:
        logger.warning(
            "Email not configured (EMAIL_USER/EMAIL_PASS not set) — "
            "skipping send to %s. Set these in Render → Environment.", to
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = email_from or f"MyPy Tutor <{email_user}>"
        msg["To"]      = to
        msg["Reply-To"] = email_user
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html",  "utf-8"))

        with smtplib.SMTP(email_host, email_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(email_user, email_pass)
            server.sendmail(email_user, [to], msg.as_string())

        logger.info("✅ Email sent to %s (subject: %s)", to, subject)
        return True

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "❌ Gmail auth failed for %s — check EMAIL_PASS is a Gmail App Password "
            "(not your normal password): %s", email_user, exc
        )
        return False
    except smtplib.SMTPException as exc:
        logger.error("❌ SMTP error sending to %s: %s", to, exc)
        return False
    except Exception as exc:
        logger.error("❌ Failed to send email to %s: %s", to, exc)
        return False


def _send_email_async(to: str, subject: str, html_body: str, text_body: str) -> None:
    """Fire-and-forget email send in a daemon thread — never blocks the request."""
    import threading
    t = threading.Thread(
        target=_send_email,
        args=(to, subject, html_body, text_body),
        daemon=True,
        name=f"email-{to[:20]}",
    )
    t.start()


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
    token = _get_token_serializer().dumps(email, salt="email-confirm")

    _pending[email] = {
        "name":          name,
        "email":         email,
        "learner_id":    learner_id,
        "password_hash": password_hash,
        "token":         token,
        "created_at":    time.time(),
    }

    app_url     = _cfg("APP_URL", "https://mypytutor.onrender.com")
    confirm_url = f"{app_url}/auth/confirm?token={token}"

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

    # Send confirmation email in a background thread (non-blocking)
    _send_email_async(email, "Confirm your MyPy Tutor account", html_body, text_body)

    email_user = _cfg("EMAIL_USER")
    email_pass = _cfg("EMAIL_PASS")

    if not email_user or not email_pass:
        # Dev mode — no email credentials, auto-confirm immediately
        logger.warning("DEV MODE: auto-confirming %s (EMAIL_USER/EMAIL_PASS not set)", email)
        return confirm_email_token(token)

    return True, (
        f"✅ Confirmation email sent to {email}! "
        "Please check your inbox and spam folder, then click the link to activate your account."
    )


def confirm_email_token(token: str) -> tuple[bool, str]:
    """
    Confirm an email token.
    Returns (success, message).
    On success, moves user from _pending to _confirmed.
    """
    try:
        email = _get_token_serializer().loads(token, salt="email-confirm", max_age=CONFIRM_MAX_AGE)
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

    _confirmed[email]               = user_data
    _by_id[user_data["learner_id"]]  = user_data
    del _pending[email]

    # Persist to SQLite
    try:
        from app.db import save_email_account
        save_email_account(
            email=email,
            name=user_data["name"],
            learner_id=user_data["learner_id"],
            password_hash=user_data["password_hash"],
            token=user_data.get("token", ""),
            confirmed=True,
        )
    except Exception as exc:
        logger.warning("SQLite save failed for confirmed user: %s", exc)

    # Apply access code tier AFTER confirmation — prevents pre-confirmation abuse
    access_code = user_data.get("access_code", "")
    access_tier = user_data.get("access_tier", "")
    if access_code and access_tier:
        try:
            from app.db import validate_access_code, redeem_access_code, upgrade_tier_db
            code_rec = validate_access_code(access_code)
            if code_rec:
                redeemed = redeem_access_code(access_code, email, user_data["learner_id"])
                if redeemed:
                    upgrade_tier_db(user_data["learner_id"], access_tier)
                    logger.info("Access code %s applied for %s → %s", access_code, email, access_tier)
        except Exception as exc:
            logger.warning("Access code tier grant failed: %s", exc)

    # Mirror to Supabase — survives Render ephemeral restarts
    try:
        from app.supabase_client import sb_upsert_email_account
        sb_upsert_email_account(
            email=email,
            learner_id=user_data["learner_id"],
            full_name=user_data["name"],
            password_hash=user_data["password_hash"],
        )
    except Exception as exc:
        logger.warning("Supabase email account sync failed: %s", exc)

    # Send welcome email asynchronously (non-blocking)
    _send_email_async(
        user_data["email"],
        f"Welcome to MyPy Tutor, {user_data['name'].split()[0]}! Your learning journey begins 🐍",
        *_build_welcome_email(user_data["name"], user_data["email"])
    )

    return True, f"Email confirmed! Welcome to MyPy Tutor, {user_data['name']} 🎉"


def _build_welcome_email(name: str, email: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for the welcome email."""
    first_name = name.split()[0] if name else "Learner"
    app_url    = _cfg("APP_URL", "https://mypytutor.onrender.com")

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
  <tr><td style="background:linear-gradient(135deg,#0d2b6e 0%,#1a3f9a 100%);border-radius:14px 14px 0 0;padding:32px 40px;text-align:center;">
    <div style="font-size:2.2rem;margin-bottom:6px;">🐍</div>
    <h1 style="color:#ffffff;font-size:1.5rem;margin:0;">MyPy Tutor</h1>
    <p style="color:rgba(255,255,255,0.7);font-size:0.75rem;margin:6px 0 0;letter-spacing:0.12em;text-transform:uppercase;">Powered by TeamTega Technologies Limited</p>
  </td></tr>
  <tr><td style="background:#ffffff;padding:36px 40px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
    <p style="font-size:1rem;color:#1a202c;margin:0 0 16px;">Dear <strong>{first_name}</strong>,</p>
    <h2 style="color:#0d2b6e;font-size:1.3rem;margin:0 0 12px;">Welcome to MyPy Tutor!</h2>
    <p style="color:#4a5568;line-height:1.7;margin:0 0 14px;">We're excited to have you join a growing community of learners mastering Python through personalised, AI-powered learning.</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8faff;border-radius:10px;border:1px solid #e2e8f0;padding:20px 24px;margin-bottom:20px;">
    <tr><td>
      <h3 style="color:#0d2b6e;font-size:0.95rem;margin:0 0 14px;">What You Can Expect</h3>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>🤖 Sir. Tega AI Tutor</strong> — Your personal AI instructor that explains concepts clearly, debugs your code, and adapts to your learning needs.</p>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>📚 Structured Learning</strong> — Comprehensive Python courses from fundamentals to AI, data science, and databases.</p>
      <p style="margin:0 0 10px;color:#2d3748;line-height:1.6;"><strong>📈 Progress Tracking</strong> — Your history, achievements, and knowledge gaps are stored so you continue where you left off.</p>
      <p style="margin:0;color:#2d3748;line-height:1.6;"><strong>🏆 Professional Certification</strong> — Earn verifiable certificates issued by Teamsamikoko Global Academy.</p>
    </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7ff;border-radius:10px;border-left:4px solid #0d2b6e;padding:18px 22px;margin-bottom:24px;">
    <tr><td>
      <h3 style="color:#0d2b6e;font-size:0.92rem;margin:0 0 10px;">Get Started Today</h3>
      <p style="color:#2d3748;margin:0 0 5px;font-size:0.88rem;">✅ Start with your recommended Python course</p>
      <p style="color:#2d3748;margin:0 0 5px;font-size:0.88rem;">✅ Ask Sir. Tega anything about Python</p>
      <p style="color:#2d3748;margin:0 0 5px;font-size:0.88rem;">✅ Practice with exercises and coding challenges</p>
      <p style="color:#2d3748;margin:0;font-size:0.88rem;">✅ Track progress and unlock certificates as you advance</p>
    </td></tr>
    </table>
    <div style="text-align:center;margin:24px 0;">
      <a href="{app_url}" style="display:inline-block;background:linear-gradient(135deg,#0d2b6e,#1a3f9a);color:#ffffff;text-decoration:none;font-weight:bold;font-size:0.95rem;padding:14px 36px;border-radius:8px;">
        🚀 Start Learning Now
      </a>
    </div>
    <p style="color:#718096;font-size:0.85rem;line-height:1.6;margin:0;">
      Warm regards,<br/><strong style="color:#0d2b6e;">The MyPy Tutor Team</strong>
    </p>
  </td></tr>
  <tr><td style="background:#0d2b6e;border-radius:0 0 14px 14px;padding:20px 40px;text-align:center;">
    <p style="color:rgba(255,255,255,0.9);font-size:0.78rem;margin:0 0 4px;font-weight:600;">Powered by TeamTega Technologies Limited</p>
    <p style="color:rgba(255,255,255,0.7);font-size:0.72rem;margin:0 0 4px;">Certified by Teamsamikoko Global Academy · Reg No: 3508656</p>
    <p style="color:rgba(255,255,255,0.55);font-size:0.7rem;margin:0 0 6px;font-style:italic;">"Learn Smarter. Code Better. Build the Future."</p>
    <a href="{app_url}" style="color:#90c4ff;font-size:0.72rem;">{app_url.replace('https://','')}</a>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    text_body = f"""Dear {first_name},

Welcome to MyPy Tutor!

Sir. Tega is ready to teach you Python from basics to AI and data science.

Get started at: {app_url}

Warm regards,
The MyPy Tutor Team
Powered by TeamTega Technologies Limited
Certified by Teamsamikoko Global Academy · Reg No: 3508656
"Learn Smarter. Code Better. Build the Future."
"""
    return html_body, text_body


# Keep old name for any external callers
def _send_welcome(name: str, email: str) -> None:
    html, text = _build_welcome_email(name, email)
    _send_email_async(
        email,
        f"Welcome to MyPy Tutor, {name.split()[0]}! Your learning journey begins 🐍",
        html, text
    )


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------

import hashlib as _hashlib


def hash_password(password: str) -> str:
    """Hash password with bcrypt (cost 12). Brute-force resistant."""
    try:
        import bcrypt as _bcrypt
        return _bcrypt.hashpw(password.encode("utf-8"),
                               _bcrypt.gensalt(rounds=12)).decode("utf-8")
    except ImportError:
        # Fallback to SHA-256 if bcrypt not installed (should not happen on Render)
        logger.warning("bcrypt not available — falling back to SHA-256")
        return _hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, stored: str) -> bool:
    """
    Verify a password against a stored hash.
    Handles both bcrypt ($2b$...) and legacy SHA-256 hashes transparently.
    """
    if stored.startswith("$2"):
        try:
            import bcrypt as _bcrypt
            return _bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False
    # Legacy SHA-256
    return stored == _hashlib.sha256(plain.encode()).hexdigest()


def sign_in_email(email: str, password: str) -> tuple[bool, Optional[dict], str]:
    """
    Attempt email/password sign-in.
    Transparently upgrades legacy SHA-256 hashes to bcrypt on first successful login.
    Returns (success, user_data, message).
    """
    email = email.lower().strip()
    if email in _pending and email not in _confirmed:
        return False, None, "Please confirm your email before signing in."

    user = _confirmed.get(email)
    if not user:
        return False, None, "No account found with this email. Please sign up."

    if not verify_password(password, user["password_hash"]):
        return False, None, "Incorrect password."

    # Upgrade legacy SHA-256 to bcrypt transparently
    if not user["password_hash"].startswith("$2"):
        try:
            new_hash = hash_password(password)
            user["password_hash"] = new_hash
            lid = user.get("learner_id", "")
            if lid and lid in _by_id:
                _by_id[lid]["password_hash"] = new_hash
            from app.db import update_password_hash as _uph
            _uph(email, new_hash)
            from app.supabase_client import sb_update_email_password as _sep
            _sep(email, new_hash)
            logger.info("Upgraded SHA-256 -> bcrypt for %s", email)
        except Exception as exc:
            logger.debug("Hash upgrade failed (non-fatal): %s", exc)

    return True, user, "Signed in successfully."


def get_email_user_by_id(learner_id: str) -> Optional[dict]:
    return _by_id.get(learner_id)


# ---------------------------------------------------------------------------
# Password reset flow
# ---------------------------------------------------------------------------

RESET_MAX_AGE = 60 * 60  # 1 hour


def request_password_reset(email: str) -> tuple[bool, str]:
    """
    Generate a password reset token and send reset email.
    Always returns success message (no email enumeration).
    """
    email = email.lower().strip()
    user  = _confirmed.get(email)

    if user:
        token = _get_token_serializer().dumps(email, salt="pw-reset")
        try:
            from app.db import save_reset_token
            save_reset_token(token, email)
        except Exception as exc:
            logger.warning("Could not save reset token to DB: %s", exc)

        reset_url  = f"{_cfg('APP_URL', 'https://mypytutor.onrender.com')}/?auth=reset&token={token}"
        first_name = user.get("name", "Learner").split()[0]

        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#0f1117;color:#e2e8f0;padding:32px;">
  <div style="max-width:520px;margin:0 auto;background:#1a202c;border-radius:16px;
              padding:32px;border:1px solid #2d3748;">
    <h1 style="color:#63b3ed;font-size:1.4rem;margin-bottom:8px;">🐍 MyPy Tutor</h1>
    <h2 style="color:#e2e8f0;font-size:1.1rem;margin-bottom:16px;">Reset your password</h2>
    <p style="color:#a0aec0;line-height:1.6;">Hi <strong style="color:#e2e8f0;">{first_name}</strong>,</p>
    <p style="color:#a0aec0;line-height:1.6;margin-top:8px;">
      We received a request to reset the password for your MyPy Tutor account.
      Click the button below to set a new password.
    </p>
    <a href="{reset_url}"
       style="display:inline-block;margin-top:24px;background:#e53e3e;color:#fff;
              padding:12px 28px;border-radius:10px;text-decoration:none;
              font-weight:bold;font-size:0.95rem;">
      🔑 Reset My Password
    </a>
    <p style="color:#4a5568;font-size:0.78rem;margin-top:24px;line-height:1.5;">
      This link expires in <strong>1 hour</strong>. If you didn't request a password reset,
      you can safely ignore this email — your password will not change.
    </p>
    <hr style="border:none;border-top:1px solid #2d3748;margin:20px 0;">
    <p style="color:#4a5568;font-size:0.75rem;">
      MyPy Tutor · Teamsamikoko Global Academy
    </p>
  </div>
</body>
</html>"""

        text_body = (
            f"Hi {first_name},\n\n"
            f"Reset your MyPy Tutor password by visiting:\n{reset_url}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you didn't request this, ignore this email.\n\n"
            f"— MyPy Tutor Team"
        )
        _send_email_async(email, "Reset your MyPy Tutor password", html_body, text_body)

    # Always return success (prevents email enumeration attacks)
    return True, (
        "If an account exists for that email, a reset link has been sent. "
        "Please check your inbox and spam folder."
    )


def confirm_password_reset(token: str, new_password: str) -> tuple[bool, str]:
    """
    Validate reset token and update password.
    Returns (success, message).
    """
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."

    # Validate token signature first (fast, no DB needed)
    try:
        email = _get_token_serializer().loads(token, salt="pw-reset", max_age=RESET_MAX_AGE)
    except SignatureExpired:
        return False, "Reset link has expired. Please request a new one."
    except BadSignature:
        return False, "Invalid reset link."

    email = email.lower().strip()

    # Check DB: token must not have been used already
    try:
        from app.db import load_reset_token, mark_reset_token_used, update_password_hash
        record = load_reset_token(token)
        if not record:
            return False, "This reset link has already been used or is invalid."
        mark_reset_token_used(token)
        new_hash = hash_password(new_password)
        update_password_hash(email, new_hash)
        # Ensure Supabase stays in sync
        try:
            from app.supabase_client import sb_update_email_password
            sb_update_email_password(email, new_hash)
        except Exception:
            pass
    except Exception as exc:
        logger.error("Password reset DB error: %s", exc)
        return False, "Could not update password. Please try again."

    # Update in-memory cache
    if email in _confirmed:
        _confirmed[email]["password_hash"] = new_hash
        lid = _confirmed[email].get("learner_id")
        if lid and lid in _by_id:
            _by_id[lid]["password_hash"] = new_hash

    # Mirror updated password_hash to Supabase
    try:
        from app.supabase_client import sb_update_email_password
        sb_update_email_password(email, new_hash)
    except Exception as exc:
        logger.warning("Supabase password update failed: %s", exc)

    logger.info("Password reset successful for %s", email)
    return True, "Password updated successfully! You can now sign in with your new password."
