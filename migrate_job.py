#!/usr/bin/env python3
"""
migrate_job.py — One-shot Render job: copy Render PostgreSQL → Supabase PostgreSQL

Deploy this as a Render Job (one-time run), NOT as the web service.
It reads SOURCE_DATABASE_URL and DATABASE_URL from environment variables
already set in the Render dashboard.

Render Jobs have access to the internal Render network, so they can
reach the suspended Render DB even after it stops accepting external connections.

HOW TO RUN THIS ON RENDER:
  1. Push this file to your repo (already done)
  2. In Render dashboard → New → Job
  3. Connect to this same GitHub repo
  4. Set:
       Build Command:  pip install psycopg2-binary
       Start Command:  python migrate_job.py
  5. Add environment variables:
       SOURCE_DATABASE_URL = postgresql://mypytutor_user:mNHjh3YBNTNkjwsH6rHaHMKb7B5newrg@dpg-d9t11o6417fc73bj9aig-a/mypytutor
       DATABASE_URL        = (already set in your mypy-tutor service — copy the same value)
  6. Click Run Job
  7. Watch the logs — it will print rows copied per table

NOTE: SOURCE_DATABASE_URL for a Render Job uses the INTERNAL hostname
(dpg-d9t11o6417fc73bj9aig-a — no .oregon-postgres.render.com suffix)
because the job runs inside Render's network.
"""

import os
import sys
import traceback
import psycopg2
import psycopg2.extras

SOURCE_URL = os.getenv("SOURCE_DATABASE_URL", "")
DEST_URL   = os.getenv("DATABASE_URL", "")

def _ssl(url):
    if not url or "sslmode" in url:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + "sslmode=require"

DEST_URL = _ssl(DEST_URL)

if not SOURCE_URL:
    print("ERROR: SOURCE_DATABASE_URL not set"); sys.exit(1)
if not DEST_URL:
    print("ERROR: DATABASE_URL not set"); sys.exit(1)

# ── Schema statements ─────────────────────────────────────────────────────────
SCHEMA = [
    "CREATE TABLE IF NOT EXISTS learner_profiles (learner_id TEXT PRIMARY KEY, tier TEXT DEFAULT 'free', level TEXT DEFAULT 'beginner', xp INTEGER DEFAULT 0, badges TEXT DEFAULT '[]', topics_seen TEXT DEFAULT '[]', topic_progress TEXT DEFAULT '{}', current_course TEXT, course_step INTEGER DEFAULT 0, completed_projects TEXT DEFAULT '[]', daily_prompts_used INTEGER DEFAULT 0, last_prompt_date TEXT DEFAULT '', email TEXT DEFAULT '', display_name TEXT DEFAULT '', prompt_plan TEXT DEFAULT '', updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS email_accounts (email TEXT PRIMARY KEY, name TEXT NOT NULL, learner_id TEXT NOT NULL, password_hash TEXT NOT NULL, token TEXT, confirmed INTEGER DEFAULT 0, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS certificates (cert_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, learner_name TEXT NOT NULL, level TEXT NOT NULL, programme TEXT DEFAULT '', issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_email TEXT NOT NULL, user_name TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL, currency TEXT DEFAULT 'NGN', plan TEXT NOT NULL, method TEXT DEFAULT 'bank', status TEXT DEFAULT 'pending', notes TEXT DEFAULT '', created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, payment_id TEXT NOT NULL, learner_id TEXT NOT NULL, email TEXT NOT NULL, name TEXT NOT NULL, plan TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL, currency TEXT DEFAULT 'NGN', issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()), due_date TEXT DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS activity_log (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, action TEXT NOT NULL, detail TEXT DEFAULT '', ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS prompt_history (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, intent TEXT DEFAULT '', topic TEXT DEFAULT '', ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS quiz_attempts (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, topic TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL, correct INTEGER DEFAULT 0, score INTEGER DEFAULT 0, ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS assignments (id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, course TEXT DEFAULT '', status TEXT DEFAULT 'pending', submission TEXT DEFAULT '', feedback TEXT DEFAULT '', score INTEGER DEFAULT 0, submitted_at DOUBLE PRECISION, reviewed_at DOUBLE PRECISION, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, discount_pct INTEGER NOT NULL, discount_flat DOUBLE PRECISION DEFAULT 0, plan TEXT DEFAULT 'any', max_uses INTEGER DEFAULT 100, uses INTEGER DEFAULT 0, expires_at DOUBLE PRECISION DEFAULT 0, active INTEGER DEFAULT 1, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS coupon_uses (id SERIAL PRIMARY KEY, code TEXT NOT NULL, learner_id TEXT NOT NULL, email TEXT NOT NULL, amount_saved DOUBLE PRECISION DEFAULT 0, ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS referrals (code TEXT PRIMARY KEY, owner_id TEXT NOT NULL, owner_email TEXT NOT NULL, uses INTEGER DEFAULT 0, max_uses INTEGER DEFAULT 50, reward_tier TEXT DEFAULT 'tier1', bonus_balance DOUBLE PRECISION DEFAULT 0, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS referral_uses (id SERIAL PRIMARY KEY, code TEXT NOT NULL, used_by_email TEXT NOT NULL, used_by_id TEXT NOT NULL, discount_pct INTEGER DEFAULT 20, referrer_bonus DOUBLE PRECISION DEFAULT 0, referee_discount DOUBLE PRECISION DEFAULT 0, ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS referral_withdrawals (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, email TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL, bank_name TEXT NOT NULL, account_name TEXT NOT NULL, account_num TEXT NOT NULL, status TEXT DEFAULT 'pending', notes TEXT DEFAULT '', created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS course_purchases (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, course_name TEXT NOT NULL, amount_ngn DOUBLE PRECISION DEFAULT 0, payment_ref TEXT DEFAULT '', purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()), UNIQUE(learner_id, course_name))",
    "CREATE TABLE IF NOT EXISTS bank_transfer_proofs (id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, email TEXT NOT NULL, plan TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL, reference TEXT DEFAULT '', proof_b64 TEXT DEFAULT '', proof_url TEXT DEFAULT '', notes TEXT DEFAULT '', status TEXT DEFAULT 'pending', admin_notes TEXT DEFAULT '', submitted_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()), reviewed_at DOUBLE PRECISION)",
    "CREATE TABLE IF NOT EXISTS user_profiles (learner_id TEXT PRIMARY KEY, display_name TEXT DEFAULT '', bio TEXT DEFAULT '', location TEXT DEFAULT '', website TEXT DEFAULT '', photo_url TEXT DEFAULT '', updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS feedback_ratings (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, rating TEXT NOT NULL, intent TEXT DEFAULT '', topic TEXT DEFAULT '', comment TEXT DEFAULT '', ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS feedback_surveys (id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL, overall INTEGER NOT NULL, clarity INTEGER NOT NULL, helpfulness INTEGER NOT NULL, suggestion TEXT DEFAULT '', would_recommend INTEGER DEFAULT 1, ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS email_automation (learner_id TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '', name TEXT NOT NULL DEFAULT '', last_reengagement_at DOUBLE PRECISION DEFAULT 0, last_course_reminder_at DOUBLE PRECISION DEFAULT 0, last_assignment_reminder_at DOUBLE PRECISION DEFAULT 0, last_weekend_msg_at DOUBLE PRECISION DEFAULT 0, last_new_month_msg_at DOUBLE PRECISION DEFAULT 0, opted_out INTEGER DEFAULT 0, updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS session_revocations (learner_id TEXT PRIMARY KEY, revoked_at DOUBLE PRECISION NOT NULL)",
    "CREATE TABLE IF NOT EXISTS processed_webhooks (reference TEXT PRIMARY KEY, processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS enquiries (id SERIAL PRIMARY KEY, learner_id TEXT DEFAULT '', name TEXT NOT NULL, email TEXT NOT NULL, category TEXT NOT NULL, subject TEXT NOT NULL, message TEXT NOT NULL, status TEXT DEFAULT 'open', created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS team_members (email TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT DEFAULT 'team', status TEXT DEFAULT 'invited', invited_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '', assigned_to TEXT NOT NULL, priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'open', due_date TEXT DEFAULT '', created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS announcements (id SERIAL PRIMARY KEY, subject TEXT NOT NULL, target TEXT NOT NULL, sent_to INTEGER DEFAULT 0, sent_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
    "CREATE TABLE IF NOT EXISTS daily_prompt_counts (key TEXT NOT NULL, date_str TEXT NOT NULL, count INTEGER DEFAULT 0, PRIMARY KEY(key, date_str))",
    "CREATE TABLE IF NOT EXISTS password_resets (token TEXT PRIMARY KEY, email TEXT NOT NULL, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()), used INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS access_codes (code TEXT PRIMARY KEY, tier TEXT NOT NULL, created_by TEXT DEFAULT 'admin', sent_to_email TEXT DEFAULT '', used_by_email TEXT DEFAULT '', used_by_id TEXT DEFAULT '', used INTEGER DEFAULT 0, expires_at DOUBLE PRECISION DEFAULT 0, discount_pct INTEGER DEFAULT 0, created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))",
]

MIGRATIONS = [
    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS programme TEXT DEFAULT ''",
    "ALTER TABLE access_codes ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0",
]

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

BATCH = 200

def connect(url, label, timeout=20):
    print(f"Connecting to {label}...", end=" ", flush=True)
    # Try multiple SSL modes
    for mode in ["require", "allow", "disable", ""]:
        try:
            test_url = url
            if mode:
                sep = "&" if "?" in url else "?"
                test_url = f"{url}{sep}sslmode={mode}"
            conn = psycopg2.connect(test_url, connect_timeout=timeout)
            print(f"OK (sslmode={mode or 'default'})")
            return conn, test_url
        except Exception as e:
            last = e
    print(f"FAILED: {last}")
    return None, None

def table_exists(cur, name):
    cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s)", (name,))
    return cur.fetchone()[0]

def migrate_table(src_cur, dst, table, pk):
    src_cur.execute(f"SELECT * FROM {table}")
    rows = src_cur.fetchall()
    if not rows:
        return 0, 0
    cols = [d[0] for d in src_cur.description]
    sql  = "INSERT INTO {} ({}) VALUES ({}) {}".format(
        table,
        ", ".join(cols),
        ", ".join(["%s"] * len(cols)),
        f"ON CONFLICT ({pk}) DO NOTHING" if pk else ""
    )
    copied = skipped = 0
    dst_cur = dst.cursor()
    for i in range(0, len(rows), BATCH):
        batch = [list(r) for r in rows[i:i+BATCH]]
        try:
            dst_cur.executemany(sql, batch)
            dst.commit()
            copied += len(batch)
        except Exception:
            dst.rollback()
            for row in batch:
                try:
                    dst_cur.execute(sql, row)
                    dst.commit()
                    copied += 1
                except Exception:
                    dst.rollback()
                    skipped += 1
    dst_cur.close()
    return copied, skipped

def main():
    print("=" * 60)
    print("  MyPy Tutor — Render Job: DB Migration to Supabase")
    print("=" * 60)

    src, src_url = connect(SOURCE_URL, "Render PostgreSQL (source)")
    if not src:
        print("\nCannot reach source DB. Using internal Render hostname?")
        print(f"SOURCE_DATABASE_URL = {SOURCE_URL[:60]}...")
        sys.exit(1)

    dst, dst_url = connect(DEST_URL, "Supabase PostgreSQL (destination)")
    if not dst:
        print("\nCannot reach Supabase. Check DATABASE_URL.")
        sys.exit(1)

    # Create schema
    print("\nCreating schema on Supabase...", end=" ", flush=True)
    try:
        with dst.cursor() as cur:
            for stmt in SCHEMA:
                cur.execute(stmt)
            for m in MIGRATIONS:
                try: cur.execute(m)
                except Exception: pass
        dst.commit()
        print("OK")
    except Exception as e:
        dst.rollback()
        print(f"FAILED: {e}")
        sys.exit(1)

    # Migrate
    print("\nMigrating tables:")
    src.autocommit = True
    src_cur = src.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    total_copied = total_skipped = 0
    errors = []

    for table, pk in TABLES:
        print(f"  {table:<35}", end=" ", flush=True)
        try:
            if not table_exists(src_cur, table):
                print("(not in source — skipped)")
                continue
            copied, skipped = migrate_table(src_cur, dst, table, pk)
            total_copied  += copied
            total_skipped += skipped
            print(f"OK  {copied} rows" + (f"  ({skipped} skipped)" if skipped else ""))
        except Exception as e:
            errors.append((table, str(e)))
            print(f"ERROR: {e}")
            dst.rollback()

    print(f"\n{'='*60}")
    print(f"  DONE — {total_copied:,} rows copied, {total_skipped:,} skipped")
    if errors:
        print(f"  ERRORS on: {', '.join(t for t,_ in errors)}")
    else:
        print("  All tables migrated successfully!")
    print("="*60)

    src_cur.close()
    src.close()
    dst.close()

if __name__ == "__main__":
    main()
