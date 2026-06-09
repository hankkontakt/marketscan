-- Migration 027: Add deduplication constraint on insider_trades
-- Required for ON CONFLICT DO NOTHING in insider_fetcher.py to work correctly.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'insider_trades_dedup_key'
  ) THEN
    ALTER TABLE insider_trades
      ADD CONSTRAINT insider_trades_dedup_key
      UNIQUE (ticker, name, trade_date, type);
  END IF;
END
$$;
