-- 022_fund_holdings.sql
-- Separate table for mutual funds (fonder) imported from Avanza.
-- Funds don't have exchange tickers — identified by ISIN.

CREATE TABLE IF NOT EXISTS fund_holdings (
  id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id    UUID            NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  isin            TEXT            NOT NULL,
  name            TEXT            NOT NULL,
  shares          NUMERIC(14,4)   NOT NULL CHECK (shares > 0),
  cost_basis      NUMERIC(12,4),  -- GAV per unit in SEK (purchase price)
  current_price   NUMERIC(12,4),  -- Last known NAV per unit from positioner export
  marknadsvarde   NUMERIC(16,4),  -- Total market value at export time
  purchase_date   DATE,           -- Derived from inkopskurser CSV
  added_at        TIMESTAMPTZ     DEFAULT NOW(),
  updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

ALTER TABLE fund_holdings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fund_holdings_own" ON fund_holdings FOR ALL
  USING (
    (select auth.uid()) = (SELECT user_id FROM portfolios WHERE id = portfolio_id)
  )
  WITH CHECK (
    (select auth.uid()) = (SELECT user_id FROM portfolios WHERE id = portfolio_id)
  );

CREATE INDEX IF NOT EXISTS fund_holdings_portfolio_idx ON fund_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS fund_holdings_isin_idx ON fund_holdings(isin);
