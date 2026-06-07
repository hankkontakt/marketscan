-- Allow users to request tickers not yet in scan_results
-- These are picked up by the pipeline on next run and added to the universe.
CREATE TABLE IF NOT EXISTS user_ticker_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  name TEXT,
  source TEXT DEFAULT 'manual',
  added_to_universe BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (ticker)
);

ALTER TABLE user_ticker_requests ENABLE ROW LEVEL SECURITY;

-- Users can see their own requests
CREATE POLICY "Users can view own requests" ON user_ticker_requests
  FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own requests
CREATE POLICY "Users can insert own requests" ON user_ticker_requests
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Service role can update (mark as added_to_universe)
CREATE POLICY "Service role can update user_ticker_requests" ON user_ticker_requests
  FOR UPDATE USING (auth.role() = 'service_role');
