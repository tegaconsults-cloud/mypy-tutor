"""
Admin module for MyPy Tutor.
All persistent data (payments, team, tasks, announcements, certificates)
is stored in SQLite so it survives Render restarts.
In-memory fallbacks are kept for the rare case where SQLite is unavailable.
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
    return os.getenv("ADMIN_EMAIL", "")

def _get_admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "")

import secrets as _admin_secrets

# Per-process random fallback — not a publicly-known constant.
_ADMIN_RUNTIME_FALLBACK = _admin_secrets.token_hex(32)


def _get_admin_serializer() -> "URLSafeTimedSerializer":
    secret = os.getenv("SESSION_SECRET", _ADMIN_RUNTIME_FALLBACK)
    return URLSafeTimedSerializer(secret)

ADMIN_TOKEN_MAX_AGE = 60 * 60 * 8   # 8 hours


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_admin_login(email: str, password: str) -> bool:
    import hmac as _hmac
    admin_email = _get_admin_email()
    stored_pw   = _get_admin_password()
    if not admin_email or not stored_pw:
        return False
    # Use constant-time comparison for BOTH fields to prevent timing attacks.
    # Even email enumeration is prevented this way — always compare both.
    email_ok = _hmac.compare_digest(
        email.lower().strip().encode(), admin_email.lower().encode()
    )
    # Auto-detect whether ADMIN_PASSWORD is stored as plain text or SHA-256 hash.
    # A SHA-256 hex digest is always exactly 64 lowercase hex characters.
    import re as _re
    is_hashed = bool(_re.fullmatch(r'[0-9a-f]{64}', stored_pw))
    if is_hashed:
        pw_ok = _hmac.compare_digest(stored_pw.encode(), _hash(password).encode())
    else:
        pw_ok = _hmac.compare_digest(stored_pw.encode(), password.encode())
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
# Payment records — SQLite-backed, in-memory fallback
# ---------------------------------------------------------------------------

@dataclass
class PaymentRecord:
    id:          str
    user_email:  str
    user_name:   str
    amount:      float
    currency:    str = "NGN"
    plan:        str = ""
    method:      str = "bank"
    status:      str = "pending"
    notes:       str = ""
    created_at:  float = field(default_factory=time.time)


# In-memory fallback (used when SQLite unavailable)
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
    # Persist to SQLite first
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO payments "
                "(id,user_email,user_name,amount,currency,plan,method,status,notes) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (p.id, p.user_email, p.user_name, p.amount, p.currency,
                 p.plan, p.method, p.status, p.notes)
            )
    except Exception as e:
        logger.warning("add_payment SQLite write failed: %s", e)
        _payments.append(p)  # fallback to memory only
    else:
        _payments.append(p)  # also keep in memory for this session
    return p


def confirm_payment(payment_id: str) -> bool:
    # Update SQLite
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            cur = conn.execute(
                "UPDATE payments SET status='confirmed' WHERE id=?", (payment_id,)
            )
            if cur.rowcount > 0:
                # Also update in-memory cache
                for p in _payments:
                    if p.id == payment_id:
                        p.status = "confirmed"
                return True
    except Exception as e:
        logger.warning("confirm_payment SQLite failed: %s", e)
    # Fallback: update in memory only
    for p in _payments:
        if p.id == payment_id:
            p.status = "confirmed"
            return True
    return False


def get_payments() -> list[dict]:
    """Return all payments from SQLite (persistent). Falls back to in-memory."""
    try:
        from app.db import get_db as _gdb
        import datetime as _dt
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Convert unix timestamp to ISO string for the frontend
            try:
                d["created_at"] = _dt.datetime.fromtimestamp(float(d["created_at"])).isoformat()
            except Exception:
                pass
            result.append(d)
        return result
    except Exception as e:
        logger.warning("get_payments SQLite failed, using memory: %s", e)
        result = []
        for p in sorted(_payments, key=lambda x: x.created_at, reverse=True):
            result.append({
                "id": p.id, "user_email": p.user_email, "user_name": p.user_name,
                "amount": p.amount, "currency": p.currency, "plan": p.plan,
                "method": p.method, "status": p.status, "notes": p.notes,
                "created_at": datetime.fromtimestamp(p.created_at).isoformat(),
            })
        return result


def get_revenue_summary() -> dict:
    """Compute revenue summary from SQLite payments table."""
    try:
        from app.db import get_db as _gdb
        today = date.today().isoformat()
        with _gdb() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE status='confirmed'"
            ).fetchone()
            total_rev   = float(row[0] or 0)
            confirmed   = int(row[1] or 0)
            pending     = conn.execute(
                "SELECT COUNT(*) FROM payments WHERE status='pending'"
            ).fetchone()[0]
            total_pmts  = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
            today_rev   = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM payments "
                "WHERE status='confirmed' AND DATE(created_at,'unixepoch')=?", (today,)
            ).fetchone()[0]
            plan_rows = conn.execute(
                "SELECT plan, SUM(amount) FROM payments WHERE status='confirmed' GROUP BY plan"
            ).fetchall()
            by_plan = {r[0]: float(r[1]) for r in plan_rows}
        return {
            "total_revenue": total_rev,
            "today_revenue": float(today_rev or 0),
            "total_payments": total_pmts,
            "confirmed": confirmed,
            "pending": pending,
            "by_plan": by_plan,
        }
    except Exception as e:
        logger.warning("get_revenue_summary SQLite failed: %s", e)
        confirmed_list = [p for p in _payments if p.status == "confirmed"]
        total = sum(p.amount for p in confirmed_list)
        return {
            "total_revenue": total,
            "today_revenue": 0,
            "total_payments": len(_payments),
            "confirmed": len(confirmed_list),
            "pending": sum(1 for p in _payments if p.status == "pending"),
            "by_plan": {},
        }


# ---------------------------------------------------------------------------
# Team members — SQLite-backed
# ---------------------------------------------------------------------------

@dataclass
class TeamMember:
    email:      str
    name:       str
    role:       str = "team"
    invited_at: float = field(default_factory=time.time)
    status:     str = "invited"


_team: list[TeamMember] = []


def invite_team_member(email: str, name: str, role: str = "team") -> TeamMember:
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO team_members (email,name,role) VALUES (?,?,?)",
                (email.lower(), name, role)
            )
    except Exception as e:
        logger.warning("invite_team_member SQLite failed: %s", e)
    # Also update in-memory
    for m in _team:
        if m.email.lower() == email.lower():
            return m
    m = TeamMember(email=email.lower(), name=name, role=role)
    _team.append(m)
    return m


def get_team() -> list[dict]:
    """Return team members from SQLite."""
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            rows = conn.execute("SELECT * FROM team_members ORDER BY invited_at DESC").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("get_team SQLite failed: %s", e)
        return [{"email": m.email, "name": m.name, "role": m.role, "status": m.status} for m in _team]


# ---------------------------------------------------------------------------
# Tasks — SQLite-backed
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id:           str
    title:        str
    description:  str
    assigned_to:  str
    priority:     str = "medium"
    status:       str = "open"
    due_date:     str = ""
    created_at:   float = field(default_factory=time.time)


_tasks: list[Task] = []


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
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tasks (id,title,description,assigned_to,priority,status,due_date) "
                "VALUES (?,?,?,?,?,?,?)",
                (t.id, t.title, t.description, t.assigned_to, t.priority, t.status, t.due_date)
            )
    except Exception as e:
        logger.warning("create_task SQLite failed: %s", e)
    _tasks.append(t)
    return t


def update_task_status(task_id: str, status: str) -> bool:
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            cur = conn.execute(
                "UPDATE tasks SET status=? WHERE id=?", (status, task_id)
            )
            if cur.rowcount > 0:
                for t in _tasks:
                    if t.id == task_id:
                        t.status = status
                return True
    except Exception as e:
        logger.warning("update_task_status SQLite failed: %s", e)
    for t in _tasks:
        if t.id == task_id:
            t.status = status
            return True
    return False


def get_tasks() -> list[dict]:
    """Return tasks from SQLite."""
    try:
        from app.db import get_db as _gdb
        import datetime as _dt
        with _gdb() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["created_at"] = _dt.datetime.fromtimestamp(float(d["created_at"])).isoformat()
            except Exception:
                pass
            result.append(d)
        return result
    except Exception as e:
        logger.warning("get_tasks SQLite failed: %s", e)
        return [{"id": t.id, "title": t.title, "description": t.description,
                 "assigned_to": t.assigned_to, "priority": t.priority,
                 "status": t.status, "due_date": t.due_date} for t in _tasks]


# ---------------------------------------------------------------------------
# Certificate log — SQLite-backed (via db.py)
# ---------------------------------------------------------------------------

@dataclass
class CertRecord:
    cert_id:      str
    learner_id:   str
    learner_name: str
    level:        str
    issued_at:    float = field(default_factory=time.time)


_certs: list[CertRecord] = []


def log_certificate(cert_id: str, learner_id: str, learner_name: str, level: str) -> None:
    _certs.append(CertRecord(cert_id=cert_id, learner_id=learner_id,
                              learner_name=learner_name, level=level))
    try:
        from app.db import save_certificate_db
        save_certificate_db(cert_id, learner_id, learner_name, level)
    except Exception as e:
        logger.warning("log_certificate SQLite write failed: %s", e)


def get_certificates() -> list[dict]:
    """Return certificates from SQLite with correct issue dates."""
    try:
        from app.db import get_certificates_db
        rows = get_certificates_db()
        if rows:
            return rows   # already formatted with issued_at as ISO string
    except Exception as e:
        logger.warning("get_certificates SQLite failed: %s", e)
    # Fallback to in-memory
    return [
        {
            "cert_id":      c.cert_id,
            "learner_id":   c.learner_id,
            "learner_name": c.learner_name,
            "level":        c.level,
            "issued_at":    datetime.fromtimestamp(c.issued_at).isoformat(),
        }
        for c in sorted(_certs, key=lambda x: x.issued_at, reverse=True)
    ]


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

_activity_log: list[dict] = []


def log_activity(learner_id: str, action: str, detail: str = "") -> None:
    _activity_log.append({
        "ts":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "learner_id": learner_id,
        "action":     action,
        "detail":     detail[:200],
    })
    if len(_activity_log) > 2000:
        _activity_log.pop(0)
    try:
        from app.db import log_activity_db
        log_activity_db(learner_id, action, detail)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Announcements — SQLite-backed
# ---------------------------------------------------------------------------

_announcements: list[dict] = []


def _save_announcement_db(subject: str, target: str, sent_to: int) -> None:
    try:
        from app.db import get_db as _gdb
        with _gdb() as conn:
            conn.execute(
                "INSERT INTO announcements (subject,target,sent_to) VALUES (?,?,?)",
                (subject, target, sent_to)
            )
    except Exception as e:
        logger.warning("save_announcement_db failed: %s", e)


def get_announcements() -> list[dict]:
    """Return announcements from SQLite, falling back to in-memory."""
    try:
        from app.db import get_db as _gdb
        import datetime as _dt
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT * FROM announcements ORDER BY id DESC LIMIT 100"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["sent_at"] = _dt.datetime.fromtimestamp(float(d["sent_at"])).isoformat()
            except Exception:
                pass
            result.append(d)
        return result
    except Exception as e:
        logger.warning("get_announcements SQLite failed: %s", e)
        return list(reversed(_announcements))


async def send_announcement(target: str, subject: str, body_text: str) -> int:
    """
    Send announcement email to all matching users. Returns count sent.

    Source of truth: SQLite (persistent across Render restarts) — NOT the
    in-memory _confirmed / _store dicts, which are wiped on every Render
    restart and only contain users active since the last boot.
    Supabase is used as a final fallback if SQLite is also empty.
    """
    from app.db import get_db as _gdb

    seen_emails: set[str] = set()
    # { learner_id: (email, name, tier) }
    user_map: dict[str, tuple[str, str, str]] = {}

    # ── Source 1: learner_profiles — all users, carries email + tier ─────────────
    try:
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT learner_id, email, display_name, tier FROM learner_profiles"
            ).fetchall()
        for r in rows:
            lid   = (r["learner_id"] or "").strip()
            email = (r["email"] or "").lower().strip()
            name  = (r["display_name"] or "").strip()
            tier  = (r["tier"] or "free").strip()
            if lid and email and "@" in email:
                user_map[lid] = (email, name, tier)
    except Exception as exc:
        logger.warning("send_announcement: learner_profiles query failed: %s", exc)

    # ── Source 2: email_accounts — confirmed users, carries proper full name ──────
    try:
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT learner_id, email, name FROM email_accounts WHERE confirmed=1"
            ).fetchall()
        for r in rows:
            lid   = (r["learner_id"] or "").strip()
            email = (r["email"] or "").lower().strip()
            name  = (r["name"] or "").strip()
            if lid and email and "@" in email:
                existing = user_map.get(lid)
                tier     = existing[2] if existing else "free"
                # Prefer the proper full name from email_accounts
                best_name = name or (existing[1] if existing else "")
                user_map[lid] = (email, best_name, tier)
    except Exception as exc:
        logger.warning("send_announcement: email_accounts query failed: %s", exc)

    # ── Source 3: Supabase fallback (covers Render ephemeral-restart window) ──────
    if not user_map:
        logger.info("send_announcement: SQLite empty — falling back to Supabase")
        try:
            from app.supabase_client import get_supabase
            sb = get_supabase()
            if sb:
                res = sb.table("profiles").select("id,email,full_name").execute()
                for r in (res.data or []):
                    lid   = (r.get("id") or "").strip()
                    email = (r.get("email") or "").lower().strip()
                    name  = (r.get("full_name") or "").strip()
                    if lid and email and "@" in email:
                        user_map[lid] = (email, name, "free")
                # Overlay tiers from learner_progress table
                res2 = sb.table("learner_progress").select("learner_id,tier").execute()
                for r in (res2.data or []):
                    lid  = (r.get("learner_id") or "").strip()
                    tier = (r.get("tier") or "free").strip()
                    if lid in user_map:
                        e, n, _ = user_map[lid]
                        user_map[lid] = (e, n, tier)
        except Exception as exc:
            logger.warning("send_announcement: Supabase fallback failed: %s", exc)

    # ── Build deduplicated recipient list filtered by target tier ─────────────────
    recipients: list[tuple[str, str]] = []
    for lid, (email, name, tier) in user_map.items():
        if email in seen_emails:
            continue
        if _matches_target(target, tier):
            seen_emails.add(email)
            recipients.append((email, name or email.split("@")[0]))

    logger.info(
        "send_announcement: target=%s total_users=%d matching=%d",
        target, len(user_map), len(recipients),
    )

    if not recipients:
        _save_announcement_db(subject, target, 0)
        return 0

    try:
        from app.services.email_service import send_bulk_announcement
        sent = send_bulk_announcement(
            subject=subject,
            body_html=(
                "<p style='color:#475569;line-height:1.7;white-space:pre-wrap;'>"
                + body_text
                + "</p>"
            ),
            body_text=body_text,
            recipients=recipients,
            target_label=target,
        )
    except Exception as exc:
        logger.error("Announcement send failed: %s", exc)
        sent = 0

    record = {"subject": subject, "target": target, "sent_to": sent,
              "sent_at": datetime.now().isoformat()}
    _announcements.append(record)
    _save_announcement_db(subject, target, sent)
    return sent


def _matches_target(target: str, tier: str) -> bool:
    if target == "all":   return True
    if target == "free":  return tier == "free"
    if target == "paid":  return tier in ("tier1", "tier2", "tier3")
    return target == tier
