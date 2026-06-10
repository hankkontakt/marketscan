-- Migration 030: Doc Intelligence (pgvector + dokumenttabeller + kvalitativa signaler)
-- Kräver pgvector extension. Körs MANUELLT i Supabase SQL Editor.
-- OBS: Skapa ivfflat-index FÖRST efter att data laddats (index kräver data).

CREATE EXTENSION IF NOT EXISTS vector;

-- Råa dokument (en rad per rapport)
CREATE TABLE IF NOT EXISTS company_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  doc_type TEXT NOT NULL,        -- 'annual_report' | 'interim_report' | 'press_release'
  title TEXT,
  published_date DATE,
  source_url TEXT,
  language TEXT DEFAULT 'sv',
  raw_text TEXT,                 -- extraherad text (PDF→text)
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, doc_type, published_date, source_url)
);

-- Chunkar + embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES company_documents(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  section TEXT,                  -- 'outlook' | 'ceo_letter' | 'risk' | 'financials' | 'other'
  chunk_index INTEGER,
  content TEXT NOT NULL,
  embedding vector(768),         -- matchar Gemini-embeddings dimension
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON document_chunks (ticker);

-- Extraherade kvalitativa signaler (en rad per bolag, senaste rapport)
CREATE TABLE IF NOT EXISTS qualitative_signals (
  ticker TEXT PRIMARY KEY,
  qualitative_score FLOAT,       -- 0-100
  outlook_direction TEXT,        -- 'positive'|'neutral'|'negative'
  hedging_density FLOAT,         -- andel osäkerhetsspråk (0-1)
  capital_intent TEXT,           -- 'investing'|'returning'|'cutting'
  tone_change FLOAT,             -- vs föregående rapport (-1..+1)
  summary TEXT,                  -- kort svensk sammanfattning (DeepSeek)
  based_on_doc_id UUID,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: company_documents/document_chunks = ingen publik läsning (upphovsrättsskydd)
ALTER TABLE company_documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE qualitative_signals   ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON qualitative_signals TO anon, authenticated;

CREATE POLICY "qual_public_read" ON qualitative_signals FOR SELECT USING (true);

-- ivfflat index skapas EFTER att data laddats (kräver data för att fungera):
-- CREATE INDEX IF NOT EXISTS idx_chunks_embedding
--   ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE company_documents IS 'Raw company documents. Migration 030. Diagnostic marker: migration_030_doc_intelligence.';
COMMENT ON TABLE document_chunks IS 'Document chunks with embeddings. Migration 030.';
COMMENT ON TABLE qualitative_signals IS 'Qualitative signals from document analysis. Migration 030.';
