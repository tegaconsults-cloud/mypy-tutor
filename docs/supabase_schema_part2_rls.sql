-- ============================================================
-- MyPy Tutor — Supabase Schema  PART 2: Row Level Security
-- Run this SECOND (after part 1) in a NEW query tab
-- ============================================================
-- NOTE: These policies only affect clients using the anon key.
-- The backend uses the service_role key which bypasses RLS entirely.
-- ============================================================

-- Enable RLS on each table
alter table profiles         enable row level security;
alter table email_accounts   enable row level security;
alter table conversations    enable row level security;
alter table messages         enable row level security;
alter table learner_progress enable row level security;
alter table certificates     enable row level security;

-- Drop existing policies first so this script is re-runnable
drop policy if exists "own_profile"        on profiles;
drop policy if exists "own_email_account"  on email_accounts;
drop policy if exists "own_conversations"  on conversations;
drop policy if exists "own_messages"       on messages;
drop policy if exists "own_progress"       on learner_progress;
drop policy if exists "own_certs"          on certificates;

-- Profiles: learner can read their own row
create policy "own_profile" on profiles
  for select
  using (id = auth.uid()::text);

-- Email accounts: learner can read their own row
create policy "own_email_account" on email_accounts
  for select
  using (learner_id = auth.uid()::text);

-- Conversations: learner can read their own rows
create policy "own_conversations" on conversations
  for select
  using (learner_id = auth.uid()::text);

-- Messages: learner can read their own rows
create policy "own_messages" on messages
  for select
  using (learner_id = auth.uid()::text);

-- Progress: learner can read their own row
create policy "own_progress" on learner_progress
  for select
  using (learner_id = auth.uid()::text);

-- Certificates: learner can read their own rows
create policy "own_certs" on certificates
  for select
  using (learner_id = auth.uid()::text);
