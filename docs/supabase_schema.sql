-- ============================================================
-- MyPy Tutor — Supabase Schema  (fixed)
-- Run this once in: Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. HELPER: auto-update updated_at on any table
-- ─────────────────────────────────────────────────────────────
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ─────────────────────────────────────────────────────────────
-- 2. PROFILES  (one row per registered user)
-- ─────────────────────────────────────────────────────────────
create table if not exists profiles (
  id            text primary key,
  email         text unique not null,
  full_name     text not null default '',
  subscription  text not null default 'free',
  level         text not null default 'beginner',
  xp            integer not null default 0,
  picture       text default '',
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

drop trigger if exists profiles_updated_at on profiles;
create trigger profiles_updated_at
  before update on profiles
  for each row execute procedure set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- 3. EMAIL ACCOUNTS  (email/password sign-ups)
-- No FK to profiles — learner_id is set independently.
-- ─────────────────────────────────────────────────────────────
create table if not exists email_accounts (
  email         text primary key,
  learner_id    text not null,
  full_name     text not null default '',
  password_hash text not null,
  confirmed     boolean not null default true,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create index if not exists idx_email_accounts_learner
  on email_accounts (learner_id);

drop trigger if exists email_accounts_updated_at on email_accounts;
create trigger email_accounts_updated_at
  before update on email_accounts
  for each row execute procedure set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- 4. LEARNER PROGRESS
-- No FK to profiles — progress can exist before profile row.
-- ─────────────────────────────────────────────────────────────
create table if not exists learner_progress (
  learner_id           text primary key,
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

drop trigger if exists learner_progress_updated_at on learner_progress;
create trigger learner_progress_updated_at
  before update on learner_progress
  for each row execute procedure set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- 5. CONVERSATIONS
-- No FK to profiles — avoids insert-order dependency.
-- ─────────────────────────────────────────────────────────────
create table if not exists conversations (
  id          text primary key default gen_random_uuid()::text,
  learner_id  text not null,
  title       text default 'New Conversation',
  created_at  timestamptz default now()
);

create index if not exists idx_conversations_learner
  on conversations (learner_id);

-- ─────────────────────────────────────────────────────────────
-- 6. MESSAGES  (every Sir. Tega exchange)
-- FK to conversations only — conversations is already created.
-- ─────────────────────────────────────────────────────────────
create table if not exists messages (
  id               bigserial primary key,
  conversation_id  text not null
                     references conversations (id) on delete cascade,
  learner_id       text not null,
  role             text not null
                     check (role in ('user', 'assistant', 'system')),
  content          text not null,
  intent           text default '',
  topic            text default '',
  created_at       timestamptz default now()
);

create index if not exists idx_messages_conv
  on messages (conversation_id);

create index if not exists idx_messages_learner
  on messages (learner_id);

-- ─────────────────────────────────────────────────────────────
-- 7. CERTIFICATES
-- ─────────────────────────────────────────────────────────────
create table if not exists certificates (
  id            text primary key,
  learner_id    text not null,
  learner_name  text not null,
  level         text not null,
  issued_at     timestamptz default now()
);

create index if not exists idx_certs_learner
  on certificates (learner_id);

-- ─────────────────────────────────────────────────────────────
-- 8. PAYMENTS
-- ─────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────
-- 9. ROW LEVEL SECURITY
-- Service role key (used by backend) bypasses RLS entirely.
-- These policies only affect anon/authenticated client keys.
-- ─────────────────────────────────────────────────────────────
alter table profiles          enable row level security;
alter table email_accounts    enable row level security;
alter table conversations     enable row level security;
alter table messages          enable row level security;
alter table learner_progress  enable row level security;
alter table certificates      enable row level security;

-- Drop policies first so re-running this script is safe
drop policy if exists "own profile"        on profiles;
drop policy if exists "own email account"  on email_accounts;
drop policy if exists "own conversations"  on conversations;
drop policy if exists "own messages"       on messages;
drop policy if exists "own progress"       on learner_progress;
drop policy if exists "own certs"          on certificates;

create policy "own profile" on profiles
  for select using (
    id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );

create policy "own email account" on email_accounts
  for select using (
    learner_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );

create policy "own conversations" on conversations
  for select using (
    learner_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );

create policy "own messages" on messages
  for select using (
    learner_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );

create policy "own progress" on learner_progress
  for select using (
    learner_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );

create policy "own certs" on certificates
  for select using (
    learner_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
  );
