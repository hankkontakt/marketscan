CREATE TABLE IF NOT EXISTS ai_cache (
  cache_key TEXT PRIMARY KEY,
  response_data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_cache_created_at ON ai_cache (created_at);

-- Cleanup function: remove cache entries older than 7 days
-- Called periodically or on each cache write
CREATE OR REPLACE FUNCTION clean_ai_cache()
RETURNS void AS $$
BEGIN
  DELETE FROM ai_cache WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
