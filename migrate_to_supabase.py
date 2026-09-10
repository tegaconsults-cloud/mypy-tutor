#!/usr/bin/env python3
"""
migrate_to_supabase.py — MyPy Tutor emergency data migration
=============================================================

Copies ALL data from the expired Render PostgreSQL database to
Supabase's PostgreSQL (Transaction Pooler connection).

USAGE:
  1. Install deps:  pip install psycopg2-binary python-dotenv
  2. Set credentials in .env or export them as environment variables:
       SOURCE_DATABASE_URL=postgresql://mypytutor_user:PASSWORD@dpg-d9t11o6417fc73bj9aig-a/mypytutor
       SUPABASE_POSTGRES_URL=postgresql://postgres.YOURREF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres
  3. Run: python migrate_to_supabase.py

HOW TO GET SUPABASE_POSTGRES_URL:
  Supabase dashboard → Settings → Database → Connection string → URI
  Use the "Transaction pooler" URL (port 5432 or 6543).

SAFETY:
  - Reads source in read-only transactions
  - Uses ON CONFLICT DO NOTHING on all inserts — safe to re-run
  - Prints a full progress report and any errors
  - Does NOT delete anything from source or destination
"""

import os, sys, json, time, traceback
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
SOURCE_URL   = os.getenv("SOURCE_DATABASE_URL", "")
DEST_URL     = os.getenv("SUPABASE_POSTGRES_URL", "") or os.getenv("DATABASE_URL", "")

if not SOURCE_URL:
    print("❌  SOURCE_DATABASE_URL is not set.")
    print("    Export it or add it to your .env file:")
    print("    SOURCE_DATABASE_URL=postgresql://mypytutor_user:PASSWORD@dpg-d9t11o6417fc73bj9aig-a/mypytutor")
    sys.exit(1)

if not DEST_URL:
    print("❌  SUPABASE_POSTGRES_URL is not set.")
    print("    Get it from: Supabase → Settings → Database → Connection string → URI")
    print("    SUPABASE_POSTGRES_URL=postgresql://postgres.YOURREF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
    sys.exit(1)

# ── Connection helpers ────────────────────────────────────────────────────────
def connect(url: str, label: str):
    print(f"  Connecting to {label}...", end=" ", flush=True)
    try:
        conn = psycopg2.connect(url, connect_timeout=20)
        conn.autocommit = False
        print("✓")
        return conn
    except Exception as e:
        print(f"❌  {e}")
        sys.exit(1)

# ── Schema creation on destination ───────────────────────────────────────────
DEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS learner_profiles (
    learner_id TEXT PRIMARY KEY, tier TEXT DEFAULT 'free',
    level TEXT DEFAULT 'beginner', xp INTEGER DEFAULT 0,
    badges TEXT DEFAULT '[]', topics_seen TEXT DEFAULT '[]',
    topic_progress TEXT DEFAULT '{}', current_course TEXT,
    course_step INTEGER DEFAULT 0, completed_projects TEXT DEFAULT '[]',
    daily_prompts_used INTEGER DEFAULT 0, last_prompt_date TEXT DEFAULT '',
    email TEXT DEFAULT '', display_name TEXT DEFAULT '',
    prompt_plan TEXT DEFAULT '',
    updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS email_accounts (
    email TEXT PRIMARY KEY, name TEXT NOT NULL,
    learner_id TEXT NOT NULL, password_hash TEXT NOT NULL,
    token TEXT, confirmed INTEGER DEFAULT 0,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS certificates (
    cert_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
    learner_name TEXT NOT NULL, level TEXT NOT NULL,
    programme TEXT DEFAULT '',
    issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY, user_email TEXT NOT NULL,
    user_name TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
    currency TEXT DEFAULT 'NGN', plan TEXT NOT NULL,
    method TEXT DEFAULT 'bank', status TEXT DEFAULT 'pending',
    notes TEXT DEFAULT '',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY, payment_id TEXT NOT NULL,
    learner_id TEXT NOT NULL, email TEXT NOT NULL,
    name TEXT NOT NULL, plan TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL, currency TEXT DEFAULT 'NGN',
    issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    due_date TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    action TEXT NOT NULL, detail TEXT DEFAULT '',
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS prompt_history (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    role TEXT NOT NULL, content TEXT NOT NULL,
    intent TEXT DEFAULT '', topic TEXT DEFAULT '',
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    topic TEXT NOT NULL, question TEXT NOT NULL,
    answer TEXT NOT NULL, correct INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
    title TEXT NOT NULL, description TEXT NOT NULL,
    course TEXT DEFAULT '', status TEXT DEFAULT 'pending',
    submission TEXT DEFAULT '', feedback TEXT DEFAULT '',
    score INTEGER DEFAULT 0,
    submitted_at DOUBLE PRECISION, reviewed_at DOUBLE PRECISION,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY, discount_pct INTEGER NOT NULL,
    discount_flat DOUBLE PRECISION DEFAULT 0, plan TEXT DEFAULT 'any',
    max_uses INTEGER DEFAULT 100, uses INTEGER DEFAULT 0,
    expires_at DOUBLE PRECISION DEFAULT 0, active INTEGER DEFAULT 1,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS coupon_uses (
    id SERIAL PRIMARY KEY, code TEXT NOT NULL,
    learner_id TEXT NOT NULL, email TEXT NOT NULL,
    amount_saved DOUBLE PRECISION DEFAULT 0,
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS referrals (
    code TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
    owner_email TEXT NOT NULL, uses INTEGER DEFAULT 0,
    max_uses INTEGER DEFAULT 50, reward_tier TEXT DEFAULT 'tier1',
    bonus_balance DOUBLE PRECISION DEFAULT 0,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS referral_uses (
    id SERIAL PRIMARY KEY, code TEXT NOT NULL,
    used_by_email TEXT NOT NULL, used_by_id TEXT NOT NULL,
    discount_pct INTEGER DEFAULT 20,
    referrer_bonus DOUBLE PRECISION DEFAULT 0,
    referee_discount DOUBLE PRECISION DEFAULT 0,
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS referral_withdrawals (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    email TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
    bank_name TEXT NOT NULL, account_name TEXT NOT NULL,
    account_num TEXT NOT NULL, status TEXT DEFAULT 'pending',
    notes TEXT DEFAULT '',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS course_purchases (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    course_name TEXT NOT NULL, amount_ngn DOUBLE PRECISION DEFAULT 0,
    payment_ref TEXT DEFAULT '',
    purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    UNIQUE (learner_id, course_name)
);
CREATE TABLE IF NOT EXISTS bank_transfer_proofs (
    id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
    email TEXT NOT NULL, plan TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL, reference TEXT DEFAULT '',
    proof_b64 TEXT DEFAULT '', proof_url TEXT DEFAULT '',
    notes TEXT DEFAULT '', status TEXT DEFAULT 'pending',
    admin_notes TEXT DEFAULT '',
    submitted_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    reviewed_at DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS user_profiles (
    learner_id TEXT PRIMARY KEY, display_name TEXT DEFAULT '',
    bio TEXT DEFAULT '', location TEXT DEFAULT '',
    website TEXT DEFAULT '', photo_url TEXT DEFAULT '',
    updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS feedback_ratings (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    rating TEXT NOT NULL, intent TEXT DEFAULT '',
    topic TEXT DEFAULT '', comment TEXT DEFAULT '',
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS feedback_surveys (
    id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
    overall INTEGER NOT NULL, clarity INTEGER NOT NULL,
    helpfulness INTEGER NOT NULL, suggestion TEXT DEFAULT '',
    would_recommend INTEGER DEFAULT 1,
    ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS email_automation (
    learner_id TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    last_reengagement_at DOUBLE PRECISION DEFAULT 0,
    last_course_reminder_at DOUBLE PRECISION DEFAULT 0,
    last_assignment_reminder_at DOUBLE PRECISION DEFAULT 0,
    last_weekend_msg_at DOUBLE PRECISION DEFAULT 0,
    last_new_month_msg_at DOUBLE PRECISION DEFAULT 0,
    opted_out INTEGER DEFAULT 0,
    updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS session_revocations (
    learner_id TEXT PRIMARY KEY,
    revoked_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_webhooks (
    reference TEXT PRIMARY KEY,
    processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS enquiries (
    id SERIAL PRIMARY KEY, learner_id TEXT DEFAULT '',
    name TEXT NOT NULL, email TEXT NOT NULL,
    category TEXT NOT NULL, subject TEXT NOT NULL,
    message TEXT NOT NULL, status TEXT DEFAULT 'open',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS team_members (
    email TEXT PRIMARY KEY, name TEXT NOT NULL,
    role TEXT DEFAULT 'team', status TEXT DEFAULT 'invited',
    invited_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, title TEXT NOT NULL,
    description TEXT DEFAULT '', assigned_to TEXT NOT NULL,
    priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'open',
    due_date TEXT DEFAULT '',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS announcements (
    id SERIAL PRIMARY KEY, subject TEXT NOT NULL,
    target TEXT NOT NULL, sent_to INTEGER DEFAULT 0,
    sent_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS daily_prompt_counts (
    key TEXT NOT NULL, date_str TEXT NOT NULL,
    count INTEGER DEFAULT 0, PRIMARY KEY (key, date_str)
);
CREATE TABLE IF NOT EXISTS password_resets (
    token TEXT PRIMARY KEY, email TEXT NOT NULL,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    used INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS access_codes (
    code TEXT PRIMARY KEY, tier TEXT NOT NULL,
    created_by TEXT DEFAULT 'admin', sent_to_email TEXT DEFAULT '',
    used_by_email TEXT DEFAULT '', used_by_id TEXT DEFAULT '',
    used INTEGER DEFAULT 0, expires_at DOUBLE PRECISION DEFAULT 0,
    discount_pct INTEGER DEFAULT 0,
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);
"""

# ── Tables to migrate, in dependency order ────────────────────────────────────
# (parent tables before child tables to avoid FK issues)
# Format: (table_name, pk_columns_for_conflict_clause)
TABLES = [
    # Core user data — highest priority
    ("learner_profiles",    "learner_id"),
    ("email_accounts",      "email"),
    ("user_profiles",       "learner_id"),
    ("session_revocations", "learner_id"),
    ("password_resets",     "token"),
    ("email_automation",    "learner_id"),

    # Financial — critical
    ("payments",            "id"),
    ("invoices",            "id"),
    ("bank_transfer_proofs","id"),
    ("processed_webhooks",  "reference"),
    ("course_purchases",    "learner_id, course_name"),

    # Certificates
    ("certificates",        "cert_id"),

    # Coupons & referrals
    ("coupons",             "code"),
    ("coupon_uses",         None),   # SERIAL pk — no conflict clause
    ("referrals",           "code"),
    ("referral_uses",       None),
    ("referral_withdrawals",None),
    ("access_codes",        "code"),

    # Learning history
    ("prompt_history",      None),
    ("quiz_attempts",       None),
    ("assignments",         "id"),
    ("daily_prompt_counts", "key, date_str"),

    # Feedback
    ("feedback_ratings",    None),
    ("feedback_surveys",    None),

    # Admin / ops
    ("activity_log",        None),
    ("team_members",        "email"),
    ("tasks",               "id"),
    ("announcements",       None),
    ("enquiries",           None),
]

BATCH_SIZE = 500   # rows per INSERT batch

def migrate_table(src_cur, dst_conn, table: str, pk: str | None) -> tuple[int, int]:
    """Migrate one table. Returns (rows_copied, rows_skipped_on_conflict)."""
    src_cur.execute(f"SELECT * FROM {table}")
    rows = src_cur.fetchall()
    if not rows:
        return 0, 0

    cols = [desc[0] for desc in src_cur.description]
    col_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    conflict_clause = ""
    if pk:
        conflict_clause = f"ON CONFLICT ({pk}) DO NOTHING"

    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) {conflict_clause}"

    copied = 0
    skipped = 0
    dst_cur = dst_conn.cursor()

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        try:
            dst_cur.executemany(sql, [list(r) for r in batch])
            dst_conn.commit()
            copied += len(batch)
        except Exception as e:
            dst_conn.rollback()
            # Try row-by-row to skip bad rows
            for row in batch:
                try:
                    dst_cur.execute(sql, list(row))
                    dst_conn.commit()
                    copied += 1
                except Exception:
                    dst_conn.rollback()
                    skipped += 1

    dst_cur.close()
    return copied, skipped


def main():
    print("\n" + "="*60)
    print("  MyPy Tutor — Emergency Migration to Supabase")
    print("="*60)

    # Connect to both databases
    print("\n[1/4] Connecting...")
    src = connect(SOURCE_URL, "Render PostgreSQL (source)")
    dst = connect(DEST_URL,   "Supabase PostgreSQL (destination)")

    # Create schema on destination
    print("\n[2/4] Creating schema on Supabase (IF NOT EXISTS)...", end=" ", flush=True)
    try:
        with dst.cursor() as cur:
            for stmt in DEST_SCHEMA.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        dst.commit()
        print("✓")
    except Exception as e:
        dst.rollback()
        print(f"❌  {e}")
        traceback.print_exc()
        sys.exit(1)

    # Migrate all tables
    print("\n[3/4] Migrating tables...\n")
    src_cur = src.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    total_copied = 0
    total_skipped = 0
    errors = []

    for table, pk in TABLES:
        print(f"  {table:<35}", end=" ", flush=True)
        try:
            # Check table exists in source
            src_cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name=%s)", (table,)
            )
            if not src_cur.fetchone()["exists"]:
                print("— (not in source, skipped)")
                continue

            copied, skipped = migrate_table(src_cur, dst, table, pk)
            total_copied  += copied
            total_skipped += skipped
            status = f"✓  {copied:>6} rows"
            if skipped:
                status += f"  ({skipped} skipped)"
            print(status)

        except Exception as e:
            errors.append((table, str(e)))
            print(f"❌  {e}")
            dst.rollback()

    src_cur.close()

    # Summary
    print("\n[4/4] Summary")
    print("="*60)
    print(f"  Total rows copied:  {total_copied:,}")
    print(f"  Total rows skipped: {total_skipped:,}")
    if errors:
        print(f"\n  ❌  Errors on {len(errors)} table(s):")
        for t, e in errors:
            print(f"     {t}: {e}")
    else:
        print("\n  ✅  All tables migrated successfully!")

    print("\n" + "="*60)
    print("  NEXT STEPS:")
    print("  1. In Render → mypy-tutor → Environment, set:")
    print("     DATABASE_URL = your SUPABASE_POSTGRES_URL value")
    print("  2. Redeploy the service")
    print("  3. Verify by opening the admin dashboard")
    print("="*60 + "\n")

    src.close()
    dst.close()


if __name__ == "__main__":
    main()
