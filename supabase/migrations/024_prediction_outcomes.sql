-- MarketScan — Migration 024: ML-prediktionsutfall (prediction_outcomes)
-- Loggar varje nattlig ML-prediktion + fyller i faktisk avkastning efter 30 dagar.
-- Kärnan i "AI lär sig av sina fel" och AI-prestanda-dashboarden.
--
-- Kör manuellt i Supabase SQL Editor.

-- ─── Tabell ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prediction_outcomes (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Prediktion
    ticker              TEXT        NOT NULL,
    predicted_at        DATE        NOT NULL,
    model_version       TEXT        NOT NULL DEFAULT 'ranker_v1',
    predicted_return    FLOAT,            -- modellens rankingpoäng (relativ)
    ml_rank             INTEGER,          -- percentil-rang 0-100
    score_total         FLOAT,            -- heuristisk total-score vid prediktionstillfället
    price_at            FLOAT,            -- stängningskurs vid prediktionstillfället (SEK/lokal)

    -- Utfall (fylls i efter 30 dagar av outcome_filler.py)
    realized_return_30d FLOAT,            -- (price_30d_later - price_at) / price_at
    price_30d           FLOAT,            -- faktisk kurs 30 dagar senare
    evaluated_at        DATE,             -- när utfallet fylldes i

    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    -- Unik per ticker+dag+modellversion (idempotent upsert)
    UNIQUE (ticker, predicted_at, model_version)
);

-- ─── Index ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_po_ticker_date
    ON prediction_outcomes (ticker, predicted_at DESC);

CREATE INDEX IF NOT EXISTS idx_po_predicted_at
    ON prediction_outcomes (predicted_at DESC);

CREATE INDEX IF NOT EXISTS idx_po_evaluated
    ON prediction_outcomes (evaluated_at)
    WHERE evaluated_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_po_pending_eval
    ON prediction_outcomes (predicted_at)
    WHERE evaluated_at IS NULL;

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE prediction_outcomes ENABLE ROW LEVEL SECURITY;

-- Admin-only write (pipeline via service_role kringgår RLS)
-- Publik läsning av aggregerade metrics OK (inga enskilda user-data)
CREATE POLICY "prediction_outcomes_public_read" ON prediction_outcomes
    FOR SELECT USING (true);

-- Ingen anonym/authenticated write — allt skrivs av service_role (pipeline + cron)

-- ─── GRANT ───────────────────────────────────────────────────────────────────
GRANT SELECT ON prediction_outcomes TO authenticated, anon;
-- INSERT/UPDATE/DELETE görs av backend service_role (kringgår grants) — ej nödvändigt att granta

-- ─── Diagnostics marker ──────────────────────────────────────────────────────
-- Lägg till i diagnostics.py USER_TABLES efter att denna migration körts
COMMENT ON TABLE prediction_outcomes IS
    'ML prediction log + realized returns. Written by pipeline (service_role). '
    'Migration 024. Diagnostic marker: migration_024_prediction_outcomes.';
