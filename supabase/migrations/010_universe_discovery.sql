CREATE TABLE IF NOT EXISTS universe_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL UNIQUE,
  name TEXT,
  source TEXT,
  sector TEXT,
  market_cap FLOAT,
  score_total FLOAT,
  added_to_universe BOOLEAN DEFAULT false,
  discovered_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE universe_candidates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view universe_candidates" ON universe_candidates FOR SELECT USING (true);
