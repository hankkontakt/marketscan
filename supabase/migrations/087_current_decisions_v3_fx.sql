-- MarketScan Ultimate Rebuild v3 — FX context in the published projection.
--
-- Every published decision carries the dated, sourced SEK rate of its listing
-- currency, so any consumer can normalize without its own lookup. Missing
-- rate (unknown currency / no dated rate) surfaces as NULL — explicit, never
-- silently approximated (Phase 4 contract).

CREATE OR REPLACE VIEW public.current_decisions_v3 WITH (security_invoker = true) AS
SELECT d.decision_id, d.decision_snapshot_id, d.listing_id, l.ticker, l.mic,
       l.currency, l.state AS tradability_state, d.decision_time,
       d.master_rank_score, d.thesis_band, d.segment_percentile, d.setup_vector,
       d.setup_state, d.risk_vector, d.risk_state, d.is_actionable, d.data_grade,
       d.coverage, d.stale_critical_count, d.street_context, d.positive_drivers,
       d.negative_drivers, d.warnings, d.model_versions, s.published_at,
       sr.name, sr.segment, sr.price, sr.change_pct,
       fx.rate AS fx_rate_sek, fx.rate_date AS fx_rate_date, fx.source AS fx_source
FROM public.decision_manifests d
JOIN public.listings l ON l.listing_id = d.listing_id
JOIN public.decision_snapshots s ON s.decision_snapshot_id = d.decision_snapshot_id
JOIN public.publication_state p ON p.current_decision_snapshot_id = d.decision_snapshot_id
LEFT JOIN LATERAL (
    SELECT sr2.name, sr2.segment, sr2.price, sr2.change_pct
    FROM public.scan_results sr2
    WHERE upper(sr2.ticker) = upper(l.ticker)
    ORDER BY sr2.scan_date DESC, sr2.updated_at DESC NULLS LAST
    LIMIT 1
) sr ON true
LEFT JOIN LATERAL (
    SELECT fx2.rate, fx2.rate_date, fx2.source
    FROM public.fx_rates fx2
    WHERE fx2.base_currency = 'SEK' AND fx2.quote_currency = l.currency
      AND fx2.rate_date <= s.published_at::date
    ORDER BY fx2.rate_date DESC
    LIMIT 1
) fx ON true
WHERE s.status = 'PUBLISHED';

GRANT SELECT ON public.current_decisions_v3 TO anon, authenticated;