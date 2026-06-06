CREATE TABLE IF NOT EXISTS paper_portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name TEXT DEFAULT 'Pappersportfölj',
  cash FLOAT DEFAULT 100000,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

ALTER TABLE paper_portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own paper_portfolios" ON paper_portfolios FOR ALL USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS paper_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID REFERENCES paper_portfolios(id) ON DELETE CASCADE NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  shares FLOAT NOT NULL,
  price FLOAT NOT NULL,
  total FLOAT NOT NULL,
  traded_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE paper_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own paper_trades" ON paper_trades FOR ALL USING (
  portfolio_id IN (SELECT id FROM paper_portfolios WHERE user_id = auth.uid())
);

CREATE TABLE IF NOT EXISTS paper_positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID REFERENCES paper_portfolios(id) ON DELETE CASCADE NOT NULL,
  ticker TEXT NOT NULL,
  shares FLOAT NOT NULL,
  avg_cost FLOAT NOT NULL,
  UNIQUE(portfolio_id, ticker)
);

ALTER TABLE paper_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own paper_positions" ON paper_positions FOR ALL USING (
  portfolio_id IN (SELECT id FROM paper_portfolios WHERE user_id = auth.uid())
);
