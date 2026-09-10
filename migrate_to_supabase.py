#!/usr/bin/env python3
"""
migrate_to_supabase.py — MyPy Tutor emergency data migration
=============================================================

Copies ALL data from the suspended Render PostgreSQL database into
Supabase PostgreSQL (which is now the primary database).

USAGE:
  1. Install deps:
       pip install psycopg2-binary python-dotenv

  2. Create a .env file in this directory (or export env vars):
       SOURCE_DATABASE_URL=postgresql://mypytutor_user:PASSWORD@dpg-d9t11o6417fc73bj9aig-a.oregon-postgres.render.com/mypytutor
       DATABASE_URL=postgresql://postgres:PASSWORD@db.fzgllhmstxrshsfzcrqu.supabase.co:5432/postgres

     NOTE: SOURCE_DATABASE_URL = your Render DB (use the EXTERNAL URL, not internal)
           DATABASE_URL         = your Supabase DB (already set in Render environment)

  3. Run:
       python migrate_to_supabase.py

  4. After success, verify at:
       https://mypytutor.onrender.com/health
       https://mypytutor.onrender.com/admin.html

HOW TO GET THE RENDER EXTERNAL URL:
  Render → mypy-tutor-db → Connect → External Database URL
  It looks like: postgresql://mypytutor_user:PASSWORD@dpg-XXX.oregon-postgres.render.com/mypytutor
  (The DB is SUSPENDED but still readable — you have ~13 days before deletion)

SAFETY:
  - Reads Render DB with a read-only transaction
  - Uses ON CONFLICT DO NOTHING — safe to re-run multiple times
  - Does NOT delete anything from source or destination
  - Skips tables that don't exist in the source
"""

import os
import sys
import traceback
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
SOURCE_URL = os.getenv("SOURCE_DATABASE_URL", "")
DEST_URL   = os.getenv("DATABASE_URL", "") or os.getenv("SUPABASE_POSTGRES_URL", "")

# Add SSL to destination if missing (Supabase requires it)
def _ssl(url: str) -> str:
    if not url or "sslmode" in url:
        return url
    return url + ("&" if "?" in url else "?") + "sslmode=require"

DEST_URL = _ssl(DEST_URL)

if not SOURCE_URL:
    print("\n❌  SOURCE_DATABASE_URL is not set.")
    print("    Get it from: Render → mypy-tutor-db → Connect → External Database URL")
    print("    Add to .env: SOURCE_DATABASE_URL=postgresql://mypytutor_user:PASS@dpg-XXX.oregon-postgres.render.com/mypytutor\n")
    sys.exit(1)

if not DEST_URL:
    print("\n❌  DATABASE_URL (Supabase) is not set.")
    print("    Add to .env: DATABASE_URL=postgresql://postgres:PASS@db.fzgllhmstxrshsfzcrqu.supabase.co:5432/postgres\n")
    sys.exit(1)

# ── Connection test ───────────────────────────────────────────────────────────
def test_connect(url: str, label: str):
    print(f"  Testing {label}...", end=" ", flush=True)
    # Try with sslmode=require first, then without SSL (suspended Render DBs may reject SSL)
    urls_to_try = [url]
    if "sslmode" not in url:
        urls_to_try.append(url + ("&" if "?" in url else "?") + "sslmode=disable")
        urls_to_try.append(url + ("&" if "?" in url else "?") + "sslmode=allow")
    for attempt_url in urls_to_try:
        try:
            conn = psycopg2.connect(attempt_url, connect_timeout=20)
            cur  = conn.cursor()
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0].split(",")[0]
            conn.close()
            print(f"✓  {ver}")
            return attempt_url   # return the URL that worked
        except Exception as e:
            last_err = e
    print(f"❌  {last_err}")
    return None

# ── Schema on destination ─────────────────────────────────────────────────────
DEST_SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS learner_profiles (
        learner_id TEXT PRIMARY KEY, tier TEXT DEFAULT 'free',
        level TEXT DEFAULT 'beginner', xp INTEGER DEFAULT 0,
        badges TEXT DEFAULT '[]', topics_seen TEXT DEFAULT '[]',
        topic_progress TEXT DEFAULT '{}', current_course TEXT,
        course_step INTEGER DEFAULT 0, completed_projects TEXT DEFAULT '[]',
        daily_prompts_used INTEGER DEFAULT 0, last_prompt_date TEXT DEFAULT '',
        email TEXT DEFAULT '', display_name TEXT DEFAULT '',
        prompt_plan TEXT DEFAULT '',
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS email_accounts (
        email TEXT PRIMARY KEY, name TEXT NOT NULL,
        learner_id TEXT NOT NULL, password_hash TEXT NOT NULL,
        token TEXT, confirmed INTEGER DEFAULT 0,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS certificates (
        cert_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
        learner_name TEXT NOT NULL, level TEXT NOT NULL,
        programme TEXT DEFAULT '',
        issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY, user_email TEXT NOT NULL,
        user_name TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
        currency TEXT DEFAULT 'NGN', plan TEXT NOT NULL,
        method TEXT DEFAULT 'bank', status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY, payment_id TEXT NOT NULL,
        learner_id TEXT NOT NULL, email TEXT NOT NULL,
        name TEXT NOT NULL, plan TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL, currency TEXT DEFAULT 'NGN',
        issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        due_date TEXT DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS activity_log (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        action TEXT NOT NULL, detail TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS prompt_history (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        role TEXT NOT NULL, content TEXT NOT NULL,
        intent TEXT DEFAULT '', topic TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS quiz_attempts (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        topic TEXT NOT NULL, question TEXT NOT NULL,
        answer TEXT NOT NULL, correct INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
        title TEXT NOT NULL, description TEXT NOT NULL,
        course TEXT DEFAULT '', status TEXT DEFAULT 'pending',
        submission TEXT DEFAULT '', feedback TEXT DEFAULT '',
        score INTEGER DEFAULT 0,
        submitted_at DOUBLE PRECISION, reviewed_at DOUBLE PRECISION,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS coupons (
        code TEXT PRIMARY KEY, discount_pct INTEGER NOT NULL,
        discount_flat DOUBLE PRECISION DEFAULT 0, plan TEXT DEFAULT 'any',
        max_uses INTEGER DEFAULT 100, uses INTEGER DEFAULT 0,
        expires_at DOUBLE PRECISION DEFAULT 0, active INTEGER DEFAULT 1,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS coupon_uses (
        id SERIAL PRIMARY KEY, code TEXT NOT NULL,
        learner_id TEXT NOT NULL, email TEXT NOT NULL,
        amount_saved DOUBLE PRECISION DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS referrals (
        code TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
        owner_email TEXT NOT NULL, uses INTEGER DEFAULT 0,
        max_uses INTEGER DEFAULT 50, reward_tier TEXT DEFAULT 'tier1',
        bonus_balance DOUBLE PRECISION DEFAULT 0,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS referral_uses (
        id SERIAL PRIMARY KEY, code TEXT NOT NULL,
        used_by_email TEXT NOT NULL, used_by_id TEXT NOT NULL,
        discount_pct INTEGER DEFAULT 20,
        referrer_bonus DOUBLE PRECISION DEFAULT 0,
        referee_discount DOUBLE PRECISION DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS referral_withdrawals (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        email TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
        bank_name TEXT NOT NULL, account_name TEXT NOT NULL,
        account_num TEXT NOT NULL, status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS course_purchases (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        course_name TEXT NOT NULL, amount_ngn DOUBLE PRECISION DEFAULT 0,
        payment_ref TEXT DEFAULT '',
        purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        UNIQUE (learner_id, course_name))""",
    """CREATE TABLE IF NOT EXISTS bank_transfer_proofs (
        id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
        email TEXT NOT NULL, plan TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL, reference TEXT DEFAULT '',
        proof_b64 TEXT DEFAULT '', proof_url TEXT DEFAULT '',
        notes TEXT DEFAULT '', status TEXT DEFAULT 'pending',
        admin_notes TEXT DEFAULT '',
        submitted_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        reviewed_at DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS user_profiles (
        learner_id TEXT PRIMARY KEY, display_name TEXT DEFAULT '',
        bio TEXT DEFAULT '', location TEXT DEFAULT '',
        website TEXT DEFAULT '', photo_url TEXT DEFAULT '',
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS feedback_ratings (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        rating TEXT NOT NULL, intent TEXT DEFAULT '',
        topic TEXT DEFAULT '', comment TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS feedback_surveys (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        overall INTEGER NOT NULL, clarity INTEGER NOT NULL,
        helpfulness INTEGER NOT NULL, suggestion TEXT DEFAULT '',
        would_recommend INTEGER DEFAULT 1,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS email_automation (
        learner_id TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        last_reengagement_at DOUBLE PRECISION DEFAULT 0,
        last_course_reminder_at DOUBLE PRECISION DEFAULT 0,
        last_assignment_reminder_at DOUBLE PRECISION DEFAULT 0,
        last_weekend_msg_at DOUBLE PRECISION DEFAULT 0,
        last_new_month_msg_at DOUBLE PRECISION DEFAULT 0,
        opted_out INTEGER DEFAULT 0,
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS session_revocations (
        learner_id TEXT PRIMARY KEY,
        revoked_at DOUBLE PRECISION NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS processed_webhooks (
        reference TEXT PRIMARY KEY,
        processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS enquiries (
        id SERIAL PRIMARY KEY, learner_id TEXT DEFAULT '',
        name TEXT NOT NULL, email TEXT NOT NULL,
        category TEXT NOT NULL, subject TEXT NOT NULL,
        message TEXT NOT NULL, status TEXT DEFAULT 'open',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS team_members (
        email TEXT PRIMARY KEY, name TEXT NOT NULL,
        role TEXT DEFAULT 'team', status TEXT DEFAULT 'invited',
        invited_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL,
        description TEXT DEFAULT '', assigned_to TEXT NOT NULL,
        priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'open',
        due_date TEXT DEFAULT '',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS announcements (
        id SERIAL PRIMARY KEY, subject TEXT NOT NULL,
        target TEXT NOT NULL, sent_to INTEGER DEFAULT 0,
        sent_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
    """CREATE TABLE IF NOT EXISTS daily_prompt_counts (
        key TEXT NOT NULL, date_str TEXT NOT NULL,
        count INTEGER DEFAULT 0, PRIMARY KEY (key, date_str))""",
    """CREATE TABLE IF NOT EXISTS password_resets (
        token TEXT PRIMARY KEY, email TEXT NOT NULL,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        used INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS access_codes (
        code TEXT PRIMARY KEY, tier TEXT NOT NULL,
        created_by TEXT DEFAULT 'admin', sent_to_email TEXT DEFAULT '',
        used_by_email TEXT DEFAULT '', used_by_id TEXT DEFAULT '',
        used INTEGER DEFAULT 0, expires_at DOUBLE PRECISION DEFAULT 0,
        discount_pct INTEGER DEFAULT 0,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))""",
]

# Safe column migrations (idempotent)
MIGRATIONS = [
    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS programme TEXT DEFAULT ''",
    "ALTER TABLE access_codes ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0",
]

# ── Tables in dependency order ────────────────────────────────────────────────
# (table_name, conflict_pk_or_None)
TABLES = [
    ("learner_profiles",     "learner_id"),
    ("email_accounts",       "email"),
    ("user_profiles",        "learner_id"),
    ("session_revocations",  "learner_id"),
    ("password_resets",      "token"),
    ("email_automation",     "learner_id"),
    ("payments",             "id"),
    ("invoices",             "id"),
    ("bank_transfer_proofs", "id"),
    ("processed_webhooks",   "reference"),
    ("course_purchases",     "learner_id, course_name"),
    ("certificates",         "cert_id"),
    ("coupons",              "code"),
    ("coupon_uses",          None),
    ("referrals",            "code"),
    ("referral_uses",        None),
    ("referral_withdrawals", None),
    ("access_codes",         "code"),
    ("prompt_history",       None),
    ("quiz_attempts",        None),
    ("assignments",          "id"),
    ("daily_prompt_counts",  "key, date_str"),
    ("feedback_ratings",     None),
    ("feedback_surveys",     None),
    ("activity_log",         None),
    ("team_members",         "email"),
    ("tasks",                "id"),
    ("announcements",        None),
    ("enquiries",            None),
]

BATCH = 500

def table_exists(cur, name: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s)",
        (name,)
    )
    return cur.fetchone()[0]

def migrate_table(src_cur, dst_conn, table: str, pk: str | None) -> tuple[int, int]:
    src_cur.execute(f"SELECT * FROM {table}")
    rows = src_cur.fetchall()
    if not rows:
        return 0, 0

    cols = [d[0] for d in src_cur.description]
    col_list     = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    conflict     = f"ON CONFLICT ({pk}) DO NOTHING" if pk else ""
    sql          = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) {conflict}"

    copied = skipped = 0
    dst_cur = dst_conn.cursor()

    for i in range(0, len(rows), BATCH):
        batch = [list(r) for r in rows[i:i + BATCH]]
        try:
            dst_cur.executemany(sql, batch)
            dst_conn.commit()
            copied += len(batch)
        except Exception:
            dst_conn.rollback()
            for row in batch:
                try:
                    dst_cur.execute(sql, row)
                    dst_conn.commit()
                    copied += 1
                except Exception:
                    dst_conn.rollback()
                    skipped += 1

    dst_cur.close()
    return copied, skipped


def main():
    print("\n" + "=" * 62)
    print("  MyPy Tutor — Render → Supabase Recovery Migration")
    print("=" * 62)

    # ── Step 1: Connectivity tests ────────────────────────────────
    print("\n[1/4] Testing connections...")
    src_url  = test_connect(SOURCE_URL, "Render DB (source — suspended but readable)")
    dest_url = test_connect(DEST_URL,   "Supabase PostgreSQL (destination)")

    if not src_url:
        print("\n❌  Cannot reach Render source DB.")
        print("    Options:")
        print("    1. The password in SOURCE_DATABASE_URL may be wrong — check .env")
        print("    2. The Render DB is fully deleted (only 13 days after expiry)")
        print("    3. Try the Render dashboard: mypy-tutor-db → Connect → External URL")
        print("\n    If Render DB is gone, check Supabase for existing data:")
        print("    Supabase → Table Editor → learner_profiles")
        sys.exit(1)

    if not dest_url:
        print("\n❌  Cannot reach Supabase destination DB.")
        print("    Check DATABASE_URL in your .env file:")
        print("    Should be: postgresql://postgres:PASS@db.fzgllhmstxrshsfzcrqu.supabase.co:5432/postgres")
        sys.exit(1)

    # ── Step 2: Create schema on Supabase ─────────────────────────
    print("\n[2/4] Creating schema on Supabase (IF NOT EXISTS)...", end=" ", flush=True)
    dst = psycopg2.connect(dest_url, connect_timeout=20)
    dst.autocommit = False
    try:
        with dst.cursor() as cur:
            for stmt in DEST_SCHEMA_STATEMENTS:
                cur.execute(stmt)
            for m in MIGRATIONS:
                try:
                    cur.execute(m)
                except Exception:
                    pass
        dst.commit()
        print("✓")
    except Exception as e:
        dst.rollback()
        print(f"❌  {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── Step 3: Migrate all tables ────────────────────────────────
    print("\n[3/4] Migrating tables...\n")
    src = psycopg2.connect(src_url, connect_timeout=20)
    src.autocommit = True           # read-only — no transaction needed
    src_cur = src.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    total_copied = total_skipped = 0
    errors = []

    for table, pk in TABLES:
        print(f"  {table:<35}", end=" ", flush=True)
        try:
            if not table_exists(src_cur, table):
                print("— (not in source)")
                continue

            copied, skipped = migrate_table(src_cur, dst, table, pk)
            total_copied  += copied
            total_skipped += skipped
            msg = f"✓  {copied:>6} rows"
            if skipped:
                msg += f"  ({skipped} conflict-skipped)"
            print(msg)

        except Exception as e:
            errors.append((table, str(e)))
            print(f"❌  {e}")
            dst.rollback()

    src_cur.close()
    src.close()

    # ── Step 4: Summary ───────────────────────────────────────────
    print("\n[4/4] Summary")
    print("=" * 62)
    print(f"  Rows copied:   {total_copied:,}")
    print(f"  Rows skipped:  {total_skipped:,}  (already existed — safe)")

    if errors:
        print(f"\n  ❌  Errors on {len(errors)} table(s):")
        for t, e in errors:
            print(f"     • {t}: {e}")
        print("\n  Re-run the script to retry failed tables (it is idempotent).")
    else:
        print("\n  ✅  All tables migrated successfully!")

    print("""
  NEXT STEPS:
  ─────────────────────────────────────────────────────────
  1. Verify in Supabase dashboard → Table Editor — check that
     learner_profiles, payments, certificates, email_accounts
     have rows.
  2. Open https://mypytutor.onrender.com/admin.html and confirm
     users and payments are visible.
  3. The Render DB can now be safely ignored — Supabase is primary.
""")
    dst.close()


if __name__ == "__main__":
    main()
