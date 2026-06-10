-- MarketScan — Migration 034: Notisinställningar + worker-state (Spec 09)
-- Per-user-inställningar för watchlist-notiser + diff-state för insider/MEWS-flash.
-- Kör manuellt i Supabase SQL Editor.

-- ─── notification_prefs ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notification_prefs (
  user_id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  on_new_stark         BOOLEAN DEFAULT TRUE,
  on_score_move        BOOLEAN DEFAULT TRUE,
  on_insider_cluster   BOOLEAN DEFAULT TRUE,
  on_mews_flag         BOOLEAN DEFAULT TRUE,
  on_earnings_memo     BOOLEAN DEFAULT TRUE,
  score_move_threshold INTEGER DEFAULT 15,
  email_enabled        BOOLEAN DEFAULT FALSE,
  updated_at           TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE notification_prefs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_prefs_rw" ON notification_prefs
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
GRANT SELECT, INSERT, UPDATE ON notification_prefs TO authenticated;
COMMENT ON TABLE notification_prefs IS
  'Per-user notification prefs. Migration 034. Diagnostic marker: migration_034_notification_prefs.';

-- ─── worker_state (diff-state för flash-notiser, skrivs av service_role) ──────
CREATE TABLE IF NOT EXISTS worker_state (
  key        TEXT PRIMARY KEY,
  value      JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE worker_state ENABLE ROW LEVEL SECURITY;
-- Ingen publik åtkomst — endast service_role (kringgår RLS) läser/skriver.
COMMENT ON TABLE worker_state IS
  'Internal worker diff-state. Migration 034. Diagnostic marker: migration_034_worker_state.';
