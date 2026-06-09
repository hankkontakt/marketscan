-- Migration 025: Utöka pipeline_runs run_type CHECK-constraint
--
-- Den ursprungliga constraintens tillät bara morning/evening/weekly/manual.
-- Pipeline stöder nu även smallcap, targeted, refresh_missing, retry_rate_limited.
--
-- Kör i Supabase SQL Editor (Settings → SQL Editor → New query).

ALTER TABLE pipeline_runs
  DROP CONSTRAINT IF EXISTS pipeline_runs_run_type_check;

ALTER TABLE pipeline_runs
  ADD CONSTRAINT pipeline_runs_run_type_check
  CHECK (run_type IN (
    'morning',
    'evening',
    'weekly',
    'manual',
    'smallcap',
    'targeted',
    'refresh_missing',
    'retry_rate_limited'
  ));
