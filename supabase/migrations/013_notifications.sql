-- MarketScan 2.0 — Migration 013: Notifications
-- In-app notification center

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('price_alert', 'earnings', 'score_change', 'system', 'insider')),
  title TEXT NOT NULL,
  body TEXT,
  link TEXT,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created
  ON notifications (user_id, created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notifications_own"
  ON notifications
  USING (auth.uid() = user_id);

-- Allow UPDATE for marking as read (owner only)
CREATE POLICY "notifications_own_update"
  ON notifications
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
