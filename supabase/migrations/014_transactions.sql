-- MarketScan 2.0 — Migration 014: Transactions
-- Transaction log for TWR calculation + audit trail

CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('buy', 'sell', 'deposit', 'withdrawal')),
  shares NUMERIC(14,4),
  price NUMERIC(12,4),
  amount NUMERIC(14,2),
  traded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_traded
  ON transactions (user_id, traded_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_user_ticker
  ON transactions (user_id, ticker);

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "transactions_own"
  ON transactions
  USING (auth.uid() = user_id);

CREATE POLICY "transactions_own_insert"
  ON transactions
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "transactions_own_update"
  ON transactions
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "transactions_own_delete"
  ON transactions
  FOR DELETE
  USING (auth.uid() = user_id);
