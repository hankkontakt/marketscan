-- MarketScan — Migration 035: User Feedback (Spec 13)
-- Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS user_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  component TEXT NOT NULL,
  context TEXT,
  rating INTEGER NOT NULL CHECK (rating IN (1, 0, -1)),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_component ON user_feedback (component);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback (created_at DESC);

ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "feedback_insert_own" ON user_feedback
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "feedback_select_own" ON user_feedback
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "feedback_admin_all" ON user_feedback
  FOR ALL USING (
    (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
  );

GRANT SELECT, INSERT, UPDATE, DELETE ON user_feedback TO authenticated;

COMMENT ON TABLE user_feedback IS 'User feedback on UI components. Migration 035. Diagnostic marker: migration_035_user_feedback.';
