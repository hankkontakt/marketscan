-- MarketScan Ultimate Rebuild v3 — extend the published projection.
--
-- The V3 screener (plan section 27) needs Kurs/Idag, segment and company name
-- next to Thesis/Setup/Risk/Data. Those live in legacy scan_results during the
-- migration window, so the published view joins the latest same-ticker row.
-- The view remains security_invoker=true: anon/authenticated only see rows
-- their own RLS allows, and every field still resolves to one published
-- decision snapshot.

CREATE OR REPLACE VIEW public.current_decisions_v3 WITH (security_invoker = true) AS
SELECT d.decision_id, d.decision_snapshot_id, d.listing_id, l.ticker, l.mic,
       l.currency, l.state AS tradability_state, d.decision_time,
       d.master_rank_score, d.thesis_band, d.segment_percentile, d.setup_vector,
       d.setup_state, d.risk_vector, d.risk_state, d.is_actionable, d.data_grade,
       d.coverage, d.stale_critical_count, d.street_context, d.positive_drivers,
       d.negative_drivers, d.warnings, d.model_versions, s.published_at,
       sr.name, sr.segment, sr.price, sr.change_pct
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
WHERE s.status = 'PUBLISHED';

GRANT SELECT ON public.current_decisions_v3 TO anon, authenticated;