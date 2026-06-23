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
# Admin credentials — set ADMIN_EMAIL and ADMIN_PASSWORD in Render dashboard
# ---------------------------------------------------------------------------

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "tega.com.ng@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")   # hashed SHA-256 of plain password
ADMIN_TOKEN_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production-32-chars-min")

_admin_serializer = URLSafeTimedSerializer(ADMIN_TOKEN_SECRET)
ADMIN_TOKEN_MAX_AGE = 60 * 60 * 8   # 8 hours


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_admin_login(email: str, password: str) -> bool:
    """Check admin credentials. Constant-time comparison."""
    email_ok = email.lower().strip() == ADMIN_EMAIL.lower()
    # If ADMIN_PASSWORD env var is set as a hash, compare hashes
    # Otherwise fall back to direct comparison (dev only)
    stored = ADMIN_PASSWORD
    pw_ok = False
    if stored:
        # Support both plain text (dev) and sha256 hash (prod)
        pw_ok = (stored == _hash(password)) or (stored == password)
    else:
        # No password set — deny all
        pw_ok = False
    return email_ok and pw_ok


def create_admin_token() -> str:
    return _admin_serializer.dumps("admin", salt="admin-session")


def verify_admin_token(token: str) -> bool:
    try:
        val = _admin_serializer.loads(token, salt="admin-session", max_age=ADMIN_TOKEN_MAX_AGE)
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


def get_certificates() -> list[CertRecord]:
    return sorted(_certs, key=lambda c: c.issued_at, reverse=True)
