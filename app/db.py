"""
SQLite persistence layer for MyPy Tutor.
Stores user progress, email accounts, and auth data in a local SQLite database.

On Render FREE tier: data persists within a session but resets on restart
  (ephemeral filesystem). For permanent persistence, upgrade to Render's
  persistent disk add-on ($7/mo) or use Supabase free tier.

On Render PAID tier with persistent disk mounted at /data:
  Set DB_PATH=/data/mypytutor.db in Render env vars.

For now this is FAR better than pure memory — survives deploys, multiple
  workers won't conflict because SQLite handles locking.
"""

import os
import json
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Use DB_PATH env var if set (for persistent disk), otherwise local file
DB_PATH = os.getenv("DB_PATH", "mypytutor.db")


@contextmanager
def get_db():
    """Context manager for SQLite connection with auto-commit."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent reads
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS learner_profiles (
            learner_id      TEXT PRIMARY KEY,
            tier            TEXT DEFAULT 'free',
            level           TEXT DEFAULT 'beginner',
            xp              INTEGER DEFAULT 0,
            badges          TEXT DEFAULT '[]',
            topics_seen     TEXT DEFAULT '[]',
            topic_progress  TEXT DEFAULT '{}',
            current_course  TEXT,
            course_step     INTEGER DEFAULT 0,
            completed_projects TEXT DEFAULT '[]',
            daily_prompts_used INTEGER DEFAULT 0,
            last_prompt_date TEXT DEFAULT '',
            updated_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS email_accounts (
            email           TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            learner_id      TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
            token           TEXT,
            confirmed       INTEGER DEFAULT 0,
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id      TEXT NOT NULL,
            action          TEXT NOT NULL,
            detail          TEXT DEFAULT '',
            ts              REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS certificates (
            cert_id         TEXT PRIMARY KEY,
            learner_id      TEXT NOT NULL,
            learner_name    TEXT NOT NULL,
            level           TEXT NOT NULL,
            issued_at       REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS payments (
            id              TEXT PRIMARY KEY,
            user_email      TEXT NOT NULL,
            user_name       TEXT NOT NULL,
            amount          REAL NOT NULL,
            currency        TEXT DEFAULT 'NGN',
            plan            TEXT NOT NULL,
            method          TEXT DEFAULT 'bank',
            status          TEXT DEFAULT 'pending',
            notes           TEXT DEFAULT '',
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS team_members (
            email           TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            role            TEXT DEFAULT 'team',
            status          TEXT DEFAULT 'invited',
            invited_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            assigned_to     TEXT NOT NULL,
            priority        TEXT DEFAULT 'medium',
            status          TEXT DEFAULT 'open',
            due_date        TEXT DEFAULT '',
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            subject         TEXT NOT NULL,
            target          TEXT NOT NULL,
            sent_to         INTEGER DEFAULT 0,
            sent_at         REAL DEFAULT (unixepoch())
        );
        """)
    logger.info("Database initialised at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Learner profile helpers
# ---------------------------------------------------------------------------

def load_profile(learner_id: str):
    """Load a learner profile from SQLite. Returns None if not found."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)
        ).fetchone()
    if not row:
        return None
    return dict(row)


def save_profile_db(learner_id: str, profile_dict: dict) -> None:
    """Upsert a learner profile to SQLite — persists ALL fields including tier."""
    with get_db() as conn:
        conn.execute("""
        INSERT INTO learner_profiles
          (learner_id,tier,level,xp,badges,topics_seen,topic_progress,
           current_course,course_step,completed_projects,
           daily_prompts_used,last_prompt_date,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,unixepoch())
        ON CONFLICT(learner_id) DO UPDATE SET
          tier=excluded.tier,
          level=excluded.level,
          xp=excluded.xp,
          badges=excluded.badges,
          topics_seen=excluded.topics_seen,
          topic_progress=excluded.topic_progress,
          current_course=excluded.current_course,
          course_step=excluded.course_step,
          completed_projects=excluded.completed_projects,
          daily_prompts_used=excluded.daily_prompts_used,
          last_prompt_date=excluded.last_prompt_date,
          updated_at=unixepoch()
        """, (
            learner_id,
            profile_dict.get("tier", "free"),
            profile_dict.get("level", "beginner"),
            profile_dict.get("xp", 0),
            json.dumps(profile_dict.get("badges", [])),
            json.dumps(profile_dict.get("topics_seen", [])),
            json.dumps(profile_dict.get("topic_progress", {})),
            profile_dict.get("current_course"),
            profile_dict.get("current_course_step", 0),
            json.dumps(profile_dict.get("completed_projects", [])),
            profile_dict.get("daily_prompts_used", 0),
            profile_dict.get("last_prompt_date", ""),
        ))


def upgrade_tier_db(learner_id: str, tier: str) -> None:
    """Upgrade a specific learner's tier — called on payment confirmation."""
    with get_db() as conn:
        conn.execute(
            "UPDATE learner_profiles SET tier=?, updated_at=unixepoch() WHERE learner_id=?",
            (tier, learner_id)
        )
        # If profile doesn't exist yet, create it with the tier
        conn.execute("""
        INSERT OR IGNORE INTO learner_profiles (learner_id, tier)
        VALUES (?, ?)
        """, (learner_id, tier))


def get_all_learners() -> list[dict]:
    """Return all learner profiles from SQLite for admin use."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM learner_profiles ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for field in ('badges', 'topics_seen', 'completed_projects'):
            try:
                d[field] = json.loads(d.get(field) or '[]')
            except Exception:
                d[field] = []
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Email account helpers
# ---------------------------------------------------------------------------

def save_email_account(email: str, name: str, learner_id: str,
                        password_hash: str, token: str, confirmed: bool) -> None:
    with get_db() as conn:
        conn.execute("""
        INSERT INTO email_accounts (email,name,learner_id,password_hash,token,confirmed)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET
          name=excluded.name, password_hash=excluded.password_hash,
          token=excluded.token, confirmed=excluded.confirmed
        """, (email, name, learner_id, password_hash, token, int(confirmed)))


def load_email_account(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM email_accounts WHERE email=?", (email.lower(),)
        ).fetchone()
    return dict(row) if row else None


def confirm_email_db(email: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE email_accounts SET confirmed=1 WHERE email=?", (email.lower(),))


def get_all_confirmed_emails() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM email_accounts WHERE confirmed=1").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

def log_activity_db(learner_id: str, action: str, detail: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO activity_log (learner_id,action,detail) VALUES (?,?,?)",
            (learner_id, action, detail[:200])
        )
        # Keep only last 2000 entries
        conn.execute(
            "DELETE FROM activity_log WHERE id NOT IN "
            "(SELECT id FROM activity_log ORDER BY id DESC LIMIT 2000)"
        )


def get_activity_log(limit: int = 200) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(d["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

def save_certificate_db(cert_id: str, learner_id: str, learner_name: str, level: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO certificates (cert_id,learner_id,learner_name,level) VALUES (?,?,?,?)",
            (cert_id, learner_id, learner_name, level)
        )


def get_certificates_db() -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM certificates ORDER BY issued_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at"] = _dt.datetime.fromtimestamp(d["issued_at"]).isoformat()
        result.append(d)
    return result
