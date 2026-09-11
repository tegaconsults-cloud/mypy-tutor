#!/usr/bin/env python3
"""
fix_schema.py — Align Supabase schema with app expectations.

Run once: python fix_schema.py

What this does:
1. Creates all missing tables (learner_profiles, activity_log, etc.)
2. Adds missing columns to existing tables (payments.user_email, etc.)
3. Migrates existing data to new column names where needed
4. Creates all indexes
"""
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()
url = os.getenv("DATABASE_URL","").strip()
if not url:
    print("ERROR: DATABASE_URL not set"); exit(1)
if "sslmode" not in url:
    url += "?sslmode=require"

print("Connecting to Supabase...")
conn = psycopg2.connect(url, connect_timeout=15)
conn.autocommit = False
cur = conn.cursor()
print("Connected.\n")

def run(sql, desc=""):
    try:
        cur.execute(sql)
        if desc: print(f"  ✓ {desc}")
    except Exception as e:
        print(f"  ⚠ {desc or sql[:60]}: {e}")
        conn.rollback()

# ── Step 1: Create missing tables ──────────────────────────────────────────
print("Step 1: Creating missing tables...")

tables = [
    ("learner_profiles", """CREATE TABLE IF NOT EXISTS learner_profiles (
        learner_id TEXT PRIMARY KEY, tier TEXT DEFAULT 'free',
        level TEXT DEFAULT 'beginner', xp INTEGER DEFAULT 0,
        badges TEXT DEFAULT '[]', topics_seen TEXT DEFAULT '[]',
        topic_progress TEXT DEFAULT '{}', current_course TEXT,
        course_step INTEGER DEFAULT 0, completed_projects TEXT DEFAULT '[]',
        daily_prompts_used INTEGER DEFAULT 0, last_prompt_date TEXT DEFAULT '',
        email TEXT DEFAULT '', display_name TEXT DEFAULT '',
        prompt_plan TEXT DEFAULT '',
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("activity_log", """CREATE TABLE IF NOT EXISTS activity_log (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        action TEXT NOT NULL, detail TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("prompt_history", """CREATE TABLE IF NOT EXISTS prompt_history (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        role TEXT NOT NULL, content TEXT NOT NULL,
        intent TEXT DEFAULT '', topic TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("quiz_attempts", """CREATE TABLE IF NOT EXISTS quiz_attempts (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        topic TEXT NOT NULL, question TEXT NOT NULL,
        answer TEXT NOT NULL, correct INTEGER DEFAULT 0, score INTEGER DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("assignments", """CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
        title TEXT NOT NULL, description TEXT NOT NULL,
        course TEXT DEFAULT '', status TEXT DEFAULT 'pending',
        submission TEXT DEFAULT '', feedback TEXT DEFAULT '',
        score INTEGER DEFAULT 0, submitted_at DOUBLE PRECISION,
        reviewed_at DOUBLE PRECISION,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("coupons", """CREATE TABLE IF NOT EXISTS coupons (
        code TEXT PRIMARY KEY, discount_pct INTEGER NOT NULL,
        discount_flat DOUBLE PRECISION DEFAULT 0, plan TEXT DEFAULT 'any',
        max_uses INTEGER DEFAULT 100, uses INTEGER DEFAULT 0,
        expires_at DOUBLE PRECISION DEFAULT 0, active INTEGER DEFAULT 1,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("coupon_uses", """CREATE TABLE IF NOT EXISTS coupon_uses (
        id SERIAL PRIMARY KEY, code TEXT NOT NULL,
        learner_id TEXT NOT NULL, email TEXT NOT NULL,
        amount_saved DOUBLE PRECISION DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("referrals", """CREATE TABLE IF NOT EXISTS referrals (
        code TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
        owner_email TEXT NOT NULL, uses INTEGER DEFAULT 0,
        max_uses INTEGER DEFAULT 50, reward_tier TEXT DEFAULT 'tier1',
        bonus_balance DOUBLE PRECISION DEFAULT 0,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("referral_uses", """CREATE TABLE IF NOT EXISTS referral_uses (
        id SERIAL PRIMARY KEY, code TEXT NOT NULL,
        used_by_email TEXT NOT NULL, used_by_id TEXT NOT NULL,
        discount_pct INTEGER DEFAULT 20, referrer_bonus DOUBLE PRECISION DEFAULT 0,
        referee_discount DOUBLE PRECISION DEFAULT 0,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("referral_withdrawals", """CREATE TABLE IF NOT EXISTS referral_withdrawals (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        email TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
        bank_name TEXT NOT NULL, account_name TEXT NOT NULL,
        account_num TEXT NOT NULL, status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("course_purchases", """CREATE TABLE IF NOT EXISTS course_purchases (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        course_name TEXT NOT NULL, amount_ngn DOUBLE PRECISION DEFAULT 0,
        payment_ref TEXT DEFAULT '',
        purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        UNIQUE(learner_id, course_name))"""),
    ("bank_transfer_proofs", """CREATE TABLE IF NOT EXISTS bank_transfer_proofs (
        id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, email TEXT NOT NULL,
        plan TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL,
        reference TEXT DEFAULT '', proof_b64 TEXT DEFAULT '',
        proof_url TEXT DEFAULT '', notes TEXT DEFAULT '',
        status TEXT DEFAULT 'pending', admin_notes TEXT DEFAULT '',
        submitted_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        reviewed_at DOUBLE PRECISION)"""),
    ("user_profiles", """CREATE TABLE IF NOT EXISTS user_profiles (
        learner_id TEXT PRIMARY KEY, display_name TEXT DEFAULT '',
        bio TEXT DEFAULT '', location TEXT DEFAULT '',
        website TEXT DEFAULT '', photo_url TEXT DEFAULT '',
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("feedback_ratings", """CREATE TABLE IF NOT EXISTS feedback_ratings (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        rating TEXT NOT NULL, intent TEXT DEFAULT '',
        topic TEXT DEFAULT '', comment TEXT DEFAULT '',
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("feedback_surveys", """CREATE TABLE IF NOT EXISTS feedback_surveys (
        id SERIAL PRIMARY KEY, learner_id TEXT NOT NULL,
        overall INTEGER NOT NULL, clarity INTEGER NOT NULL,
        helpfulness INTEGER NOT NULL, suggestion TEXT DEFAULT '',
        would_recommend INTEGER DEFAULT 1,
        ts DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("email_automation", """CREATE TABLE IF NOT EXISTS email_automation (
        learner_id TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        last_reengagement_at DOUBLE PRECISION DEFAULT 0,
        last_course_reminder_at DOUBLE PRECISION DEFAULT 0,
        last_assignment_reminder_at DOUBLE PRECISION DEFAULT 0,
        last_weekend_msg_at DOUBLE PRECISION DEFAULT 0,
        last_new_month_msg_at DOUBLE PRECISION DEFAULT 0,
        opted_out INTEGER DEFAULT 0,
        updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("session_revocations", """CREATE TABLE IF NOT EXISTS session_revocations (
        learner_id TEXT PRIMARY KEY, revoked_at DOUBLE PRECISION NOT NULL)"""),
    ("processed_webhooks", """CREATE TABLE IF NOT EXISTS processed_webhooks (
        reference TEXT PRIMARY KEY,
        processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("enquiries", """CREATE TABLE IF NOT EXISTS enquiries (
        id SERIAL PRIMARY KEY, learner_id TEXT DEFAULT '',
        name TEXT NOT NULL, email TEXT NOT NULL, category TEXT NOT NULL,
        subject TEXT NOT NULL, message TEXT NOT NULL, status TEXT DEFAULT 'open',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("team_members", """CREATE TABLE IF NOT EXISTS team_members (
        email TEXT PRIMARY KEY, name TEXT NOT NULL,
        role TEXT DEFAULT 'team', status TEXT DEFAULT 'invited',
        invited_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("tasks", """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL,
        description TEXT DEFAULT '', assigned_to TEXT NOT NULL,
        priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'open',
        due_date TEXT DEFAULT '',
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("announcements", """CREATE TABLE IF NOT EXISTS announcements (
        id SERIAL PRIMARY KEY, subject TEXT NOT NULL,
        target TEXT NOT NULL, sent_to INTEGER DEFAULT 0,
        sent_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("daily_prompt_counts", """CREATE TABLE IF NOT EXISTS daily_prompt_counts (
        key TEXT NOT NULL, date_str TEXT NOT NULL,
        count INTEGER DEFAULT 0, PRIMARY KEY(key, date_str))"""),
    ("password_resets", """CREATE TABLE IF NOT EXISTS password_resets (
        token TEXT PRIMARY KEY, email TEXT NOT NULL,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        used INTEGER DEFAULT 0)"""),
    ("access_codes", """CREATE TABLE IF NOT EXISTS access_codes (
        code TEXT PRIMARY KEY, tier TEXT NOT NULL,
        created_by TEXT DEFAULT 'admin', sent_to_email TEXT DEFAULT '',
        used_by_email TEXT DEFAULT '', used_by_id TEXT DEFAULT '',
        used INTEGER DEFAULT 0, expires_at DOUBLE PRECISION DEFAULT 0,
        discount_pct INTEGER DEFAULT 0,
        created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()))"""),
    ("invoices", """CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY, payment_id TEXT NOT NULL,
        learner_id TEXT NOT NULL, email TEXT NOT NULL,
        name TEXT NOT NULL, plan TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL, currency TEXT DEFAULT 'NGN',
        issued_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
        due_date TEXT DEFAULT '')"""),
]

for tname, sql in tables:
    run(sql, f"CREATE TABLE IF NOT EXISTS {tname}")

conn.commit()

# ── Step 2: Column migrations on EXISTING tables ───────────────────────────
print("\nStep 2: Adding missing columns to existing tables...")

col_migrations = [
    # payments: rename/add columns to match app schema
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT ''",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS user_name  TEXT DEFAULT ''",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency   TEXT DEFAULT 'NGN'",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS notes      TEXT DEFAULT ''",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS method     TEXT DEFAULT 'bank'",
    # Migrate existing data: copy email->user_email, name->user_name
    "UPDATE payments SET user_email=email WHERE user_email='' AND email IS NOT NULL",
    "UPDATE payments SET user_name=name   WHERE user_name=''  AND name  IS NOT NULL",
    # certificates
    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS programme TEXT DEFAULT ''",
    # email_accounts: add 'name' alias column (app uses 'name', Supabase uses 'full_name')
    "ALTER TABLE email_accounts ADD COLUMN IF NOT EXISTS name TEXT DEFAULT ''",
    "UPDATE email_accounts SET name=full_name WHERE name='' AND full_name IS NOT NULL",
    # access_codes
    "ALTER TABLE access_codes ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0",
    # learner_profiles: add prompt_plan if missing
    "ALTER TABLE learner_profiles ADD COLUMN IF NOT EXISTS prompt_plan TEXT DEFAULT ''",
]

for sql in col_migrations:
    run(sql, sql[:70])

conn.commit()

# ── Step 3: Create indexes ─────────────────────────────────────────────────
print("\nStep 3: Creating indexes...")

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_learner_profiles_tier ON learner_profiles (tier)",
    "CREATE INDEX IF NOT EXISTS idx_email_accounts_learner ON email_accounts (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_email_accounts_email ON email_accounts (email)",
    "CREATE INDEX IF NOT EXISTS idx_email_accounts_confirmed ON email_accounts (confirmed)",
    "CREATE INDEX IF NOT EXISTS idx_payments_email ON payments (user_email)",
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status)",
    "CREATE INDEX IF NOT EXISTS idx_payments_created ON payments (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_certificates_learner ON certificates (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_history_learner ON prompt_history (learner_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_activity_log_learner ON activity_log (learner_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_assignments_learner ON assignments (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_learner ON invoices (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_course_purchases_learner ON course_purchases (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_ratings_learner ON feedback_ratings (learner_id, ts)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_surveys_learner ON feedback_surveys (learner_id, ts)",
    "CREATE INDEX IF NOT EXISTS idx_btp_learner ON bank_transfer_proofs (learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_btp_status ON bank_transfer_proofs (status)",
    "CREATE INDEX IF NOT EXISTS idx_email_automation_opted ON email_automation (opted_out)",
    "CREATE INDEX IF NOT EXISTS idx_daily_prompts_key ON daily_prompt_counts (key, date_str)",
    "CREATE INDEX IF NOT EXISTS idx_coupons_active ON coupons (active, plan)",
    "CREATE INDEX IF NOT EXISTS idx_referral_uses_code ON referral_uses (code)",
]

for sql in indexes:
    run(sql, sql[22:80])

conn.commit()

# ── Step 4: Verify ─────────────────────────────────────────────────────────
print("\nStep 4: Verification...")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables_now = [r[0] for r in cur.fetchall()]
print(f"  Tables: {len(tables_now)} — {tables_now}")

for t in ["payments","learner_profiles","email_accounts","certificates"]:
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    n = cur.fetchone()[0]
    print(f"  {t}: {n} rows | cols: {cols}")

conn.close()
print("\n✅ Schema fix complete. Redeploy Render to pick up changes.")
