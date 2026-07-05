-- ============================================================
-- MyPy Tutor — Supabase Migration v3
-- Run once in Supabase SQL Editor → New Query
--
-- Adds 3 tables that make email verification, password reset,
-- and referral codes survive Render ephemeral restarts:
--
--   pending_confirmations  — stores unconfirmed signup tokens
--   password_reset_tokens  — stores reset link tokens
--   referral_codes         — mirrors user-generated referral codes
--
-- All tables are safe to run multiple times (idempotent).
-- ============================================================

-- ── 1. Pending email confirmations ─────────────────────────────────────────
-- Stores signups awaiting email confirmation.
-- The backend repopulates _pending from this on startup so that
-- confirmation links work even after a Render restart wipes memory.
create table if not exists pending_confirmations (
  email         text primary key,
  learner_id    text not null default '',
  full_name     text not null default '',
  password_hash text not null default '',
  token         text not null default '',
  created_at    double precision not null default extract(epoch from now())
);

-- Auto-delete rows older than 25 hours (confirmation links expire at 24h)
-- (Supabase pg_cron or a manual periodic cleanup; the app also skips them)


-- ── 2. Password reset tokens ────────────────────────────────────────────────
-- Stores one-time password reset tokens.
-- The backend falls back to this table when SQLite is wiped on restart,
-- so reset links sent before a deploy still work.
create table if not exists password_reset_tokens (
  token      text primary key,
  email      text not null default '',
  used       boolean not null default false,
  created_at double precision not null default extract(epoch from now())
);

create index if not exists idx_prt_email on password_reset_tokens (email);


-- ── 3. Referral codes ────────────────────────────────────────────────────────
-- Mirrors user-generated referral codes from SQLite to Supabase.
-- Recovered on startup so codes still work after Render filesystem wipe.
create table if not exists referral_codes (
  code          text primary key,
  owner_id      text not null default '',
  owner_email   text not null default '',
  max_uses      integer not null default 50,
  reward_tier   text not null default 'tier1',
  uses          integer not null default 0,
  bonus_balance numeric not null default 0,
  created_at    timestamptz default now()
);

create index if not exists idx_refcodes_owner on referral_codes (owner_id);


-- ── Confirm tables exist ────────────────────────────────────────────────────
select
  table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'pending_confirmations',
    'password_reset_tokens',
    'referral_codes'
  )
order by table_name;
