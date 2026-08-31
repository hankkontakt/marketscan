-- MarketScan — Migration 075: Fundamentals & Forensics (ROND 11)
-- Lägger till djupa fundamenta och forensiska varningssignaler:
--   1. Fritt kassaflöde (fcf_ttm, fcf_yield)
--   2. Operativt kassaflöde (ocf_ttm)
--   3. Nettoskuld (net_debt, total_debt, cash_and_equivalents)
--   4. Forensiska mått (sloan_accruals, cash_runway_months, dilution_rate_pct)
--   5. AI-kvalitativa signaler (ai_tone_score, forensic_flags, ai_red_flags)

ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS fcf_ttm                NUMERIC(18,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS ocf_ttm                NUMERIC(18,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS net_debt               NUMERIC(18,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS total_debt             NUMERIC(18,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS cash_and_equivalents   NUMERIC(18,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS fcf_yield              NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS sloan_accrual_ratio    NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS cash_runway_months     NUMERIC(8,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS dilution_rate_pct      NUMERIC(8,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS gross_margin_latest    NUMERIC(10,6);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS gross_margin_trend_pct NUMERIC(8,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS forensic_flags         TEXT[];
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS ai_tone_score          NUMERIC(5,2);
ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS ai_red_flags           TEXT[];

COMMENT ON COLUMN scan_results.sloan_accrual_ratio IS
    'Sloan Accrual Anomaly: (Net Income - Operating Cash Flow) / Total Assets.
    Positivt > 0.10 indikerar att bokförd vinst inte backas upp av kassaflöde.
    Migration 075.';

COMMENT ON COLUMN scan_results.cash_runway_months IS
    'Månader av likviditet kvar baserat på kvartalsvis fritt kassaflödes-burn.
    Värden < 6.0 indikerar akut emissionsrisk. Migration 075.';
