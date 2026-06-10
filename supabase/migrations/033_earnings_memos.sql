-- MarketScan — Migration 033: AI-rapportmemo (earnings_memos) — Spec 08
-- Ett strukturerat memo per bolag och rapport, genererat från RAG-chunkar.
-- Kör manuellt i Supabase SQL Editor (kräver migration 030 / company_documents).

CREATE TABLE IF NOT EXISTS earnings_memos (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker         TEXT NOT NULL,
  doc_id         UUID REFERENCES company_documents(id) ON DELETE CASCADE,
  published_date DATE,
  memo           JSONB NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, doc_id)
);

CREATE INDEX IF NOT EXISTS idx_earnings_memos_ticker
  ON earnings_memos (ticker, published_date DESC);

ALTER TABLE earnings_memos ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON earnings_memos TO anon, authenticated;
CREATE POLICY "earnings_memos_public_read" ON earnings_memos FOR SELECT USING (true);

COMMENT ON TABLE earnings_memos IS
  'AI earnings memos. Migration 033. Diagnostic marker: migration_033_earnings_memos.';
