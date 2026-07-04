-- ============================================================
-- MyPy Tutor — Supabase Migration: learner_progress v2
-- Run this once in Supabase SQL Editor → New Query
--
-- Adds missing columns to learner_progress so progress,
-- topic detail, email and display name survive Render restarts.
-- Safe to run multiple times (uses IF NOT EXISTS / DO NOTHING).
-- ============================================================

-- Add topic_progress column (stores per-topic quiz scores, weak flags, etc.)
alter table learner_progress
  add column if not exists topic_progress jsonb not null default '{}';

-- Add email column (so admin panel shows correct email after restart)
alter table learner_progress
  add column if not exists email text not null default '';

-- Add display_name column (user's chosen display name)
alter table learner_progress
  add column if not exists display_name text not null default '';

-- Confirm migration
select
  column_name,
  data_type,
  column_default
from information_schema.columns
where table_name = 'learner_progress'
order by ordinal_position;
