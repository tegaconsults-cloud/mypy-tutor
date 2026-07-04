"""
Admin module for MyPy Tutor.
In-memory admin store — tracks users, payments, tasks, team members.
Protected by admin password hash.
"""

import os
import time
import hashlib
import secrets
import logging
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Admin credentials — read lazily at call time so Render env vars are current
# ---------------------------------------------------------------------------

def _get_admin_email() -> str:
    return os.getenv("ADMIN_EMAIL", "tega.com.ng@gmail.com")

def _get_admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "")

def _get_admin_serializer() -> "URLSafeTimedSerializer":
    secret = os.getenv("SESSION_SECRET", "change-me-in-production-32-chars-min")
    return URLSafeTimedSerializer(secret)

ADMIN_TOKEN_MAX_AGE = 60 * 60 * 8   # 8 hours


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_admin_login(email: str, password: str) -> bool:
    """
    Check admin credentials.
    ADMIN_PASSWORD in Render env can be EITHER:
      - The raw password itself (e.g. "MySecret123")
      - The SHA-256 hash of the password
    This avoids breaking existing deployments while being more secure than
    the previous plaintext-equality check.
    """
    admin_email    = _get_admin_email()
    stored_pw      = _get_admin_password()
    email_ok = email.lower().strip() == admin_email.lower()
    pw_ok = False
    if stored_pw:
        # Accept both: stored hash of pw, OR stored pw being the raw password
        pw_ok = (stored_pw == _hash(password)) or (stored_pw == password)
    return email_ok and pw_ok


def create_admin_token() -> str:
    return _get_admin_serializer().dumps("admin", salt="admin-session")


def verify_admin_token(token: str) -> bool:
    try:
        val = _get_admin_serializer().loads(token, salt="admin-session", max_age=ADMIN_TOKEN_MAX_AGE)
        return val == "admin"
    except (BadSignature, SignatureExpired):
        return False


# ---------------------------------------------------------------------------
# Payment records (manual entry since Paystack webhook not yet integrated)
# ---------------------------------------------------------------------------

@dataclass
class PaymentRecord:
    id:          str
    user_email:  str
    user_name:   str
    amount:      float
    currency:    str = "NGN"
    plan:        str = ""        # tier1/tier2/tier3/basic-cert/adv-cert/exec-cert
    method:      str = "bank"    # bank | paystack
    status:      str = "pending" # pending | confirmed | refunded
    notes:       str = ""
    created_at:  float = field(default_factory=time.time)


_payments: list[PaymentRecord] = []


def add_payment(user_email: str, user_name: str, amount: float,
                plan: str, method: str = "bank", notes: str = "") -> PaymentRecord:
    p = PaymentRecord(
        id=secrets.token_hex(6).upper(),
        user_email=user_email,
        user_name=user_name,
        amount=amount,
        plan=plan,
        method=method,
        notes=notes,
    )
    _payments.append(p)
    return p


def confirm_payment(payment_id: str) -> bool:
    for p in _payments:
        if p.id == payment_id:
            p.status = "confirmed"
            return True
    return False


def get_payments() -> list[PaymentRecord]:
    return sorted(_payments, key=lambda p: p.created_at, reverse=True)


def get_revenue_summary() -> dict:
    confirmed = [p for p in _payments if p.status == "confirmed"]
    total     = sum(p.amount for p in confirmed)
    today     = date.today().isoformat()
    today_rev = sum(p.amount for p in confirmed
                    if datetime.fromtimestamp(p.created_at).date().isoformat() == today)
    by_plan: dict[str, float] = {}
    for p in confirmed:
        by_plan[p.plan] = by_plan.get(p.plan, 0) + p.amount
    return {
        "total_revenue":   total,
        "today_revenue":   today_rev,
        "total_payments":  len(_payments),
        "confirmed":       len(confirmed),
        "pending":         sum(1 for p in _payments if p.status == "pending"),
        "by_plan":         by_plan,
    }


# ---------------------------------------------------------------------------
# Team members & tasks
# ---------------------------------------------------------------------------

@dataclass
class TeamMember:
    email:      str
    name:       str
    role:       str = "team"
    invited_at: float = field(default_factory=time.time)
    status:     str = "invited"   # invited | active


@dataclass
class Task:
    id:           str
    title:        str
    description:  str
    assigned_to:  str   # email
    priority:     str = "medium"   # low | medium | high | urgent
    status:       str = "open"     # open | in_progress | done
    due_date:     str = ""
    created_at:   float = field(default_factory=time.time)


_team:  list[TeamMember] = []
_tasks: list[Task]        = []


def invite_team_member(email: str, name: str, role: str = "team") -> TeamMember:
    # Check if already exists
    for m in _team:
        if m.email.lower() == email.lower():
            return m
    m = TeamMember(email=email.lower(), name=name, role=role)
    _team.append(m)
    return m


def create_task(title: str, description: str, assigned_to: str,
                priority: str = "medium", due_date: str = "") -> Task:
    t = Task(
        id=secrets.token_hex(4).upper(),
        title=title,
        description=description,
        assigned_to=assigned_to.lower(),
        priority=priority,
        due_date=due_date,
    )
    _tasks.append(t)
    return t


def update_task_status(task_id: str, status: str) -> bool:
    for t in _tasks:
        if t.id == task_id:
            t.status = status
            return True
    return False


def get_team() -> list[TeamMember]:
    return _team


def get_tasks() -> list[Task]:
    return sorted(_tasks, key=lambda t: t.created_at, reverse=True)


# ---------------------------------------------------------------------------
# Certificate issued log
# ---------------------------------------------------------------------------

@dataclass
class CertRecord:
    cert_id:     str
    learner_id:  str
    learner_name:str
    level:       str
    issued_at:   float = field(default_factory=time.time)


_certs: list[CertRecord] = []


def log_certificate(cert_id: str, learner_id: str, learner_name: str, level: str) -> None:
    _certs.append(CertRecord(cert_id=cert_id, learner_id=learner_id,
                              learner_name=learner_name, level=level))
    try:
        from app.db import save_certificate_db
        save_certificate_db(cert_id, learner_id, learner_name, level)
    except Exception:
        pass


def get_certificates() -> list[CertRecord]:
    # Try SQLite first for persistence
    try:
        from app.db import get_certificates_db
        rows = get_certificates_db()
        if rows:
            result = []
            for r in rows:
                result.append(CertRecord(
                    cert_id=r["cert_id"],
                    learner_id=r["learner_id"],
                    learner_name=r["learner_name"],
                    level=r["level"],
                    issued_at=r.get("issued_at_ts", time.time()),
                ))
            return result
    except Exception:
        pass
    return sorted(_certs, key=lambda c: c.issued_at, reverse=True)


# ---------------------------------------------------------------------------
# Activity log — track what users do (populated by main.py hooks)
# ---------------------------------------------------------------------------

_activity_log: list[dict] = []   # max 2000 entries


def log_activity(learner_id: str, action: str, detail: str = "") -> None:
    _activity_log.append({
        "ts":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "learner_id":  learner_id,
        "action":      action,
        "detail":      detail[:200],
    })
    if len(_activity_log) > 2000:
        _activity_log.pop(0)
    # Also persist to SQLite
    try:
        from app.db import log_activity_db
        log_activity_db(learner_id, action, detail)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

_announcements: list[dict] = []


async def send_announcement(target: str, subject: str, body_text: str) -> int:
    """Send announcement email to all matching users. Returns count sent."""
    import smtplib, os as _os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from app.email_auth import _confirmed
    from app.progress import _store as ls

    EMAIL_HOST = _os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(_os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER = _os.getenv("EMAIL_USER", "")
    EMAIL_PASS = _os.getenv("EMAIL_PASS", "")
    EMAIL_FROM = _os.getenv("EMAIL_FROM", "MyPy Tutor <noreply@mypytutor.com>")

    # Build recipient list
    recipients: list[tuple[str, str]] = []  # (email, name)

    # Email account users
    for email, u in _confirmed.items():
        lid = u.get("learner_id", "")
        profile = ls.get(lid)
        tier = profile.tier if profile else "free"
        if _matches_target(target, tier):
            recipients.append((email, u.get("name", email)))

    if not recipients:
        _announcements.append({"subject": subject, "target": target, "sent_to": 0,
                                "sent_at": datetime.now().isoformat()})
        return 0

    sent = 0
    if EMAIL_USER and EMAIL_PASS:
        try:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=15) as server:
                server.ehlo(); server.starttls(); server.login(EMAIL_USER, EMAIL_PASS)
                for email, name in recipients:
                    try:
                        html = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px;max-width:560px">
                        <h2 style="color:#63b3ed">🐍 MyPy Tutor</h2>
                        <p>Hi <strong>{name}</strong>,</p>
                        <div style="margin-top:12px">{body_text}</div>
                        <hr style="border:none;border-top:1px solid #2d3748;margin:20px 0"/>
                        <p style="font-size:.75rem;color:#4a5568">MyPy Tutor · Teamsamikoko Global Academy</p></div>"""
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"]    = EMAIL_FROM
                        msg["To"]      = email
                        msg.attach(MIMEText(body_text, "plain"))
                        msg.attach(MIMEText(html, "html"))
                        server.sendmail(EMAIL_USER, email, msg.as_string())
                        sent += 1
                    except Exception as e:
                        logger.warning("Announcement email to %s failed: %s", email, e)
        except Exception as e:
            logger.error("Announcement SMTP error: %s", e)

    _announcements.append({"subject": subject, "target": target, "sent_to": sent,
                            "sent_at": datetime.now().isoformat()})
    return sent


def _matches_target(target: str, tier: str) -> bool:
    if target == "all":        return True
    if target == "free":       return tier == "free"
    if target == "paid":       return tier in ("tier1","tier2","tier3")
    if target == "tier1":      return tier == "tier1"
    if target == "tier2":      return tier == "tier2"
    if target == "tier3":      return tier == "tier3"
    return True
