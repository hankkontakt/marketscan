CREATE TABLE IF NOT EXISTS portfolio_optimizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  method TEXT NOT NULL,
  weights JSONB NOT NULL,
  expected_return FLOAT,
  expected_volatility FLOAT,
  sharpe FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE portfolio_optimizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own portfolio_optimizations" ON portfolio_optimizations FOR ALL USING (auth.uid() = user_id);
