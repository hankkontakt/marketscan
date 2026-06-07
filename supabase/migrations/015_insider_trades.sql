-- MarketScan 2.0 — Migration 015: Insider trades
-- Swedish insider data (Finansinspektionen)

CREATE TABLE IF NOT EXISTS insider_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT,
  type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
  shares NUMERIC(14,2),
  amount NUMERIC(14,2),
  trade_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insider_trades_ticker
  ON insider_trades (ticker, trade_date DESC);

ALTER TABLE insider_trades ENABLE ROW LEVEL SECURITY;

-- Insider trades are public (read-only), written by pipeline via service role
GRANT SELECT ON public.insider_trades TO anon, authenticated;

CREATE POLICY "insider_trades_public_read"
  ON insider_trades
  FOR SELECT
  USING (true);
