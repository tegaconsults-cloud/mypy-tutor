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
    """Create all tables then all indexes — order matters: indexes must come after tables."""
    with get_db() as conn:
        # ── PASS 1: All tables ───────────────────────────────────────────────
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

        CREATE TABLE IF NOT EXISTS password_resets (
            token           TEXT PRIMARY KEY,
            email           TEXT NOT NULL,
            created_at      REAL DEFAULT (unixepoch()),
            used            INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS prompt_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id      TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            intent          TEXT DEFAULT '',
            topic           TEXT DEFAULT '',
            ts              REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id      TEXT NOT NULL,
            topic           TEXT NOT NULL,
            question        TEXT NOT NULL,
            answer          TEXT NOT NULL,
            correct         INTEGER DEFAULT 0,
            score           INTEGER DEFAULT 0,
            ts              REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id              TEXT PRIMARY KEY,
            learner_id      TEXT NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL,
            course          TEXT DEFAULT '',
            status          TEXT DEFAULT 'pending',
            submission      TEXT DEFAULT '',
            feedback        TEXT DEFAULT '',
            score           INTEGER DEFAULT 0,
            submitted_at    REAL,
            reviewed_at     REAL,
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS referrals (
            code            TEXT PRIMARY KEY,
            owner_id        TEXT NOT NULL,
            owner_email     TEXT NOT NULL,
            uses            INTEGER DEFAULT 0,
            max_uses        INTEGER DEFAULT 50,
            reward_tier     TEXT DEFAULT 'tier1',
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS referral_uses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT NOT NULL,
            used_by_email   TEXT NOT NULL,
            used_by_id      TEXT NOT NULL,
            discount_pct    INTEGER DEFAULT 20,
            ts              REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS coupons (
            code            TEXT PRIMARY KEY,
            discount_pct    INTEGER NOT NULL,
            discount_flat   REAL DEFAULT 0,
            plan            TEXT DEFAULT 'any',
            max_uses        INTEGER DEFAULT 100,
            uses            INTEGER DEFAULT 0,
            expires_at      REAL DEFAULT 0,
            active          INTEGER DEFAULT 1,
            created_at      REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS coupon_uses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT NOT NULL,
            learner_id      TEXT NOT NULL,
            email           TEXT NOT NULL,
            amount_saved    REAL DEFAULT 0,
            ts              REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id              TEXT PRIMARY KEY,
            payment_id      TEXT NOT NULL,
            learner_id      TEXT NOT NULL,
            email           TEXT NOT NULL,
            name            TEXT NOT NULL,
            plan            TEXT NOT NULL,
            amount          REAL NOT NULL,
            currency        TEXT DEFAULT 'NGN',
            issued_at       REAL DEFAULT (unixepoch()),
            due_date        TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS access_codes (
            code            TEXT PRIMARY KEY,
            tier            TEXT NOT NULL,
            created_by      TEXT DEFAULT 'admin',
            sent_to_email   TEXT DEFAULT '',
            used_by_email   TEXT DEFAULT '',
            used_by_id      TEXT DEFAULT '',
            used            INTEGER DEFAULT 0,
            expires_at      REAL DEFAULT 0,
            created_at      REAL DEFAULT (unixepoch())
        );

        -- User editable profile (bio, location, website)
        CREATE TABLE IF NOT EXISTS user_profiles (
            learner_id   TEXT PRIMARY KEY,
            display_name TEXT DEFAULT '',
            bio          TEXT DEFAULT '',
            location     TEXT DEFAULT '',
            website      TEXT DEFAULT '',
            updated_at   REAL DEFAULT (unixepoch())
        );

        -- Individual course purchases (separate from tier bundles)
        CREATE TABLE IF NOT EXISTS course_purchases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id  TEXT NOT NULL,
            course_name TEXT NOT NULL,
            amount_ngn  REAL DEFAULT 0,
            payment_ref TEXT DEFAULT '',
            purchased_at REAL DEFAULT (unixepoch()),
            UNIQUE(learner_id, course_name)
        );
        """)

        # ── PASS 2: All indexes (tables guaranteed to exist now) ─────────────
        conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_prompt_history_learner
            ON prompt_history (learner_id, id);
        CREATE INDEX IF NOT EXISTS idx_quiz_attempts_learner
            ON quiz_attempts (learner_id);
        CREATE INDEX IF NOT EXISTS idx_activity_log_learner
            ON activity_log (learner_id, id);
        CREATE INDEX IF NOT EXISTS idx_assignments_learner
            ON assignments (learner_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_learner
            ON invoices (learner_id);
        CREATE INDEX IF NOT EXISTS idx_referral_uses_code
            ON referral_uses (code);
        CREATE INDEX IF NOT EXISTS idx_coupons_active
            ON coupons (active, plan);
        CREATE INDEX IF NOT EXISTS idx_payments_email
            ON payments (user_email);
        CREATE INDEX IF NOT EXISTS idx_access_codes_email
            ON access_codes (sent_to_email);
        CREATE INDEX IF NOT EXISTS idx_course_purchases_learner
            ON course_purchases (learner_id);
        """)

        # ── Schema migrations — add new columns to existing tables ──────────
        # These ALTER TABLE ... ADD COLUMN statements are no-ops if the
        # column already exists (SQLite ignores the error via try/except).
        _migrations = [
            "ALTER TABLE learner_profiles ADD COLUMN email TEXT DEFAULT ''",
            "ALTER TABLE learner_profiles ADD COLUMN display_name TEXT DEFAULT ''",
            "ALTER TABLE referrals ADD COLUMN bonus_balance REAL DEFAULT 0",
            "ALTER TABLE referral_uses ADD COLUMN referrer_bonus REAL DEFAULT 0",
            "ALTER TABLE referral_uses ADD COLUMN referee_discount REAL DEFAULT 0",
            "ALTER TABLE user_profiles ADD COLUMN photo_url TEXT DEFAULT ''",
        ]
        for sql in _migrations:
            try:
                conn.execute(sql)
            except Exception:
                pass   # column already exists — safe to ignore

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
    """Upsert a learner profile to SQLite — persists ALL fields including tier, email, name."""
    with get_db() as conn:
        conn.execute("""
        INSERT INTO learner_profiles
          (learner_id,tier,level,xp,badges,topics_seen,topic_progress,
           current_course,course_step,completed_projects,
           daily_prompts_used,last_prompt_date,email,display_name,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,unixepoch())
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
          email=CASE WHEN excluded.email != '' THEN excluded.email ELSE learner_profiles.email END,
          display_name=CASE WHEN excluded.display_name != '' THEN excluded.display_name ELSE learner_profiles.display_name END,
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
            profile_dict.get("email", ""),
            profile_dict.get("display_name", ""),
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


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def save_reset_token(token: str, email: str) -> None:
    with get_db() as conn:
        # Invalidate any existing tokens for this email first
        conn.execute("DELETE FROM password_resets WHERE email=?", (email.lower(),))
        conn.execute(
            "INSERT INTO password_resets (token,email) VALUES (?,?)",
            (token, email.lower())
        )


def load_reset_token(token: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token=? AND used=0", (token,)
        ).fetchone()
    return dict(row) if row else None


def mark_reset_token_used(token: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE password_resets SET used=1 WHERE token=?", (token,))


def update_password_hash(email: str, new_hash: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE email_accounts SET password_hash=? WHERE email=?",
            (new_hash, email.lower())
        )


# ---------------------------------------------------------------------------
# Prompt / conversation history
# ---------------------------------------------------------------------------

PROMPT_HISTORY_LIMIT = 50   # keep last 50 messages per user


def save_prompt_history(learner_id: str, role: str, content: str,
                         intent: str = "", topic: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO prompt_history (learner_id,role,content,intent,topic) VALUES (?,?,?,?,?)",
            (learner_id, role, content[:4000], intent[:50], topic[:100])
        )
        # Trim to last PROMPT_HISTORY_LIMIT rows.
        # The subquery returns NULL when there are fewer rows than the limit,
        # making the WHERE clause false — no rows deleted. This is correct.
        # The composite index (learner_id, id) makes both the subquery and
        # the DELETE fast even with thousands of rows.
        conn.execute("""
        DELETE FROM prompt_history
        WHERE learner_id = ? AND id <= (
            SELECT id FROM prompt_history
            WHERE learner_id = ?
            ORDER BY id DESC
            LIMIT 1 OFFSET ?
        )
        """, (learner_id, learner_id, PROMPT_HISTORY_LIMIT - 1))


def get_prompt_history(learner_id: str, limit: int = 20) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_history WHERE learner_id=? ORDER BY id DESC LIMIT ?",
            (learner_id, limit)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(d["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return list(reversed(result))   # chronological order


# ---------------------------------------------------------------------------
# Quiz attempts
# ---------------------------------------------------------------------------

def save_quiz_attempt(learner_id: str, topic: str, question: str,
                       answer: str, correct: bool, score: int) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts (learner_id,topic,question,answer,correct,score) VALUES (?,?,?,?,?,?)",
            (learner_id, topic, question[:500], answer[:300], int(correct), score)
        )


def get_quiz_attempts(learner_id: str, limit: int = 50) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM quiz_attempts WHERE learner_id=? ORDER BY id DESC LIMIT ?",
            (learner_id, limit)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(d["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

def create_assignment_db(assignment_id: str, learner_id: str, title: str,
                          description: str, course: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO assignments (id,learner_id,title,description,course) VALUES (?,?,?,?,?)",
            (assignment_id, learner_id, title, description, course)
        )


def submit_assignment_db(assignment_id: str, learner_id: str, submission: str) -> bool:
    import time as _t
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE assignments SET submission=?, status='submitted', submitted_at=? "
            "WHERE id=? AND learner_id=?",
            (submission[:8000], _t.time(), assignment_id, learner_id)
        )
    return cur.rowcount > 0


def review_assignment_db(assignment_id: str, feedback: str, score: int) -> bool:
    import time as _t
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE assignments SET feedback=?, score=?, status='reviewed', reviewed_at=? WHERE id=?",
            (feedback[:2000], score, _t.time(), assignment_id)
        )
    return cur.rowcount > 0


def get_assignments_db(learner_id: str) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM assignments WHERE learner_id=? ORDER BY created_at DESC",
            (learner_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for ts_field in ("submitted_at", "reviewed_at", "created_at"):
            if d.get(ts_field):
                d[ts_field] = _dt.datetime.fromtimestamp(d[ts_field]).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def get_all_assignments_db() -> list[dict]:
    """Admin: return all assignments across all learners."""
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM assignments ORDER BY created_at DESC LIMIT 500"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for ts_field in ("submitted_at", "reviewed_at", "created_at"):
            if d.get(ts_field):
                try:
                    d[ts_field] = _dt.datetime.fromtimestamp(float(d[ts_field])).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Referral codes
# ---------------------------------------------------------------------------

def create_referral_code(code: str, owner_id: str, owner_email: str,
                          max_uses: int = 50, reward_tier: str = "tier1") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO referrals (code,owner_id,owner_email,max_uses,reward_tier) VALUES (?,?,?,?,?)",
            (code.upper(), owner_id, owner_email.lower(), max_uses, reward_tier)
        )


def get_referral_code(code: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE code=?", (code.upper(),)
        ).fetchone()
    return dict(row) if row else None


def use_referral_code(code: str, used_by_email: str, used_by_id: str,
                       discount_pct: int = 10,
                       payment_amount: float = 0) -> bool:
    """
    Record a referral use.
    - Referee gets 10% discount (tracked via discount_pct).
    - Referrer gets 10% bonus of the payment credited to their bonus_balance.
    Returns False if code is exhausted or invalid.
    """
    ref = get_referral_code(code)
    if not ref or ref["uses"] >= ref["max_uses"]:
        return False
    referrer_bonus   = round(payment_amount * 0.10, 2)
    referee_discount = round(payment_amount * 0.10, 2)
    with get_db() as conn:
        conn.execute(
            "UPDATE referrals SET uses=uses+1, bonus_balance=bonus_balance+? WHERE code=?",
            (referrer_bonus, code.upper())
        )
        conn.execute(
            "INSERT INTO referral_uses "
            "(code,used_by_email,used_by_id,discount_pct,referrer_bonus,referee_discount) "
            "VALUES (?,?,?,?,?,?)",
            (code.upper(), used_by_email.lower(), used_by_id,
             discount_pct, referrer_bonus, referee_discount)
        )
    # Mirror updated stats to Supabase so they survive Render restarts
    try:
        updated = get_referral_code(code)
        if updated:
            from app.supabase_client import sb_update_referral_stats
            import threading as _t
            _t.Thread(
                target=sb_update_referral_stats,
                args=(code, updated["uses"], updated.get("bonus_balance", 0)),
                daemon=False,
            ).start()
    except Exception:
        pass
    return True


def get_referral_uses(code: str) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM referral_uses WHERE code=? ORDER BY id DESC",
            (code.upper(),)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(d["ts"]).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def get_learner_referral_code(owner_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE owner_id=?", (owner_id,)
        ).fetchone()
    return dict(row) if row else None


def get_referral_bonus_balance(owner_id: str) -> dict:
    """Return the referrer's bonus balance and use history."""
    code_rec = get_learner_referral_code(owner_id)
    if not code_rec:
        return {"balance": 0.0, "uses": 0, "code": None, "history": []}
    code  = code_rec["code"]
    uses  = get_referral_uses(code)
    total = sum(u.get("referrer_bonus", 0) for u in uses)
    return {
        "code":    code,
        "balance": round(total, 2),
        "uses":    code_rec.get("uses", 0),
        "history": uses[:20],
    }


# ---------------------------------------------------------------------------
# Coupon codes
# ---------------------------------------------------------------------------

def create_coupon_db(code: str, discount_pct: int, discount_flat: float = 0,
                      plan: str = "any", max_uses: int = 100,
                      expires_at: float = 0) -> None:
    with get_db() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO coupons
          (code,discount_pct,discount_flat,plan,max_uses,expires_at)
        VALUES (?,?,?,?,?,?)
        """, (code.upper(), discount_pct, discount_flat, plan, max_uses, expires_at))


def validate_coupon_db(code: str, plan: str = "any") -> dict | None:
    """
    Returns coupon dict if valid and applicable to plan, else None.
    Checks: active, not expired, uses < max_uses, plan matches.
    """
    import time as _t
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM coupons WHERE code=? AND active=1", (code.upper(),)
        ).fetchone()
    if not row:
        return None
    c = dict(row)
    if c["expires_at"] and c["expires_at"] > 0 and _t.time() > c["expires_at"]:
        return None
    if c["uses"] >= c["max_uses"]:
        return None
    if c["plan"] not in ("any", plan):
        return None
    return c


def use_coupon_db(code: str, learner_id: str, email: str, amount_saved: float) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE coupons SET uses=uses+1 WHERE code=?", (code.upper(),)
        )
        conn.execute(
            "INSERT INTO coupon_uses (code,learner_id,email,amount_saved) VALUES (?,?,?,?)",
            (code.upper(), learner_id, email.lower(), amount_saved)
        )


def get_all_coupons_db() -> list[dict]:
    import datetime as _dt, time as _t
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM coupons ORDER BY created_at DESC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["expired"] = bool(d["expires_at"] and d["expires_at"] > 0 and _t.time() > d["expires_at"])
        if d["expires_at"]:
            try:
                d["expires_at_fmt"] = _dt.datetime.fromtimestamp(d["expires_at"]).strftime("%Y-%m-%d")
            except Exception:
                d["expires_at_fmt"] = ""
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

def create_invoice_db(invoice_id: str, payment_id: str, learner_id: str,
                       email: str, name: str, plan: str, amount: float,
                       currency: str = "NGN") -> None:
    with get_db() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO invoices
          (id,payment_id,learner_id,email,name,plan,amount,currency)
        VALUES (?,?,?,?,?,?,?,?)
        """, (invoice_id, payment_id, learner_id, email.lower(), name, plan, amount, currency))


def get_invoice_db(invoice_id: str) -> dict | None:
    import datetime as _dt
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["issued_at_fmt"] = _dt.datetime.fromtimestamp(d["issued_at"]).strftime("%d %B %Y")
    return d


def get_invoices_by_learner(learner_id: str) -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE learner_id=? ORDER BY issued_at DESC",
            (learner_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at_fmt"] = _dt.datetime.fromtimestamp(d["issued_at"]).strftime("%d %B %Y")
        result.append(d)
    return result


def get_all_invoices_db() -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices ORDER BY issued_at DESC LIMIT 500"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at_fmt"] = _dt.datetime.fromtimestamp(d["issued_at"]).strftime("%d %B %Y")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Access codes — admin generates, user enters at signup to get tier instantly
# ---------------------------------------------------------------------------

def create_access_code(code: str, tier: str, sent_to_email: str = "",
                        expires_at: float = 0) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO access_codes "
            "(code, tier, sent_to_email, expires_at) VALUES (?,?,?,?)",
            (code.upper(), tier, sent_to_email.lower(), expires_at)
        )


def validate_access_code(code: str) -> dict | None:
    """
    Return the access code record if it's valid (unused, not expired).
    Returns None if invalid.
    """
    import time as _t
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM access_codes WHERE code=? AND used=0",
            (code.upper(),)
        ).fetchone()
    if not row:
        return None
    r = dict(row)
    if r["expires_at"] and r["expires_at"] > 0 and _t.time() > r["expires_at"]:
        return None
    return r


def redeem_access_code(code: str, email: str, learner_id: str) -> bool:
    """Mark code as used. Returns False if already used or not found."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE access_codes SET used=1, used_by_email=?, used_by_id=? "
            "WHERE code=? AND used=0",
            (email.lower(), learner_id, code.upper())
        )
    return cur.rowcount > 0


def get_all_access_codes() -> list[dict]:
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM access_codes ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = _dt.datetime.fromtimestamp(d["created_at"]).strftime("%Y-%m-%d %H:%M")
        d["expires_fmt"] = (
            _dt.datetime.fromtimestamp(d["expires_at"]).strftime("%Y-%m-%d")
            if d["expires_at"] else "Never"
        )
        result.append(d)
    return result

# ---------------------------------------------------------------------------
# User editable profile helpers
# ---------------------------------------------------------------------------

def update_user_profile_db(learner_id: str, display_name: str,
                             bio: str, location: str, website: str,
                             photo_url: str = "") -> None:
    with get_db() as conn:
        conn.execute("""
        INSERT INTO user_profiles (learner_id, display_name, bio, location, website, photo_url)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(learner_id) DO UPDATE SET
            display_name = excluded.display_name,
            bio          = excluded.bio,
            location     = excluded.location,
            website      = excluded.website,
            photo_url    = CASE WHEN excluded.photo_url != '' THEN excluded.photo_url ELSE user_profiles.photo_url END,
            updated_at   = unixepoch()
        """, (learner_id, display_name[:80], bio[:500], location[:100], website[:200], photo_url))


def get_user_profile_db(learner_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE learner_id=?", (learner_id,)
        ).fetchone()
    if row:
        return dict(row)
    return {"learner_id": learner_id, "display_name": "",
            "bio": "", "location": "", "website": ""}


# ---------------------------------------------------------------------------
# Course purchases — individual course access (separate from tier bundles)
# ---------------------------------------------------------------------------

def record_course_purchase(learner_id: str, course_name: str,
                            amount_ngn: float = 0, payment_ref: str = "") -> None:
    """Record that a learner has purchased individual access to a course."""
    with get_db() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO course_purchases
          (learner_id, course_name, amount_ngn, payment_ref)
        VALUES (?, ?, ?, ?)
        """, (learner_id, course_name, amount_ngn, payment_ref))


def has_course_purchase(learner_id: str, course_name: str) -> bool:
    """Return True if the learner has individually purchased this course."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM course_purchases WHERE learner_id=? AND course_name=?",
            (learner_id, course_name)
        ).fetchone()
    return row is not None


def get_learner_courses(learner_id: str) -> list[str]:
    """Return list of course names individually purchased by a learner."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT course_name FROM course_purchases WHERE learner_id=?",
            (learner_id,)
        ).fetchall()
    return [r["course_name"] for r in rows]


def get_all_course_purchases() -> list[dict]:
    """Admin: return all course purchases across all learners."""
    import datetime as _dt
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM course_purchases ORDER BY purchased_at DESC LIMIT 1000"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["purchased_at_fmt"] = _dt.datetime.fromtimestamp(d["purchased_at"]).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result
