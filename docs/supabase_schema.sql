-- ============================================================
-- MyPy Tutor — Supabase Schema
-- Run Part 1 first, then Part 2 in a separate query.
-- See supabase_schema_part1_tables.sql and supabase_schema_part2_rls.sql
-- Or just run this file — if it errors on RLS, run parts separately.
-- ============================================================

-- 1. Helper trigger function
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 2. PROFILES
create table if not exists profiles (
  id           text primary key,
  email        text unique not null,
  full_name    text not null default '',
  subscription text not null default 'free',
  level        text not null default 'beginner',
  xp           integer not null default 0,
  picture      text default '',
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);
drop trigger if exists trg_profiles_updated_at on profiles;
create trigger trg_profiles_updated_at
  before update on profiles
  for each row execute procedure set_updated_at();

-- 3. EMAIL ACCOUNTS
create table if not exists email_accounts (
  email         text primary key,
  learner_id    text not null default '',
  full_name     text not null default '',
  password_hash text not null default '',
  confirmed     boolean not null default true,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);
create index if not exists idx_email_learner on email_accounts (learner_id);
drop trigger if exists trg_email_accounts_updated_at on email_accounts;
create trigger trg_email_accounts_updated_at
  before update on email_accounts
  for each row execute procedure set_updated_at();

-- 4. LEARNER PROGRESS
create table if not exists learner_progress (
  learner_id          text primary key,
  level               text not null default 'beginner',
  xp                  integer not null default 0,
  tier                text not null default 'free',
  badges              jsonb not null default '[]',
  topics_seen         jsonb not null default '[]',
  topic_progress      jsonb not null default '{}',
  current_course      text,
  current_course_step integer not null default 0,
  completed_projects  jsonb not null default '[]',
  email               text not null default '',
  display_name        text not null default '',
  updated_at          timestamptz default now()
);
drop trigger if exists trg_progress_updated_at on learner_progress;
create trigger trg_progress_updated_at
  before update on learner_progress
  for each row execute procedure set_updated_at();

-- 5. CONVERSATIONS
create table if not exists conversations (
  id         text primary key default gen_random_uuid()::text,
  learner_id text not null default '',
  title      text not null default 'New Conversation',
  created_at timestamptz default now()
);
create index if not exists idx_conv_learner on conversations (learner_id);

-- 6. MESSAGES
create table if not exists messages (
  id              bigserial primary key,
  conversation_id text not null references conversations (id) on delete cascade,
  learner_id      text not null default '',
  role            text not null default 'user'
                    check (role in ('user','assistant','system')),
  content         text not null default '',
  intent          text not null default '',
  topic           text not null default '',
  created_at      timestamptz default now()
);
create index if not exists idx_msg_conv    on messages (conversation_id);
create index if not exists idx_msg_learner on messages (learner_id);

-- 7. CERTIFICATES
create table if not exists certificates (
  id           text primary key,
  learner_id   text not null default '',
  learner_name text not null default '',
  level        text not null default '',
  issued_at    timestamptz default now()
);
create index if not exists idx_cert_learner on certificates (learner_id);

-- 8. PAYMENTS
create table if not exists payments (
  id         text primary key,
  email      text not null default '',
  name       text not null default '',
  amount     numeric not null default 0,
  plan       text not null default '',
  method     text not null default 'paystack',
  status     text not null default 'confirmed',
  created_at timestamptz default now()
);

-- 9. ROW LEVEL SECURITY
alter table profiles         enable row level security;
alter table email_accounts   enable row level security;
alter table conversations    enable row level security;
alter table messages         enable row level security;
alter table learner_progress enable row level security;
alter table certificates     enable row level security;

drop policy if exists "own_profile"        on profiles;
drop policy if exists "own_email_account"  on email_accounts;
drop policy if exists "own_conversations"  on conversations;
drop policy if exists "own_messages"       on messages;
drop policy if exists "own_progress"       on learner_progress;
drop policy if exists "own_certs"          on certificates;

create policy "own_profile"       on profiles         for select using (id          = auth.uid()::text);
create policy "own_email_account" on email_accounts   for select using (learner_id  = auth.uid()::text);
create policy "own_conversations" on conversations    for select using (learner_id  = auth.uid()::text);
create policy "own_messages"      on messages         for select using (learner_id  = auth.uid()::text);
create policy "own_progress"      on learner_progress for select using (learner_id  = auth.uid()::text);
create policy "own_certs"         on certificates     for select using (learner_id  = auth.uid()::text);
