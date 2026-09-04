"""
PostgreSQL persistence layer for MyPy Tutor.
Drop-in replacement for the previous SQLite layer — all function signatures
are identical so nothing else in the codebase needs to change.

Connection string is read from DATABASE_URL env var (Render PostgreSQL add-on).
Set DATABASE_URL in Render → mypy-tutor → Environment:
  postgresql://mypytutor_user:PASSWORD@dpg-d9t11o6417fc73bj9aig-a/mypytutor
"""

import os
import json
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# Connection pool — reuse connections instead of open/close per query.
# ThreadedConnectionPool is safe for multi-threaded WSGI/ASGI workers.
#
# minconn=2  — keep 2 connections warm at all times (covers idle periods)
# maxconn=10 — Render free PostgreSQL allows up to 25 concurrent connections;
#              we cap at 10 so other services sharing the DB have headroom.
# ---------------------------------------------------------------------------
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """Lazy-initialise the connection pool on first use."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:          # double-checked locking
            return _pool
        if not DATABASE_URL:
            return None
        try:
            import psycopg2.pool
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=DATABASE_URL,
                connect_timeout=10,   # fail fast if DB is unreachable (vs hanging 30s+)
            )
            logger.info("PostgreSQL connection pool initialised (min=2 max=10)")
        except Exception as exc:
            logger.error("Failed to create connection pool: %s", exc)
            _pool = None
        return _pool


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

@contextmanager
def get_db():
    """Yield a PostgreSQL connection from the pool (auto-commit/rollback).

    Falls back to a plain single connection if the pool is unavailable
    (e.g. during init_db() before the pool exists, or in unit tests).
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Go to Render → mypy-tutor → Environment and add DATABASE_URL "
            "with the Internal Database URL from the mypy-tutor-db PostgreSQL service."
        )
    import psycopg2
    import psycopg2.extras

    pool = _get_pool()
    conn = None
    from_pool = False

    if pool:
        try:
            # getconn() can block indefinitely if all connections are in use.
            # Wrap with a 5s timeout using a background thread so the request
            # fails fast instead of hanging the Render worker.
            import threading as _pt
            _conn_holder: list = [None]
            _conn_exc:    list = [None]

            def _fetch():
                try:
                    _conn_holder[0] = pool.getconn()
                except Exception as e:
                    _conn_exc[0] = e

            _t = _pt.Thread(target=_fetch, daemon=True)
            _t.start()
            _t.join(timeout=5)   # wait at most 5s for a pool slot

            if _conn_holder[0] is not None:
                conn      = _conn_holder[0]
                from_pool = True
            elif _conn_exc[0] is not None:
                logger.warning("Pool.getconn() error (%s) — falling back to direct connect", _conn_exc[0])
            else:
                logger.warning("Pool.getconn() timed out after 5s — falling back to direct connect")
        except Exception as exc:
            logger.warning("Pool.getconn() failed (%s) — falling back to direct connect", exc)

    if conn is None:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)

    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if from_pool and pool:
            # Return to pool: reset the connection state first
            try:
                conn.reset()
                pool.putconn(conn)
            except Exception:
                # If reset fails the connection is broken — discard it
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
        else:
            conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables and indexes. Safe to call multiple times (IF NOT EXISTS).
    Logs a warning and skips gracefully if DATABASE_URL is not configured yet."""
    if not DATABASE_URL:
        logger.warning(
            "DATABASE_URL not set — skipping database initialisation. "
            "Set DATABASE_URL in Render → mypy-tutor → Environment to enable PostgreSQL."
        )
        return
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # ── Tables ───────────────────────────────────────────────────────
            cur.execute("""
            CREATE TABLE IF NOT EXISTS learner_profiles (
                learner_id          TEXT PRIMARY KEY,
                tier                TEXT DEFAULT 'free',
                level               TEXT DEFAULT 'beginner',
                xp                  INTEGER DEFAULT 0,
                badges              TEXT DEFAULT '[]',
                topics_seen         TEXT DEFAULT '[]',
                topic_progress      TEXT DEFAULT '{}',
                current_course      TEXT,
                course_step         INTEGER DEFAULT 0,
                completed_projects  TEXT DEFAULT '[]',
                daily_prompts_used  INTEGER DEFAULT 0,
                last_prompt_date    TEXT DEFAULT '',
                email               TEXT DEFAULT '',
                display_name        TEXT DEFAULT '',
                prompt_plan         TEXT DEFAULT '',
                updated_at          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS email_accounts (
                email           TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                learner_id      TEXT NOT NULL,
                password_hash   TEXT NOT NULL,
                token           TEXT,
                confirmed       INTEGER DEFAULT 0,
                created_at      DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id          SERIAL PRIMARY KEY,
                learner_id  TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT DEFAULT '',
                ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                cert_id         TEXT PRIMARY KEY,
                learner_id      TEXT NOT NULL,
                learner_name    TEXT NOT NULL,
                level           TEXT NOT NULL,
                issued_at       DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id          TEXT PRIMARY KEY,
                user_email  TEXT NOT NULL,
                user_name   TEXT NOT NULL,
                amount      DOUBLE PRECISION NOT NULL,
                currency    TEXT DEFAULT 'NGN',
                plan        TEXT NOT NULL,
                method      TEXT DEFAULT 'bank',
                status      TEXT DEFAULT 'pending',
                notes       TEXT DEFAULT '',
                created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                email       TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                role        TEXT DEFAULT 'team',
                status      TEXT DEFAULT 'invited',
                invited_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                assigned_to TEXT NOT NULL,
                priority    TEXT DEFAULT 'medium',
                status      TEXT DEFAULT 'open',
                due_date    TEXT DEFAULT '',
                created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id       SERIAL PRIMARY KEY,
                subject  TEXT NOT NULL,
                target   TEXT NOT NULL,
                sent_to  INTEGER DEFAULT 0,
                sent_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                token       TEXT PRIMARY KEY,
                email       TEXT NOT NULL,
                created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
                used        INTEGER DEFAULT 0
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS prompt_history (
                id          SERIAL PRIMARY KEY,
                learner_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                intent      TEXT DEFAULT '',
                topic       TEXT DEFAULT '',
                ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id          SERIAL PRIMARY KEY,
                learner_id  TEXT NOT NULL,
                topic       TEXT NOT NULL,
                question    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                correct     INTEGER DEFAULT 0,
                score       INTEGER DEFAULT 0,
                ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id           TEXT PRIMARY KEY,
                learner_id   TEXT NOT NULL,
                title        TEXT NOT NULL,
                description  TEXT NOT NULL,
                course       TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                submission   TEXT DEFAULT '',
                feedback     TEXT DEFAULT '',
                score        INTEGER DEFAULT 0,
                submitted_at DOUBLE PRECISION,
                reviewed_at  DOUBLE PRECISION,
                created_at   DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                code            TEXT PRIMARY KEY,
                owner_id        TEXT NOT NULL,
                owner_email     TEXT NOT NULL,
                uses            INTEGER DEFAULT 0,
                max_uses        INTEGER DEFAULT 50,
                reward_tier     TEXT DEFAULT 'tier1',
                bonus_balance   DOUBLE PRECISION DEFAULT 0,
                created_at      DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_uses (
                id               SERIAL PRIMARY KEY,
                code             TEXT NOT NULL,
                used_by_email    TEXT NOT NULL,
                used_by_id       TEXT NOT NULL,
                discount_pct     INTEGER DEFAULT 20,
                referrer_bonus   DOUBLE PRECISION DEFAULT 0,
                referee_discount DOUBLE PRECISION DEFAULT 0,
                ts               DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                code            TEXT PRIMARY KEY,
                discount_pct    INTEGER NOT NULL,
                discount_flat   DOUBLE PRECISION DEFAULT 0,
                plan            TEXT DEFAULT 'any',
                max_uses        INTEGER DEFAULT 100,
                uses            INTEGER DEFAULT 0,
                expires_at      DOUBLE PRECISION DEFAULT 0,
                active          INTEGER DEFAULT 1,
                created_at      DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS coupon_uses (
                id           SERIAL PRIMARY KEY,
                code         TEXT NOT NULL,
                learner_id   TEXT NOT NULL,
                email        TEXT NOT NULL,
                amount_saved DOUBLE PRECISION DEFAULT 0,
                ts           DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id          TEXT PRIMARY KEY,
                payment_id  TEXT NOT NULL,
                learner_id  TEXT NOT NULL,
                email       TEXT NOT NULL,
                name        TEXT NOT NULL,
                plan        TEXT NOT NULL,
                amount      DOUBLE PRECISION NOT NULL,
                currency    TEXT DEFAULT 'NGN',
                issued_at   DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
                due_date    TEXT DEFAULT ''
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS access_codes (
                code          TEXT PRIMARY KEY,
                tier          TEXT NOT NULL,
                created_by    TEXT DEFAULT 'admin',
                sent_to_email TEXT DEFAULT '',
                used_by_email TEXT DEFAULT '',
                used_by_id    TEXT DEFAULT '',
                used          INTEGER DEFAULT 0,
                expires_at    DOUBLE PRECISION DEFAULT 0,
                discount_pct  INTEGER DEFAULT 0,
                created_at    DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                learner_id   TEXT PRIMARY KEY,
                display_name TEXT DEFAULT '',
                bio          TEXT DEFAULT '',
                location     TEXT DEFAULT '',
                website      TEXT DEFAULT '',
                photo_url    TEXT DEFAULT '',
                updated_at   DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS course_purchases (
                id           SERIAL PRIMARY KEY,
                learner_id   TEXT NOT NULL,
                course_name  TEXT NOT NULL,
                amount_ngn   DOUBLE PRECISION DEFAULT 0,
                payment_ref  TEXT DEFAULT '',
                purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
                UNIQUE (learner_id, course_name)
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_prompt_counts (
                key      TEXT NOT NULL,
                date_str TEXT NOT NULL,
                count    INTEGER DEFAULT 0,
                PRIMARY KEY (key, date_str)
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_ratings (
                id         SERIAL PRIMARY KEY,
                learner_id TEXT NOT NULL,
                rating     TEXT NOT NULL,
                intent     TEXT DEFAULT '',
                topic      TEXT DEFAULT '',
                comment    TEXT DEFAULT '',
                ts         DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_surveys (
                id              SERIAL PRIMARY KEY,
                learner_id      TEXT NOT NULL,
                overall         INTEGER NOT NULL,
                clarity         INTEGER NOT NULL,
                helpfulness     INTEGER NOT NULL,
                suggestion      TEXT DEFAULT '',
                would_recommend INTEGER DEFAULT 1,
                ts              DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_withdrawals (
                id           SERIAL PRIMARY KEY,
                learner_id   TEXT NOT NULL,
                email        TEXT NOT NULL,
                amount       DOUBLE PRECISION NOT NULL,
                bank_name    TEXT NOT NULL,
                account_name TEXT NOT NULL,
                account_num  TEXT NOT NULL,
                status       TEXT DEFAULT 'pending',
                notes        TEXT DEFAULT '',
                created_at   DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS session_revocations (
                learner_id TEXT PRIMARY KEY,
                revoked_at DOUBLE PRECISION NOT NULL
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_transfer_proofs (
                id            TEXT PRIMARY KEY,
                learner_id    TEXT NOT NULL,
                email         TEXT NOT NULL,
                plan          TEXT NOT NULL,
                amount        DOUBLE PRECISION NOT NULL,
                reference     TEXT DEFAULT '',
                proof_b64     TEXT DEFAULT '',
                proof_url     TEXT DEFAULT '',
                notes         TEXT DEFAULT '',
                status        TEXT DEFAULT 'pending',
                admin_notes   TEXT DEFAULT '',
                submitted_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
                reviewed_at   DOUBLE PRECISION
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_webhooks (
                reference    TEXT PRIMARY KEY,
                processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS enquiries (
                id          SERIAL PRIMARY KEY,
                learner_id  TEXT DEFAULT '',
                name        TEXT NOT NULL,
                email       TEXT NOT NULL,
                category    TEXT NOT NULL,
                subject     TEXT NOT NULL,
                message     TEXT NOT NULL,
                status      TEXT DEFAULT 'open',
                created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS email_automation (
                learner_id               TEXT PRIMARY KEY,
                email                    TEXT NOT NULL DEFAULT '',
                name                     TEXT NOT NULL DEFAULT '',
                last_reengagement_at     DOUBLE PRECISION DEFAULT 0,
                last_course_reminder_at  DOUBLE PRECISION DEFAULT 0,
                last_assignment_reminder_at DOUBLE PRECISION DEFAULT 0,
                last_weekend_msg_at      DOUBLE PRECISION DEFAULT 0,
                last_new_month_msg_at    DOUBLE PRECISION DEFAULT 0,
                opted_out                INTEGER DEFAULT 0,
                updated_at               DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
            )""")

            # ── Indexes ──────────────────────────────────────────────────────
            for sql in [
                "CREATE INDEX IF NOT EXISTS idx_prompt_history_learner ON prompt_history (learner_id, id)",
                "CREATE INDEX IF NOT EXISTS idx_quiz_attempts_learner ON quiz_attempts (learner_id)",
                "CREATE INDEX IF NOT EXISTS idx_activity_log_learner ON activity_log (learner_id, id)",
                "CREATE INDEX IF NOT EXISTS idx_assignments_learner ON assignments (learner_id)",
                "CREATE INDEX IF NOT EXISTS idx_invoices_learner ON invoices (learner_id)",
                "CREATE INDEX IF NOT EXISTS idx_referral_uses_code ON referral_uses (code)",
                "CREATE INDEX IF NOT EXISTS idx_coupons_active ON coupons (active, plan)",
                "CREATE INDEX IF NOT EXISTS idx_payments_email ON payments (user_email)",
                "CREATE INDEX IF NOT EXISTS idx_access_codes_email ON access_codes (sent_to_email)",
                "CREATE INDEX IF NOT EXISTS idx_course_purchases_learner ON course_purchases (learner_id)",
                "CREATE INDEX IF NOT EXISTS idx_daily_prompts_key ON daily_prompt_counts (key, date_str)",
                "CREATE INDEX IF NOT EXISTS idx_feedback_ratings_learner ON feedback_ratings (learner_id, ts)",
                "CREATE INDEX IF NOT EXISTS idx_feedback_surveys_learner ON feedback_surveys (learner_id, ts)",
            "CREATE INDEX IF NOT EXISTS idx_btp_learner ON bank_transfer_proofs (learner_id)",
            "CREATE INDEX IF NOT EXISTS idx_btp_status ON bank_transfer_proofs (status)",
            "CREATE INDEX IF NOT EXISTS idx_email_automation_opted ON email_automation (opted_out)",
            ]:
                cur.execute(sql)

            logger.info("PostgreSQL database initialised")

            # ── Safe column migrations for existing databases ─────────────
            # These are no-ops if the column already exists.
            _col_migrations = [
                "ALTER TABLE access_codes ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0",
            ]
            for _sql in _col_migrations:
                try:
                    cur.execute(_sql)
                except Exception:
                    pass  # column already exists or unsupported syntax

    except Exception as _init_exc:
        logger.error(
            "Database initialisation failed: %s — "
            "make sure DATABASE_URL is set correctly in Render environment variables.",
            _init_exc
        )
        raise


# ---------------------------------------------------------------------------
# Learner profile helpers
# ---------------------------------------------------------------------------

def load_profile(learner_id: str):
    """Load a learner profile from PostgreSQL. Returns None if not found."""
    with get_db() as conn:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM learner_profiles WHERE learner_id=%s", (learner_id,)
            )
            row = cur.fetchone()
    return dict(row) if row else None


def save_profile_db(learner_id: str, profile_dict: dict) -> None:
    """Upsert a learner profile — persists ALL fields including tier, email, name."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO learner_profiles
              (learner_id,tier,level,xp,badges,topics_seen,topic_progress,
               current_course,course_step,completed_projects,
               daily_prompts_used,last_prompt_date,email,display_name,updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,EXTRACT(EPOCH FROM NOW()))
            ON CONFLICT(learner_id) DO UPDATE SET
              tier=EXCLUDED.tier,
              level=EXCLUDED.level,
              xp=EXCLUDED.xp,
              badges=EXCLUDED.badges,
              topics_seen=EXCLUDED.topics_seen,
              topic_progress=EXCLUDED.topic_progress,
              current_course=EXCLUDED.current_course,
              course_step=EXCLUDED.course_step,
              completed_projects=EXCLUDED.completed_projects,
              daily_prompts_used=EXCLUDED.daily_prompts_used,
              last_prompt_date=EXCLUDED.last_prompt_date,
              email=CASE WHEN EXCLUDED.email <> '' THEN EXCLUDED.email
                         ELSE learner_profiles.email END,
              display_name=CASE WHEN EXCLUDED.display_name <> '' THEN EXCLUDED.display_name
                                ELSE learner_profiles.display_name END,
              updated_at=EXTRACT(EPOCH FROM NOW())
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
    """Upgrade a learner's tier in PostgreSQL and mirror to Supabase.

    Uses a single UPSERT so new users (no profile row yet) are handled
    correctly — the previous UPDATE + INSERT ON CONFLICT DO NOTHING silently
    left the tier at 'free' for brand-new learners.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO learner_profiles (learner_id, tier, updated_at)
                VALUES (%s, %s, EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (learner_id) DO UPDATE SET
                    tier       = EXCLUDED.tier,
                    updated_at = EXTRACT(EPOCH FROM NOW())
            """, (learner_id, tier))
    try:
        from app.supabase_client import sb_update_tier
        sb_update_tier(learner_id, tier)
    except Exception:
        pass


def get_all_learners() -> list[dict]:
    """Return all learner profiles from PostgreSQL for admin use."""
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM learner_profiles ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO email_accounts (email,name,learner_id,password_hash,token,confirmed)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT(email) DO UPDATE SET
              name=EXCLUDED.name, password_hash=EXCLUDED.password_hash,
              token=EXCLUDED.token, confirmed=EXCLUDED.confirmed
            """, (email.lower(), name, learner_id, password_hash, token, int(confirmed)))


def load_email_account(email: str) -> dict | None:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM email_accounts WHERE email=%s", (email.lower(),)
            )
            row = cur.fetchone()
    return dict(row) if row else None


def confirm_email_db(email: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE email_accounts SET confirmed=1 WHERE email=%s", (email.lower(),)
            )


def get_all_confirmed_emails() -> list[dict]:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM email_accounts WHERE confirmed=1")
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

def log_activity_db(learner_id: str, action: str, detail: str = "") -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO activity_log (learner_id,action,detail) VALUES (%s,%s,%s)",
                (learner_id, action, detail[:200])
            )
            # Keep only last 2000 entries
            cur.execute("""
                DELETE FROM activity_log WHERE id NOT IN (
                    SELECT id FROM activity_log ORDER BY id DESC LIMIT 2000
                )
            """)


def get_activity_log(limit: int = 200) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT %s", (limit,)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(float(d["ts"])).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

def save_certificate_db(cert_id: str, learner_id: str, learner_name: str, level: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO certificates (cert_id,learner_id,learner_name,level) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT(cert_id) DO NOTHING",
                (cert_id, learner_id, learner_name, level)
            )


def get_certificates_db() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM certificates ORDER BY issued_at DESC")
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at"] = _dt.datetime.fromtimestamp(float(d["issued_at"])).isoformat()
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def save_reset_token(token: str, email: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM password_resets WHERE email=%s", (email.lower(),))
            cur.execute(
                "INSERT INTO password_resets (token,email) VALUES (%s,%s)",
                (token, email.lower())
            )


def load_reset_token(token: str) -> dict | None:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM password_resets WHERE token=%s AND used=0", (token,)
            )
            row = cur.fetchone()
    return dict(row) if row else None


def mark_reset_token_used(token: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE password_resets SET used=1 WHERE token=%s", (token,))


def purge_expired_reset_tokens() -> None:
    import time as _t
    cutoff = _t.time() - (2 * 3600)
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM password_resets WHERE used=1 OR created_at < %s",
                    (cutoff,)
                )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session revocation
# ---------------------------------------------------------------------------

def revoke_all_sessions(learner_id: str) -> None:
    import time as _t
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO session_revocations (learner_id, revoked_at)
                    VALUES (%s, %s)
                    ON CONFLICT(learner_id) DO UPDATE SET revoked_at=EXCLUDED.revoked_at
                """, (learner_id, _t.time()))
    except Exception as _e:
        logger.warning("revoke_all_sessions failed: %s", _e)


def is_session_revoked(learner_id: str, token_issued_at: float) -> bool:
    try:
        import psycopg2.extras
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT revoked_at FROM session_revocations WHERE learner_id=%s",
                    (learner_id,)
                )
                row = cur.fetchone()
        if row and token_issued_at < float(row["revoked_at"]):
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------

def delete_account(learner_id: str, email: str) -> dict:
    import time as _t
    email = (email or "").lower().strip()
    summary = {}
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM email_accounts WHERE learner_id=%s", (learner_id,))
                cur.execute("DELETE FROM user_profiles WHERE learner_id=%s", (learner_id,))
                # Only clean up email-dependent tables when we have a valid email
                if email:
                    cur.execute("DELETE FROM password_resets WHERE email=%s", (email,))
                cur.execute("DELETE FROM referral_withdrawals WHERE learner_id=%s", (learner_id,))
                cur.execute("""
                    INSERT INTO session_revocations (learner_id, revoked_at) VALUES (%s, %s)
                    ON CONFLICT(learner_id) DO UPDATE SET revoked_at=EXCLUDED.revoked_at
                """, (learner_id, _t.time()))
                cur.execute("""
                    UPDATE learner_profiles SET email='', display_name='[deleted]'
                    WHERE learner_id=%s
                """, (learner_id,))
                # Mark as deleted so it is excluded from admin user listings
                # We keep the row (not DELETE) to preserve XP/progress for audit,
                # but the display_name sentinel filters it out of the UI.
                cur.execute("""
                    UPDATE learner_profiles SET tier='deleted'
                    WHERE learner_id=%s
                """, (learner_id,))
                cur.execute("""
                    UPDATE prompt_history SET content='[deleted]' WHERE learner_id=%s
                """, (learner_id,))
                if email:
                    cur.execute("""
                        UPDATE payments SET user_email='deleted@deleted.invalid',
                                            user_name='[deleted]'
                        WHERE user_email=%s
                    """, (email,))
        summary = {
            "email_account": "deleted",
            "user_profile": "deleted",
            "sessions": "revoked",
            "learning_profile": "anonymised",
            "prompt_history": "anonymised",
            "payments": "email anonymised (retained 7 years per law)" if email else "skipped (no email on record)",
        }
    except Exception as _e:
        logger.error("delete_account DB error for %s: %s", learner_id, _e)
        raise
    return summary


def update_password_hash(email: str, new_hash: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE email_accounts SET password_hash=%s WHERE email=%s",
                (new_hash, email.lower())
            )


# ---------------------------------------------------------------------------
# Prompt / conversation history
# ---------------------------------------------------------------------------

PROMPT_HISTORY_LIMIT = 50


def save_prompt_history(learner_id: str, role: str, content: str,
                         intent: str = "", topic: str = "") -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prompt_history (learner_id,role,content,intent,topic) "
                "VALUES (%s,%s,%s,%s,%s)",
                (learner_id, role, content[:16000], intent[:50], topic[:100])
            )
            # Trim to last PROMPT_HISTORY_LIMIT rows for this learner
            cur.execute("""
                DELETE FROM prompt_history WHERE learner_id=%s AND id NOT IN (
                    SELECT id FROM prompt_history WHERE learner_id=%s
                    ORDER BY id DESC LIMIT %s
                )
            """, (learner_id, learner_id, PROMPT_HISTORY_LIMIT))


def get_prompt_history(learner_id: str, limit: int = 20) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM prompt_history WHERE learner_id=%s ORDER BY id DESC LIMIT %s",
                (learner_id, limit)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(float(d["ts"])).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return list(reversed(result))


# ---------------------------------------------------------------------------
# Quiz attempts
# ---------------------------------------------------------------------------

def save_quiz_attempt(learner_id: str, topic: str, question: str,
                       answer: str, correct: bool, score: int) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO quiz_attempts (learner_id,topic,question,answer,correct,score) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (learner_id, topic, question[:500], answer[:300], int(correct), score)
            )


def get_quiz_attempts(learner_id: str, limit: int = 50) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM quiz_attempts WHERE learner_id=%s ORDER BY id DESC LIMIT %s",
                (learner_id, limit)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(float(d["ts"])).strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

def create_assignment_db(assignment_id: str, learner_id: str, title: str,
                          description: str, course: str = "") -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO assignments (id,learner_id,title,description,course) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                (assignment_id, learner_id, title, description, course)
            )


def submit_assignment_db(assignment_id: str, learner_id: str, submission: str) -> bool:
    import time as _t
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assignments SET submission=%s, status='submitted', submitted_at=%s "
                "WHERE id=%s AND learner_id=%s",
                (submission[:8000], _t.time(), assignment_id, learner_id)
            )
            return cur.rowcount > 0


def review_assignment_db(assignment_id: str, feedback: str, score: int) -> bool:
    import time as _t
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assignments SET feedback=%s, score=%s, status='reviewed', reviewed_at=%s "
                "WHERE id=%s",
                (feedback[:2000], score, _t.time(), assignment_id)
            )
            return cur.rowcount > 0


def get_assignments_db(learner_id: str) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM assignments WHERE learner_id=%s ORDER BY created_at DESC",
                (learner_id,)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for ts_field in ("submitted_at", "reviewed_at", "created_at"):
            if d.get(ts_field):
                d[ts_field] = _dt.datetime.fromtimestamp(float(d[ts_field])).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def get_all_assignments_db() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM assignments ORDER BY created_at DESC LIMIT 500"
            )
            rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO referrals (code,owner_id,owner_email,max_uses,reward_tier) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT(code) DO NOTHING",
                (code.upper(), owner_id, owner_email.lower(), max_uses, reward_tier)
            )


def get_referral_code(code: str) -> dict | None:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM referrals WHERE code=%s", (code.upper(),))
            row = cur.fetchone()
    return dict(row) if row else None


def use_referral_code(code: str, used_by_email: str, used_by_id: str,
                       discount_pct: int = 5, payment_amount: float = 0) -> bool:
    ref = get_referral_code(code)
    if not ref or ref["uses"] >= ref["max_uses"]:
        return False
    referrer_bonus   = round(payment_amount * 0.15, 2)
    referee_discount = round(payment_amount * 0.05, 2)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE referrals SET uses=uses+1, bonus_balance=bonus_balance+%s WHERE code=%s",
                (referrer_bonus, code.upper())
            )
            cur.execute(
                "INSERT INTO referral_uses "
                "(code,used_by_email,used_by_id,discount_pct,referrer_bonus,referee_discount) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (code.upper(), used_by_email.lower(), used_by_id,
                 discount_pct, referrer_bonus, referee_discount)
            )
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
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM referral_uses WHERE code=%s ORDER BY id DESC",
                (code.upper(),)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ts"] = _dt.datetime.fromtimestamp(float(d["ts"])).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def get_learner_referral_code(owner_id: str) -> dict | None:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM referrals WHERE owner_id=%s", (owner_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_referral_bonus_balance(owner_id: str) -> dict:
    code_rec = get_learner_referral_code(owner_id)
    if not code_rec:
        return {"balance": 0.0, "uses": 0, "code": None, "history": []}
    code  = code_rec["code"]
    uses  = get_referral_uses(code)
    stored_balance  = float(code_rec.get("bonus_balance") or 0)
    computed_total  = sum(float(u.get("referrer_bonus", 0)) for u in uses)
    balance = max(stored_balance, computed_total)
    return {
        "code":    code,
        "balance": round(balance, 2),
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
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO coupons (code,discount_pct,discount_flat,plan,max_uses,expires_at)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT(code) DO UPDATE SET
              discount_pct=EXCLUDED.discount_pct,
              discount_flat=EXCLUDED.discount_flat,
              plan=EXCLUDED.plan,
              max_uses=EXCLUDED.max_uses,
              expires_at=EXCLUDED.expires_at
            """, (code.upper(), discount_pct, discount_flat, plan, max_uses, expires_at))


def validate_coupon_db(code: str, plan: str = "any") -> dict | None:
    import time as _t
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM coupons WHERE code=%s AND active=1", (code.upper(),)
            )
            row = cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE coupons SET uses=uses+1 WHERE code=%s", (code.upper(),)
            )
            cur.execute(
                "INSERT INTO coupon_uses (code,learner_id,email,amount_saved) VALUES (%s,%s,%s,%s)",
                (code.upper(), learner_id, email.lower(), amount_saved)
            )


def get_all_coupons_db() -> list[dict]:
    import datetime as _dt, time as _t
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM coupons ORDER BY created_at DESC")
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["expired"] = bool(d["expires_at"] and d["expires_at"] > 0 and _t.time() > d["expires_at"])
        if d["expires_at"]:
            try:
                d["expires_at_fmt"] = _dt.datetime.fromtimestamp(float(d["expires_at"])).strftime("%Y-%m-%d")
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
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO invoices (id,payment_id,learner_id,email,name,plan,amount,currency)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(id) DO NOTHING
            """, (invoice_id, payment_id, learner_id, email.lower(), name, plan, amount, currency))


def get_invoice_db(invoice_id: str) -> dict | None:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["issued_at_fmt"] = _dt.datetime.fromtimestamp(float(d["issued_at"])).strftime("%d %B %Y")
    return d


def get_invoices_by_learner(learner_id: str) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM invoices WHERE learner_id=%s ORDER BY issued_at DESC",
                (learner_id,)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at_fmt"] = _dt.datetime.fromtimestamp(float(d["issued_at"])).strftime("%d %B %Y")
        result.append(d)
    return result


def get_all_invoices_db() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM invoices ORDER BY issued_at DESC LIMIT 500")
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["issued_at_fmt"] = _dt.datetime.fromtimestamp(float(d["issued_at"])).strftime("%d %B %Y")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Access codes
# ---------------------------------------------------------------------------

def create_access_code(code: str, tier: str, sent_to_email: str = "",
                        expires_at: float = 0, discount_pct: int = 0) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO access_codes (code,tier,sent_to_email,expires_at,discount_pct) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT(code) DO NOTHING",
                (code.upper(), tier, sent_to_email.lower(), expires_at, discount_pct)
            )


def validate_access_code(code: str) -> dict | None:
    import time as _t
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM access_codes WHERE code=%s AND used=0", (code.upper(),)
            )
            row = cur.fetchone()
    if not row:
        return None
    r = dict(row)
    if r["expires_at"] and r["expires_at"] > 0 and _t.time() > r["expires_at"]:
        return None
    return r


def redeem_access_code(code: str, email: str, learner_id: str) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE access_codes SET used=1, used_by_email=%s, used_by_id=%s "
                "WHERE code=%s AND used=0",
                (email.lower(), learner_id, code.upper())
            )
            return cur.rowcount > 0


def get_all_access_codes() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM access_codes ORDER BY created_at DESC")
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = _dt.datetime.fromtimestamp(float(d["created_at"])).strftime("%Y-%m-%d %H:%M")
        d["expires_fmt"] = (
            _dt.datetime.fromtimestamp(float(d["expires_at"])).strftime("%Y-%m-%d")
            if d.get("expires_at") else "Never"
        )
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# User editable profile
# ---------------------------------------------------------------------------

def update_user_profile_db(learner_id: str, display_name: str,
                             bio: str, location: str, website: str,
                             photo_url: str = "") -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO user_profiles (learner_id, display_name, bio, location, website, photo_url)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT(learner_id) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                bio          = EXCLUDED.bio,
                location     = EXCLUDED.location,
                website      = EXCLUDED.website,
                photo_url    = CASE WHEN EXCLUDED.photo_url <> '' THEN EXCLUDED.photo_url
                                    ELSE user_profiles.photo_url END,
                updated_at   = EXTRACT(EPOCH FROM NOW())
            """, (learner_id, display_name[:80], bio[:500], location[:100], website[:200], photo_url))


def get_user_profile_db(learner_id: str) -> dict:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM user_profiles WHERE learner_id=%s", (learner_id,)
            )
            row = cur.fetchone()
    if row:
        return dict(row)
    return {"learner_id": learner_id, "display_name": "",
            "bio": "", "location": "", "website": "", "photo_url": ""}


# ---------------------------------------------------------------------------
# Course purchases
# ---------------------------------------------------------------------------

def record_course_purchase(learner_id: str, course_name: str,
                            amount_ngn: float = 0, payment_ref: str = "") -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO course_purchases (learner_id, course_name, amount_ngn, payment_ref)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT(learner_id, course_name) DO NOTHING
            """, (learner_id, course_name, amount_ngn, payment_ref))


def has_course_purchase(learner_id: str, course_name: str) -> bool:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id FROM course_purchases WHERE learner_id=%s AND course_name=%s",
                (learner_id, course_name)
            )
            row = cur.fetchone()
    return row is not None


def get_course_purchases_for_learner(learner_id: str) -> set[str]:
    """Return the set of all course names this learner has individually purchased.

    Use this instead of calling has_course_purchase() in a loop — one query
    instead of N queries.
    """
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT course_name FROM course_purchases WHERE learner_id=%s",
                (learner_id,)
            )
            rows = cur.fetchall()
    return {r["course_name"] for r in rows}


def get_learner_courses(learner_id: str) -> list[str]:
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT course_name FROM course_purchases WHERE learner_id=%s",
                (learner_id,)
            )
            rows = cur.fetchall()
    return [r["course_name"] for r in rows]


def get_all_course_purchases() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM course_purchases ORDER BY purchased_at DESC LIMIT 1000"
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["purchased_at_fmt"] = _dt.datetime.fromtimestamp(float(d["purchased_at"])).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Daily prompt counts
# ---------------------------------------------------------------------------

def get_daily_prompt_count_db(key: str, date_str: str) -> int:
    try:
        import psycopg2.extras
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT count FROM daily_prompt_counts WHERE key=%s AND date_str=%s",
                    (key, date_str)
                )
                row = cur.fetchone()
        return int(row["count"]) if row else 0
    except Exception:
        return 0


def increment_daily_prompt_count_db(key: str, date_str: str) -> int:
    try:
        import psycopg2.extras
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO daily_prompt_counts (key, date_str, count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT(key, date_str) DO UPDATE SET count = daily_prompt_counts.count + 1
                """, (key, date_str))
                cur.execute(
                    "SELECT count FROM daily_prompt_counts WHERE key=%s AND date_str=%s",
                    (key, date_str)
                )
                row = cur.fetchone()
        return int(row["count"]) if row else 1
    except Exception:
        return 1


def load_todays_prompt_counts(date_str: str) -> dict:
    try:
        import psycopg2.extras
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT key, count FROM daily_prompt_counts WHERE date_str=%s",
                    (date_str,)
                )
                rows = cur.fetchall()
        return {r["key"]: r["count"] for r in rows}
    except Exception:
        return {}


def purge_old_prompt_counts(keep_date: str) -> None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM daily_prompt_counts WHERE date_str < %s", (keep_date,)
                )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Referral withdrawal requests
# ---------------------------------------------------------------------------

def create_withdrawal_request(learner_id: str, email: str, amount: float,
                               bank_name: str, account_name: str,
                               account_num: str) -> int:
    """Insert a withdrawal record and atomically deduct the amount from bonus_balance.

    Uses SELECT … FOR UPDATE on the referrals row so concurrent requests
    cannot both read a positive balance and both succeed — the second will
    see the already-decremented balance and be rejected upstream.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            # Lock the referral row for this learner for the duration of the tx
            cur.execute(
                "SELECT bonus_balance FROM referrals WHERE owner_id=%s FOR UPDATE",
                (learner_id,)
            )
            row = cur.fetchone()
            current_balance = float(row[0]) if row else 0.0

            if current_balance < amount:
                raise ValueError(
                    f"Insufficient balance: ₦{current_balance:.2f} available, "
                    f"₦{amount:.2f} requested"
                )

            # Deduct balance atomically in the same transaction
            cur.execute(
                "UPDATE referrals SET bonus_balance = bonus_balance - %s "
                "WHERE owner_id=%s",
                (amount, learner_id)
            )

            cur.execute("""
                INSERT INTO referral_withdrawals
                  (learner_id, email, amount, bank_name, account_name, account_num)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
            """, (learner_id, email.lower(), amount, bank_name, account_name, account_num))
            id_row = cur.fetchone()
    return id_row[0] if id_row else 0


def get_withdrawals_for_learner(learner_id: str) -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM referral_withdrawals WHERE learner_id=%s ORDER BY id DESC",
                (learner_id,)
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = _dt.datetime.fromtimestamp(float(d["created_at"])).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def get_all_withdrawal_requests() -> list[dict]:
    import datetime as _dt
    import psycopg2.extras
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM referral_withdrawals ORDER BY id DESC LIMIT 500"
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = _dt.datetime.fromtimestamp(float(d["created_at"])).strftime("%Y-%m-%d %H:%M")
        result.append(d)
    return result


def update_withdrawal_status(withdrawal_id: int, status: str, notes: str = "") -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE referral_withdrawals SET status=%s, notes=%s WHERE id=%s",
                (status, notes, withdrawal_id)
            )
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Email automation helpers
# ---------------------------------------------------------------------------

def upsert_email_automation(learner_id: str, email: str, name: str) -> None:
    """Ensure a row exists for this learner; never overwrites opted_out."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_automation (learner_id, email, name, updated_at)
                VALUES (%s, %s, %s, EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (learner_id) DO UPDATE SET
                    email      = CASE WHEN EXCLUDED.email <> '' THEN EXCLUDED.email
                                      ELSE email_automation.email END,
                    name       = CASE WHEN EXCLUDED.name  <> '' THEN EXCLUDED.name
                                      ELSE email_automation.name  END,
                    updated_at = EXTRACT(EPOCH FROM NOW())
            """, (learner_id, email.lower(), name))


def mark_email_sent(learner_id: str, email_type: str) -> None:
    """Record the timestamp of the last email of a given type for a learner.

    email_type values: 'reengagement', 'course_reminder', 'assignment_reminder',
                       'weekend', 'new_month'
    """
    import time as _t
    col_map = {
        "reengagement":        "last_reengagement_at",
        "course_reminder":     "last_course_reminder_at",
        "assignment_reminder": "last_assignment_reminder_at",
        "weekend":             "last_weekend_msg_at",
        "new_month":           "last_new_month_msg_at",
    }
    col = col_map.get(email_type)
    if not col:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO email_automation (learner_id, updated_at, {col})
                VALUES (%s, EXTRACT(EPOCH FROM NOW()), %s)
                ON CONFLICT (learner_id) DO UPDATE SET
                    {col}      = EXCLUDED.{col},
                    updated_at = EXCLUDED.updated_at
            """, (learner_id, _t.time()))


def set_email_opted_out(learner_id: str, opted_out: bool = True) -> None:
    """Honour an unsubscribe request."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_automation (learner_id, opted_out, updated_at)
                VALUES (%s, %s, EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (learner_id) DO UPDATE SET
                    opted_out  = EXCLUDED.opted_out,
                    updated_at = EXCLUDED.updated_at
            """, (learner_id, int(opted_out)))


def get_email_automation_candidates(email_type: str, cooldown_days: int) -> list[dict]:
    """Return confirmed learners who are eligible for a given email type.

    A learner is eligible when:
      - They have not opted out
      - The relevant last_*_at is older than cooldown_days (or NULL)

    Returns dicts with: learner_id, email, name, last_sent_at,
    plus learner_profile fields: xp, current_course, topics_seen, updated_at,
    assignments (pending count injected by callers as needed).
    """
    import time as _t
    import psycopg2.extras
    col_map = {
        "reengagement":        "ea.last_reengagement_at",
        "course_reminder":     "ea.last_course_reminder_at",
        "assignment_reminder": "ea.last_assignment_reminder_at",
        "weekend":             "ea.last_weekend_msg_at",
        "new_month":           "ea.last_new_month_msg_at",
    }
    col = col_map.get(email_type, "ea.last_reengagement_at")
    cutoff = _t.time() - (cooldown_days * 86400)

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    em.learner_id,
                    em.email,
                    em.name,
                    lp.xp,
                    lp.updated_at          AS last_activity_at,
                    lp.current_course,
                    lp.topics_seen,
                    lp.completed_projects,
                    {col}                  AS last_sent_at
                FROM email_accounts em
                LEFT JOIN email_automation ea
                       ON ea.learner_id = em.learner_id
                LEFT JOIN learner_profiles lp
                       ON lp.learner_id = em.learner_id
                WHERE em.confirmed = 1
                  AND em.email NOT LIKE '%@github.local'
                  AND (ea.opted_out IS NULL OR ea.opted_out = 0)
                  AND ({col} IS NULL OR {col} < %s)
            """, (cutoff,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]
