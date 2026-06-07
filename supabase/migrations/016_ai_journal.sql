-- MarketScan 2.0 — Migration 016: AI journal
-- Tracks analysis committee verdicts over time for transparency

CREATE TABLE IF NOT EXISTS ai_journal (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('STARK', 'BRA', 'AVVAKTA', 'EJ_AKTUELLT')),
  confidence INTEGER CHECK (confidence BETWEEN 0 AND 100),
  summary TEXT,
  score_at_time NUMERIC(5,2),
  price_at_time NUMERIC(12,4),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_journal_ticker
  ON ai_journal (ticker, created_at DESC);

ALTER TABLE ai_journal ENABLE ROW LEVEL SECURITY;

-- AI journal is public (read-only), written by API via service role
GRANT SELECT ON public.ai_journal TO anon, authenticated;

CREATE POLICY "ai_journal_public_read"
  ON ai_journal
  FOR SELECT
  USING (true);
