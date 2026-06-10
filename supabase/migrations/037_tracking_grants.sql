-- Fix tracking_events grants: service_role behöver full access
-- (tracking endpoint använder get_supabase_admin för att undvika
--  supabase-py RLS edge case med anon key)
GRANT ALL ON tracking_events TO service_role;
GRANT USAGE, SELECT ON SEQUENCE tracking_events_id_seq TO service_role;

-- Uppdatera RLS-policyn: explicit TO anon, authenticated
DROP POLICY IF EXISTS tracking_insert ON tracking_events;
CREATE POLICY tracking_insert ON tracking_events
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);

COMMENT ON TABLE tracking_events IS 'Analytics tracking events. Migration 037. Diagnostic marker: migration_037_tracking_grants.';
