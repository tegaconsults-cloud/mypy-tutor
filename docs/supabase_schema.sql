-- ============================================================
-- MyPy Tutor — Supabase Schema
-- Run this once in: Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- Enable UUID extension (usually already enabled)
create extension if not exists "pgcrypto";

-- ─────────────────────────────────────────────
-- PROFILES  (one row per registered user)
-- ─────────────────────────────────────────────
create table if not exists profiles (
  id            text primary key,          -- learner_id (e_<hash> or g_<sub>)
  email         text unique not null,
  full_name     text not null default '',
  subscription  text not null default 'free',  -- free|tier1|tier2|tier3
  level         text not null default 'beginner',
  xp            integer not null default 0,
  picture       text default '',
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- Auto-update updated_at
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

create trigger profiles_updated_at
  before update on profiles
  for each row execute procedure set_updated_at();

-- ─────────────────────────────────────────────
-- CONVERSATIONS
-- ─────────────────────────────────────────────
create table if not exists conversations (
  id            text primary key default gen_random_uuid()::text,
  learner_id    text not null references profiles(id) on delete cascade,
  title         text default 'New Conversation',
  created_at    timestamptz default now()
);

create index if not exists idx_conversations_learner on conversations(learner_id);

-- ─────────────────────────────────────────────
-- MESSAGES  (every Sir. Tega exchange)
-- ─────────────────────────────────────────────
create table if not exists messages (
  id               bigserial primary key,
  conversation_id  text not null references conversations(id) on delete cascade,
  learner_id       text not null,
  role             text not null check (role in ('user','assistant','system')),
  content          text not null,
  intent           text default '',
  topic            text default '',
  created_at       timestamptz default now()
);

create index if not exists idx_messages_conv    on messages(conversation_id);
create index if not exists idx_messages_learner on messages(learner_id);

-- ─────────────────────────────────────────────
-- LEARNER PROGRESS
-- ─────────────────────────────────────────────
create table if not exists learner_progress (
  learner_id           text primary key references profiles(id) on delete cascade,
  level                text default 'beginner',
  xp                   integer default 0,
  tier                 text default 'free',
  badges               jsonb default '[]',
  topics_seen          jsonb default '[]',
  current_course       text,
  current_course_step  integer default 0,
  completed_projects   jsonb default '[]',
  updated_at           timestamptz default now()
);

-- ─────────────────────────────────────────────
-- CERTIFICATES
-- ─────────────────────────────────────────────
create table if not exists certificates (
  id            text primary key,
  learner_id    text not null,
  learner_name  text not null,
  level         text not null,
  issued_at     timestamptz default now()
);

create index if not exists idx_certs_learner on certificates(learner_id);

-- ─────────────────────────────────────────────
-- PAYMENTS
-- ─────────────────────────────────────────────
create table if not exists payments (
  id         text primary key,
  email      text not null,
  name       text not null,
  amount     numeric not null,
  plan       text not null,
  method     text default 'paystack',
  status     text default 'confirmed',
  created_at timestamptz default now()
);

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Learners can only read their own data.
-- Service role key bypasses RLS (backend always uses service role).
-- ─────────────────────────────────────────────
alter table profiles          enable row level security;
alter table conversations     enable row level security;
alter table messages          enable row level security;
alter table learner_progress  enable row level security;
alter table certificates      enable row level security;

-- Profiles: read own
create policy "own profile" on profiles
  for select using (id = current_setting('request.jwt.claims', true)::jsonb->>'sub');

-- Conversations: read own
create policy "own conversations" on conversations
  for select using (learner_id = current_setting('request.jwt.claims', true)::jsonb->>'sub');

-- Messages: read own
create policy "own messages" on messages
  for select using (learner_id = current_setting('request.jwt.claims', true)::jsonb->>'sub');

-- NOTE: All INSERTs/UPDATEs come from the backend using service_role key,
-- which bypasses RLS entirely. No anon insert policies needed.
