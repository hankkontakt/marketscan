-- MarketScan Ultimate Rebuild v3 — Phase 9: decision transitions, alert
-- rule types, and portfolio↔listing linkage.
--
-- Append-only, fully idempotent (IF NOT EXISTS / DO-guards / ON CONFLICT).
-- The worker writes decision_transitions; anon/authenticated read them.
-- holdings.listing_id is backfilled only against ACTIVE listings — CPRX is
-- MERGED and therefore never matches (CPRX invariant: no rows are created
-- for it).

-- ─── Decision transitions (diff layer) ───────────────────────────────────────
-- One row per observed state change between published decision snapshots.
-- snapshot_from NULL = the listing is new to the published universe.
CREATE TABLE IF NOT EXISTS public.decision_transitions (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_from   uuid REFERENCES public.decision_snapshots(decision_snapshot_id),
    snapshot_to     uuid NOT NULL REFERENCES public.decision_snapshots(decision_snapshot_id),
    listing_id      uuid NOT NULL REFERENCES public.listings(listing_id),
    ticker          text NOT NULL,
    decision_id     uuid REFERENCES public.decision_manifests(decision_id),
    transition_type text NOT NULL CHECK (transition_type IN ('thesis','setup','risk','data_grade','tradability','rank')),
    from_state      text,
    to_state        text NOT NULL,
    reason_code     text NOT NULL,
    rank_delta      numeric,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS decision_transitions_listing_created_idx
    ON public.decision_transitions (listing_id, created_at DESC);

ALTER TABLE public.decision_transitions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "decision_transitions_service_all" ON public.decision_transitions;
CREATE POLICY "decision_transitions_service_all" ON public.decision_transitions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "decision_transitions_public_read" ON public.decision_transitions;
CREATE POLICY "decision_transitions_public_read" ON public.decision_transitions
    FOR SELECT TO anon, authenticated USING (true);

GRANT SELECT ON public.decision_transitions TO anon, authenticated;
GRANT ALL ON public.decision_transitions TO service_role;

-- ─── alert_rules: extend rule_type CHECK with transition types ───────────────
-- Postgres has no ADD CONSTRAINT IF NOT EXISTS, so the DO-block looks the
-- existing CHECK up in pg_constraint, drops it, and recreates it complete
-- (all legacy types preserved + the five new transition types). If no CHECK
-- exists, the complete constraint is created directly.
DO $$
DECLARE
    v_constraint_name text;
BEGIN
    SELECT conname INTO v_constraint_name
    FROM pg_constraint
    WHERE conrelid = 'public.alert_rules'::regclass
      AND contype = 'c'
      AND (conname = 'alert_rules_rule_type_check'
           OR pg_get_constraintdef(oid) LIKE '%rule_type%')
    ORDER BY conname
    LIMIT 1;

    IF v_constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE public.alert_rules DROP CONSTRAINT %I', v_constraint_name);
    END IF;

    ALTER TABLE public.alert_rules ADD CONSTRAINT alert_rules_rule_type_check
        CHECK (rule_type IN (
            'price_cross',          -- legacy: price crosses a threshold
            'score_change',         -- legacy: score_total changes by N points
            'signal_change',        -- legacy: entry_signal or trend_signal changes
            'screen_match',         -- legacy: compound filter match (new entry only)
            'insider_cluster',      -- legacy: multiple insiders buy same stock
            'volatility_spike',     -- legacy: vol_20d spikes > 50%
            'thesis_transition',    -- thesis band changed between snapshots
            'setup_transition',     -- setup_state changed between snapshots
            'risk_transition',      -- risk_state changed between snapshots
            'data_grade_transition',-- data_grade changed between snapshots
            'tradability_transition'-- listing tradability state changed
        ));
END $$;

-- ─── triggered_alerts: link to the decision that caused the alert ────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'triggered_alerts'
          AND column_name = 'decision_id'
    ) THEN
        ALTER TABLE public.triggered_alerts
            ADD COLUMN decision_id uuid REFERENCES public.decision_manifests(decision_id);
    END IF;
END $$;

-- ─── holdings: link to the canonical listing ─────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'holdings'
          AND column_name = 'listing_id'
    ) THEN
        ALTER TABLE public.holdings
            ADD COLUMN listing_id uuid REFERENCES public.listings(listing_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS holdings_listing_id_idx
    ON public.holdings (listing_id);

-- ─── Backfill holdings.listing_id ────────────────────────────────────────────
-- Matches only ACTIVE listings on upper(ticker); a ticker must resolve to
-- exactly one ACTIVE listing, otherwise listing_id stays NULL and the ticker
-- is reported via NOTICE. CPRX is MERGED, so it never matches (invariant).
DO $$
DECLARE
    r          record;
    v_matches  bigint;
    v_updated  bigint := 0;
BEGIN
    FOR r IN
        SELECT h.id AS holding_id, h.ticker
        FROM public.holdings h
        WHERE h.listing_id IS NULL
    LOOP
        SELECT count(*) INTO v_matches
        FROM public.listings l
        WHERE upper(l.ticker) = upper(r.ticker)
          AND l.state = 'ACTIVE';

        IF v_matches = 1 THEN
            UPDATE public.holdings
               SET listing_id = (
                   SELECT l.listing_id
                   FROM public.listings l
                   WHERE upper(l.ticker) = upper(r.ticker)
                     AND l.state = 'ACTIVE'
               )
             WHERE id = r.holding_id;
            v_updated := v_updated + 1;
        ELSE
            RAISE NOTICE 'holdings backfill: ticker % has % ACTIVE listing(s) — listing_id left NULL', r.ticker, v_matches;
        END IF;
    END LOOP;

    RAISE NOTICE 'holdings backfill: % holding(s) updated with listing_id', v_updated;
END $$;