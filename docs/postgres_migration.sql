-- =============================================================================
-- MyPy Tutor — PostgreSQL Migration Script
-- Run this once in your Render PostgreSQL or Supabase SQL editor.
-- Safe to run multiple times (IF NOT EXISTS / ON CONFLICT DO NOTHING).
-- =============================================================================

-- 1. Core tables
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
);

CREATE TABLE IF NOT EXISTS email_accounts (
    email           TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    learner_id      TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    token           TEXT,
    confirmed       INTEGER DEFAULT 0,
    created_at      DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          SERIAL PRIMARY KEY,
    learner_id  TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT DEFAULT '',
    ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS certificates (
    cert_id         TEXT PRIMARY KEY,
    learner_id      TEXT NOT NULL,
    learner_name    TEXT NOT NULL,
    level           TEXT NOT NULL,
    issued_at       DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

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
);

CREATE TABLE IF NOT EXISTS team_members (
    email       TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT DEFAULT 'team',
    status      TEXT DEFAULT 'invited',
    invited_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    assigned_to TEXT NOT NULL,
    priority    TEXT DEFAULT 'medium',
    status      TEXT DEFAULT 'open',
    due_date    TEXT DEFAULT '',
    created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS announcements (
    id       SERIAL PRIMARY KEY,
    subject  TEXT NOT NULL,
    target   TEXT NOT NULL,
    sent_to  INTEGER DEFAULT 0,
    sent_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS password_resets (
    token       TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    created_at  DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    used        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_revocations (
    learner_id TEXT PRIMARY KEY,
    revoked_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_history (
    id          SERIAL PRIMARY KEY,
    learner_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    intent      TEXT DEFAULT '',
    topic       TEXT DEFAULT '',
    ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id          SERIAL PRIMARY KEY,
    learner_id  TEXT NOT NULL,
    topic       TEXT NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    correct     INTEGER DEFAULT 0,
    score       INTEGER DEFAULT 0,
    ts          DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

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
);

CREATE TABLE IF NOT EXISTS referrals (
    code            TEXT PRIMARY KEY,
    owner_id        TEXT NOT NULL,
    owner_email     TEXT NOT NULL,
    uses            INTEGER DEFAULT 0,
    max_uses        INTEGER DEFAULT 50,
    reward_tier     TEXT DEFAULT 'tier1',
    bonus_balance   DOUBLE PRECISION DEFAULT 0,
    created_at      DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS referral_uses (
    id               SERIAL PRIMARY KEY,
    code             TEXT NOT NULL,
    used_by_email    TEXT NOT NULL,
    used_by_id       TEXT NOT NULL,
    discount_pct     INTEGER DEFAULT 20,
    referrer_bonus   DOUBLE PRECISION DEFAULT 0,
    referee_discount DOUBLE PRECISION DEFAULT 0,
    ts               DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

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
);

CREATE TABLE IF NOT EXISTS coupon_uses (
    id           SERIAL PRIMARY KEY,
    code         TEXT NOT NULL,
    learner_id   TEXT NOT NULL,
    email        TEXT NOT NULL,
    amount_saved DOUBLE PRECISION DEFAULT 0,
    ts           DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

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
);

CREATE TABLE IF NOT EXISTS access_codes (
    code          TEXT PRIMARY KEY,
    tier          TEXT NOT NULL,
    created_by    TEXT DEFAULT 'admin',
    sent_to_email TEXT DEFAULT '',
    used_by_email TEXT DEFAULT '',
    used_by_id    TEXT DEFAULT '',
    used          INTEGER DEFAULT 0,
    expires_at    DOUBLE PRECISION DEFAULT 0,
    created_at    DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS user_profiles (
    learner_id   TEXT PRIMARY KEY,
    display_name TEXT DEFAULT '',
    bio          TEXT DEFAULT '',
    location     TEXT DEFAULT '',
    website      TEXT DEFAULT '',
    photo_url    TEXT DEFAULT '',
    updated_at   DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS course_purchases (
    id           SERIAL PRIMARY KEY,
    learner_id   TEXT NOT NULL,
    course_name  TEXT NOT NULL,
    amount_ngn   DOUBLE PRECISION DEFAULT 0,
    payment_ref  TEXT DEFAULT '',
    purchased_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    UNIQUE (learner_id, course_name)
);

CREATE TABLE IF NOT EXISTS daily_prompt_counts (
    key      TEXT NOT NULL,
    date_str TEXT NOT NULL,
    count    INTEGER DEFAULT 0,
    PRIMARY KEY (key, date_str)
);

CREATE TABLE IF NOT EXISTS feedback_ratings (
    id         SERIAL PRIMARY KEY,
    learner_id TEXT NOT NULL,
    rating     TEXT NOT NULL,
    intent     TEXT DEFAULT '',
    topic      TEXT DEFAULT '',
    comment    TEXT DEFAULT '',
    ts         DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS feedback_surveys (
    id              SERIAL PRIMARY KEY,
    learner_id      TEXT NOT NULL,
    overall         INTEGER NOT NULL,
    clarity         INTEGER NOT NULL,
    helpfulness     INTEGER NOT NULL,
    suggestion      TEXT DEFAULT '',
    would_recommend INTEGER DEFAULT 1,
    ts              DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

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
);

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
);

CREATE TABLE IF NOT EXISTS processed_webhooks (
    reference    TEXT PRIMARY KEY,
    processed_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_prompt_history_learner    ON prompt_history (learner_id, id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_learner     ON quiz_attempts (learner_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_learner      ON activity_log (learner_id, id);
CREATE INDEX IF NOT EXISTS idx_assignments_learner       ON assignments (learner_id);
CREATE INDEX IF NOT EXISTS idx_invoices_learner          ON invoices (learner_id);
CREATE INDEX IF NOT EXISTS idx_referral_uses_code        ON referral_uses (code);
CREATE INDEX IF NOT EXISTS idx_coupons_active            ON coupons (active, plan);
CREATE INDEX IF NOT EXISTS idx_payments_email            ON payments (user_email);
CREATE INDEX IF NOT EXISTS idx_access_codes_email        ON access_codes (sent_to_email);
CREATE INDEX IF NOT EXISTS idx_course_purchases_learner  ON course_purchases (learner_id);
CREATE INDEX IF NOT EXISTS idx_daily_prompts_key         ON daily_prompt_counts (key, date_str);
CREATE INDEX IF NOT EXISTS idx_feedback_ratings_learner  ON feedback_ratings (learner_id, ts);
CREATE INDEX IF NOT EXISTS idx_feedback_surveys_learner  ON feedback_surveys (learner_id, ts);
CREATE INDEX IF NOT EXISTS idx_enquiries_status          ON enquiries (status);
