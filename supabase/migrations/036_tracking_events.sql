-- Tracking events (replaces Umami, self-hosted in Supabase)
CREATE TABLE IF NOT EXISTS tracking_events (
  id BIGSERIAL PRIMARY KEY,
  event_name TEXT NOT NULL,
  props JSONB DEFAULT '{}',
  url TEXT,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracking_events_name ON tracking_events (event_name);
CREATE INDEX IF NOT EXISTS idx_tracking_events_created ON tracking_events (created_at DESC);

ALTER TABLE tracking_events ENABLE ROW LEVEL SECURITY;

-- Anyone authenticated can insert
CREATE POLICY "tracking_insert" ON tracking_events
  FOR INSERT WITH CHECK (true);

-- Only admin can read
CREATE POLICY "tracking_admin_read" ON tracking_events
  FOR SELECT USING (
    (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
  );

GRANT INSERT ON tracking_events TO anon, authenticated;
GRANT SELECT ON tracking_events TO authenticated;

COMMENT ON TABLE tracking_events IS 'Analytics tracking events. Migration 036. Diagnostic marker: migration_036_tracking_events.';
