"""Tester för MasterRank (ROND 8) — rena funktioner (ingen nätverk/DB)."""
import unittest
from datetime import date, timedelta

import backend_worker.master_rank as mr
import backend_worker.technical_snapshot as tech
import backend_worker.catalyst_fetcher as cat
import backend_worker.analyst_fetcher as an

WEIGHTS = mr.load_weights()


class TestFuse(unittest.TestCase):
    def test_bubble_triage_caps_extreme(self):
        """EXTREME_OVERVAL + OVERBOUGHT → rank capad till 60 (T3), BUBBLE_TRIAGE."""
        row = {"quality_z": 88.0, "value_z": 20.0, "momentum_z": 95.0,
               "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 80.0,
               "payout_z": 55.0, "growth_z": 75.0,
               "val_flags": ["EXTREME_OVERVAL"], "tech_flags": ["OVERBOUGHT"],
               "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertEqual(f["master_rank"], 60.0)
        self.assertEqual(f["tier"], "T3")
        self.assertEqual(f["bubble_triage"], "BUBBLE_TRIAGE")

    def test_pending_pit_caps_below_t2(self):
        """PENDING (ej READY) → thin_data-cap → aldrig T2/T1 (max T3)."""
        row = {"quality_z": 88.0, "value_z": 80.0, "momentum_z": 95.0,
               "analyst_z": 90.0, "insider_z": 80.0, "catalyst_z": 90.0,
               "payout_z": 80.0, "growth_z": 90.0,
               "val_flags": ["CHEAP"], "tech_flags": [],
               "pit_status": "PENDING"}
        f = mr.fuse(row, WEIGHTS)
        self.assertLess(f["master_rank"], 65.0)  # under T2-tröskeln (thin_data)
        self.assertEqual(f["tier"], "T3")  # aldrig T1/T2 när PENDING
        self.assertIn("thin_data", f["data_missing"])

    def test_missing_blocks_renormalized(self):
        """Saknade block → vikt 0 + data_missing (aldrig neutral 50)."""
        row = {"quality_z": 90.0, "value_z": None, "momentum_z": None,
               "analyst_z": None, "insider_z": None, "catalyst_z": None,
               "payout_z": None, "growth_z": None,
               "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertIsNotNone(f["master_rank"])
        self.assertIn("value", f["data_missing"])
        self.assertIn("momentum", f["data_missing"])

    def test_no_data_returns_none(self):
        row = {"quality_z": None, "value_z": None, "momentum_z": None,
               "analyst_z": None, "insider_z": None, "catalyst_z": None,
               "payout_z": None, "growth_z": None,
               "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertIsNone(f["master_rank"])

    def test_thin_data_caps_below_t1(self):
        """Färre än 6/8 block → aldrig T1 (renormalisering cap 1.5 + thin_data)."""
        row = {"quality_z": 99.0, "value_z": None, "momentum_z": 98.0,
               "analyst_z": None, "insider_z": None, "catalyst_z": None,
               "payout_z": None, "growth_z": None,
               "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertLess(f["master_rank"], 65.0)  # under T2-tröskeln
        self.assertNotEqual(f["tier"], "T1")
        self.assertIn("thin_data", f["data_missing"])

    def test_analyst_never_dominates(self):
        """Analyst capad: analyst contribution ≤ 15 % av rank."""
        row = {"quality_z": 90.0, "value_z": 90.0, "momentum_z": 90.0,
               "analyst_z": 100.0, "insider_z": 60.0, "catalyst_z": 80.0,
               "payout_z": 55.0, "growth_z": 75.0,
               "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertLessEqual(f["master_rank"], 100.0)


class TestValBlocks(unittest.TestCase):
    def test_val_hist_billig_ger_hog_z(self):
        """Låg P/E mot egen historik → hög val_hist_z."""
        pe = 10.0
        history = [20.0, 22.0, 25.0, 18.0, 21.0, 19.0, 24.0, 23.0]
        z = mr.val_hist_z(pe, history)
        self.assertGreater(z, 60.0)

    def test_val_hist_dyr_ger_lag_z(self):
        pe = 50.0
        history = [20.0, 22.0, 25.0, 18.0, 21.0, 19.0, 24.0, 23.0]
        z = mr.val_hist_z(pe, history)
        self.assertLess(z, 40.0)

    def test_val_peers_requires_15(self):
        self.assertIsNone(mr.val_peers_z(10.0, [20.0] * 14))
        z = mr.val_peers_z(10.0, [20.0] * 15)
        self.assertIsNotNone(z)

    def test_peg_extreme_flag(self):
        flags = mr.val_flags(50.0, 60.0, 30.0, peg=4.0, pe_hist_pctl=95.0)
        self.assertIn("EXTREME_OVERVAL", flags)


class TestTech(unittest.TestCase):
    def test_rsi_monotonic_up(self):
        closes = [100.0 + i * 0.5 for i in range(260)]
        r = tech.compute_technical(closes)
        self.assertEqual(r["tech_flags"], ["OVERBOUGHT"])
        self.assertEqual(r["trend_tech"], "Upptrend")

    def test_rsi_flat(self):
        closes = [100.0] * 260
        r = tech.compute_technical(closes)
        self.assertIsNotNone(r["rsi_14"])  # ingen volatilitet → 50 (neutral)
        self.assertEqual(r["rsi_14"], 50.0)
        self.assertNotIn("OVERBOUGHT", r["tech_flags"])

    def test_trend_down_detected(self):
        closes = [100.0 - i * 0.5 for i in range(260)]
        r = tech.compute_technical(closes)
        self.assertEqual(r["trend_tech"], "Nedtrend")
        self.assertIn("TREND_DOWN", r["tech_flags"])

    def test_pullback_flag(self):
        closes = [100.0] * 250 + [95.0] * 10
        r = tech.compute_technical(closes)
        self.assertIn("PULLBACK", r["tech_flags"])


class TestCatalyst(unittest.TestCase):
    def test_days_until(self):
        self.assertEqual(cat.days_until(date(2026, 9, 1), date(2026, 8, 30)), 2)

    def test_catalyst_z_near_event_higher(self):
        today = date(2026, 8, 30)
        near = [{"ticker": "A", "event_date": today + timedelta(days=5), "confidence": "high"}]
        far = [{"ticker": "A", "event_date": today + timedelta(days=100), "confidence": "high"}]
        z_near = cat.catalyst_z(near, today)
        z_far = cat.catalyst_z(far, today)
        self.assertIsNotNone(z_near)
        self.assertGreater(z_near, z_far)

    def test_catalyst_boost_window(self):
        today = date(2026, 8, 30)
        evs = [{"ticker": "A", "event_date": today + timedelta(days=10), "confidence": "medium"}]
        b = cat.catalyst_boost(evs, today)
        self.assertGreater(b, 0.0)
        self.assertLessEqual(b, 5.0)


class TestAnalyst(unittest.TestCase):
    def test_extract_target(self):
        mock = {"targetMeanPrice": 50.0, "targetHighPrice": 60.0, "targetLowPrice": 40.0,
                "numberOfAnalystOpinions": 7, "recommendationMean": 4.1,
                "recommendationKey": "buy", "currentPrice": 45.0}
        r = an.extract_analyst(mock, 45.0)
        self.assertEqual(r["target_median"], 50.0)
        self.assertAlmostEqual(r["upside_pct"], 11.11, places=2)
        self.assertEqual(r["flags"], [])

    def test_few_analysts_flag(self):
        mock = {"targetMeanPrice": 50.0, "numberOfAnalystOpinions": 1,
                "recommendationMean": 4.0, "currentPrice": 45.0}
        r = an.extract_analyst(mock, 45.0)
        self.assertIn("FEW_ANALYSTS", r["flags"])

    def test_dead_target_flag(self):
        mock = {"targetMeanPrice": 200.0, "numberOfAnalystOpinions": 3,
                "recommendationMean": 4.0, "currentPrice": 45.0}
        r = an.extract_analyst(mock, 45.0)
        self.assertIn("DEAD_TARGET", r["flags"])

    def test_analyst_z_coverage_scaling(self):
        """Fler analytiker → inte lägre z (coverage skalar upp, aldrig ned)."""
        single = {"upside_pct": 20.0, "recommendation_mean": 1.5, "target_count": 1}
        many = {"upside_pct": 20.0, "recommendation_mean": 1.5, "target_count": 10}
        z_single = an.analyst_z(single)
        z_many = an.analyst_z(many)
        self.assertIsNotNone(z_single)
        self.assertIsNotNone(z_many)
        self.assertGreaterEqual(z_many, z_single)


class TestTier(unittest.TestCase):
    def test_tier_thresholds(self):
        self.assertEqual(mr.tier_of(80.0, False, "READY"), "T1")
        self.assertEqual(mr.tier_of(70.0, False, "READY"), "T2")
        self.assertEqual(mr.tier_of(55.0, False, "READY"), "T3")
        self.assertEqual(mr.tier_of(40.0, False, "READY"), "T4")
        self.assertEqual(mr.tier_of(None, True, "READY"), "EXCLUDED")

    def test_signal_from_tier(self):
        """ROND 9: entry_signal härleds från MasterRank-tier (PETR4-fix)."""
        self.assertEqual(mr.signal_from_tier("T1"), "STARK")
        self.assertEqual(mr.signal_from_tier("T2"), "OK")
        self.assertEqual(mr.signal_from_tier("T3"), "VÄNTA")
        self.assertEqual(mr.signal_from_tier("T4"), "EJ_AKTUELL")
        self.assertEqual(mr.signal_from_tier("EXCLUDED"), "EJ_AKTUELL")

    def test_fuse_includes_entry_signal(self):
        """fuse returnerar also entry_signal — etiketten speglar ranken."""
        row = {"quality_z": 88.0, "value_z": 80.0, "momentum_z": 90.0,
               "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 80.0,
               "payout_z": 55.0, "growth_z": 75.0,
               "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(row, WEIGHTS)
        self.assertEqual(f["entry_signal"], "T2" if f["tier"] == "T2" else "STARK")

    def test_forensic_disqualification_consistency(self):
        """Forensisk diskvalificering eller T3-tak sänker rank och sätter tak.

        Invariant: om ett bolag har tier_cap='T3' pga emissionsrisk eller allvarliga
        forensiska brister, kan master_rank INTE nå T1/T2.
        """
        row = {"quality_z": 90.0, "value_z": 80.0, "momentum_z": 85.0,
               "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 80.0,
               "payout_z": 55.0, "growth_z": 75.0,
               "val_flags": [], "tech_flags": [], "pit_status": "READY",
               "tier_cap": "T3", "forensic_penalty": 15.0}
        f = mr.fuse(row, WEIGHTS)
        self.assertLess(f["master_rank"], 65.0)          # ej T2
        self.assertIn("forensic_t3_cap", f["data_missing"])

    def test_tier_smallcap_thresholds(self):
        """Småbolag har lägre trösklar — rank 62 = T1 (STARK) för small_cap."""
        self.assertEqual(mr.tier_of(62.0, False, "READY", segment="small_cap"), "T1")
        self.assertEqual(mr.tier_of(55.0, False, "READY", segment="small_cap"), "T2")
        self.assertEqual(mr.tier_of(50.0, False, "READY", segment="small_cap"), "T2")
        self.assertEqual(mr.tier_of(45.0, False, "READY", segment="small_cap"), "T3")
        self.assertEqual(mr.tier_of(38.0, False, "READY", segment="small_cap"), "T3")
        self.assertEqual(mr.tier_of(30.0, False, "READY", segment="small_cap"), "T4")

    def test_tier_microcap_same_as_smallcap(self):
        """Micro_cap använder samma trösklar som small_cap."""
        self.assertEqual(mr.tier_of(62.0, False, "READY", segment="micro_cap"), "T1")
        self.assertEqual(mr.tier_of(50.0, False, "READY", segment="micro_cap"), "T2")

    def test_tier_largecap_unchanged(self):
        """Large_cap behåller originaltrösklarna."""
        self.assertEqual(mr.tier_of(70.0, False, "READY", segment="large_cap"), "T2")
        self.assertEqual(mr.tier_of(74.0, False, "READY", segment="large_cap"), "T2")
        self.assertEqual(mr.tier_of(75.0, False, "READY", segment="large_cap"), "T1")

    def test_fuse_smallcap_thin_data_relaxed(self):
        """Småbolag med 3 block (quality, value, momentum) ska inte stoppas av thin_data."""
        row = {"quality_z": 75.0, "value_z": 70.0, "momentum_z": 65.0,
               "val_flags": [], "tech_flags": [], "pit_status": "READY",
               "segment": "small_cap"}
        f = mr.fuse(row, WEIGHTS)
        # 3 blocks filled: quality, value, momentum — should NOT be thin_data capped for small_cap
        self.assertNotIn("thin_data", f.get("data_missing", []))
        self.assertGreaterEqual(f["master_rank"], 50.0)


class TestPitStatus(unittest.TestCase):
    def test_ready(self):
        pit, reason = mr.pit_status(date(2025, 12, 31), date(2026, 8, 30))
        self.assertEqual(pit, "READY")

    def test_pending(self):
        pit, _ = mr.pit_status(date(2026, 6, 30), date(2026, 8, 30))
        self.assertEqual(pit, "PENDING")

    def test_stale(self):
        pit, _ = mr.pit_status(None, date(2026, 8, 30))
        self.assertEqual(pit, "STALE")


class TestReweight(unittest.TestCase):
    def test_ic_maps_to_weights(self):
        """IC > 0.03 → uppvikt; IC < -0.02 → nedvikt; neutral → minskad."""
        ic_map = {"quality": 0.05, "value": -0.04, "momentum": 0.002}
        new_w = mr.reweight_from_ic(ic_map, WEIGHTS)
        self.assertGreater(new_w["weights"]["quality"], WEIGHTS["weights"]["quality"])
        self.assertLess(new_w["weights"]["value"], WEIGHTS["weights"]["value"])
        total = sum(new_w["weights"].values())
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_reweight_noise_gate(self):
        """ROND 9: n < 30 → ingen ändring (brus); IC under noise-floor → ingen uppvikt."""
        # För få observationer → oförändrade vikter
        low_n = {"quality": 10}
        new_w = mr.reweight_from_ic({"quality": 0.05}, WEIGHTS, n_map=low_n)
        self.assertEqual(new_w["weights"]["quality"], WEIGHTS["weights"]["quality"])
        # IC under noise-floor (1.96/sqrt(30)=0.358) → ingen uppvikt; renorm 0.25→0.2308
        ok_n = {"quality": 30}
        new_w2 = mr.reweight_from_ic({"quality": 0.05}, WEIGHTS, n_map=ok_n)
        self.assertLess(new_w2["weights"]["quality"], WEIGHTS["weights"]["quality"] * 1.01)


class TestSectorNeutral(unittest.TestCase):
    def test_sector_z_within_sector(self):
        """ROND 9: sektor-neutral z — lägre P/E än peers → hög z, ej global."""
        sector_maps = {"pe_trailing": {"Technology": [20.0, 30.0, 40.0, 50.0, 60.0] * 4}}
        # P/E 55 (nära toppen av 20-60 → hög percentil = dyr → LÅG z)
        z = mr.sector_neutral_z(55.0, "Technology", sector_maps["pe_trailing"])
        self.assertLess(z, 30.0)
        # P/E 22 (i botten → låg percentil = billig → HÖG z)
        z2 = mr.sector_neutral_z(22.0, "Technology", sector_maps["pe_trailing"])
        self.assertGreater(z2, 70.0)

    def test_sector_z_fallback_global(self):
        """Saknar sektor/för få peers → global percentil (oförändrad)."""
        val = 42.0
        self.assertEqual(mr.sector_neutral_z(val, None, {}), 42.0)
        self.assertEqual(mr.sector_neutral_z(val, "Tech", {"Tech": [1.0]}), 42.0)


class TestEvidenceLoop(unittest.TestCase):
    def test_purged_folds(self):
        """ROND 9: purged walk-forward ger folds med icke-överlappande fönster."""
        from datetime import date, timedelta
        from backend_worker import evidence_loop
        rows = []
        for i in range(400):  # 400 dagar — ger flera folds givet horizon 30/embargo 5
            rows.append({"ticker": "A", "scan_date": date(2026, 1, 1) + timedelta(days=i),
                         "value": float(i), "fwd": float(i % 7)})
        folds = evidence_loop.purged_walk_forward(rows, horizon=30, embargo=5)
        self.assertGreater(len(folds), 0)
        # Varje fold: train-slut + horizon + embargo <= test-start (ingen läcka)
        for train, test in folds:
            train_end = max(r["scan_date"] for r in train)
            test_start = min(r["scan_date"] for r in test)
            self.assertLessEqual(train_end + timedelta(days=35), test_start)

    def test_ic_with_purge_valid(self):
        """purged-IC returnerar float för tillräcklig data."""
        from datetime import date, timedelta
        from backend_worker import evidence_loop
        rows = []
        for i in range(400):
            rows.append({"ticker": "A", "scan_date": date(2026, 1, 1) + timedelta(days=i),
                         "value": float(i), "fwd": float(i)})
        folds = evidence_loop.purged_walk_forward(rows, 30, 5)
        ic = evidence_loop.ic_with_purge(folds)
        self.assertIsNotNone(ic)

    def test_deflated_sharpe_gate(self):
        """DSR-gate: fler tester → högre strap → lägre signifikans."""
        from backend_worker import evidence_loop
        single = evidence_loop.deflated_sharpe_correction(0.05, n_tests=1, n_obs=100)
        many = evidence_loop.deflated_sharpe_correction(0.05, n_tests=8, n_obs=100)
        self.assertIsNotNone(single)
        self.assertGreater(single, many)  # fler tester straffar mer


class TestMasterRank2Upgrades(unittest.TestCase):
    def test_compute_peg_unit_consistency(self):
        """PEG hanterar både decimal (0.25) och procent (25.0) utan 100x fel."""
        # 18.8 P/E och 66.9% tillväxt (decimal 0.669) -> PEG ≈ 0.28
        peg_dec = mr.compute_peg(18.8, 0.669)
        peg_pct = mr.compute_peg(18.8, 66.9)
        self.assertIsNotNone(peg_dec)
        self.assertIsNotNone(peg_pct)
        self.assertAlmostEqual(peg_dec, 0.281, places=2)
        self.assertAlmostEqual(peg_pct, 0.281, places=2)

    def test_val_abs_z_rewards_low_peg_growth(self):
        """Låg PEG (Peter Lynch tillväxt) ger hög absolut score (≥80)."""
        z = mr.val_abs_z(pe_forward=18.8, revenue_growth=0.669, ev_ebitda=None, value_z_qmj=None)
        self.assertIsNotNone(z)
        self.assertGreater(z, 80.0)

    def test_val_abs_z_forward_inflection_bonus(self):
        """Forward P/E betydligt lägre än Trailing P/E ger turnaround-bonus."""
        # Trailing P/E 50x, Forward P/E 18x
        z_turnaround = mr.val_abs_z(pe_forward=18.0, revenue_growth=0.20, ev_ebitda=None, value_z_qmj=None, pe_trailing=50.0)
        z_flat = mr.val_abs_z(pe_forward=18.0, revenue_growth=0.20, ev_ebitda=None, value_z_qmj=None, pe_trailing=18.0)
        self.assertGreater(z_turnaround, z_flat)

    def test_qarp_synergy_boosts_quality_value_stocks(self):
        """QARP (Kvalitet ≥70 och Värde ≥65) ger icke-linjär synergibonus."""
        high_q_high_v = {"quality_z": 85.0, "value_z": 80.0, "momentum_z": 70.0,
                         "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 60.0,
                         "payout_z": 60.0, "growth_z": 70.0,
                         "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f_qarp = mr.fuse(high_q_high_v, WEIGHTS)

        # Samma aktie fast med isolerat värde lägre än 65 (ej QARP-tröskel)
        high_q_med_v = dict(high_q_high_v)
        high_q_med_v["value_z"] = 55.0
        f_non_qarp = mr.fuse(high_q_med_v, WEIGHTS)

        # QARP-versionen ska ha en tydlig uppväxling
        self.assertGreater(f_qarp["master_rank"], f_non_qarp["master_rank"] + 3.0)

    def test_compounder_payout_protection(self):
        """Högkvalitativ tillväxtcompounder straffas inte för låg utdelning."""
        compounder_low_div = {"quality_z": 90.0, "value_z": 75.0, "momentum_z": 75.0,
                              "analyst_z": 75.0, "insider_z": 50.0, "catalyst_z": 50.0,
                              "payout_z": 10.0, "growth_z": 80.0,
                              "val_flags": [], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(compounder_low_div, WEIGHTS)
        # Ska inte dras ned under T1
        self.assertGreaterEqual(f["master_rank"], 75.0)
        self.assertEqual(f["tier"], "T1")

    def test_soe_political_risk_moderation(self):
        """SOE med politisk risk cappas från att ta #1-platsen."""
        soe_stock = {"quality_z": 95.0, "value_z": 95.0, "momentum_z": 90.0,
                     "analyst_z": 80.0, "insider_z": 70.0, "catalyst_z": 80.0,
                     "payout_z": 95.0, "growth_z": 70.0,
                     "val_flags": ["SOE_POLITICAL_RISK"], "tech_flags": [], "pit_status": "READY"}
        f = mr.fuse(soe_stock, WEIGHTS)
        self.assertLessEqual(f["master_rank"], 69.5)
        self.assertIn("soe_governance_risk", f["data_missing"])

    def test_quality_momentum_guard_caps_low_quality(self):
        """Olympus-skyddet: Låg kvalitet (<60) och svag värdering (<50) cappas till max T3 trots högt momentum."""
        low_quality_high_momentum = {
            "quality_z": 55.0, "value_z": 45.0, "momentum_z": 90.0,
            "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0,
            "payout_z": 50.0, "growth_z": 40.0,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(low_quality_high_momentum, WEIGHTS)
        self.assertLess(f["master_rank"], 65.0)
        self.assertEqual(f["tier"], "T3")
        self.assertIn("quality_momentum_guard", f["data_missing"])

    def test_elite_compounder_moat_bonus(self):
        """Elite Compounders (Kvalitet ≥90, Tillväxt ≥75, Analytiker ≥75) erhåller vallgravsbonus."""
        elite_stock = {
            "quality_z": 95.0, "value_z": 60.0, "momentum_z": 85.0,
            "analyst_z": 85.0, "insider_z": 70.0, "catalyst_z": 60.0,
            "payout_z": 50.0, "growth_z": 85.0,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(elite_stock, WEIGHTS)
        self.assertGreaterEqual(f["master_rank"], 78.0)
        self.assertEqual(f["tier"], "T1")

    def test_analyst_target_exhaustion_penalty(self):
        """Analytikeruppsida ≤ 0% med stor analytikerkår (≥8) ger dämpat delbetyg."""
        exhausted = {"upside_pct": -0.5, "recommendation_mean": 2.5, "target_count": 20}
        az_exhausted = an.analyst_z(exhausted)
        self.assertIsNotNone(az_exhausted)
        self.assertLess(az_exhausted, 52.0)

    def test_analyst_strong_buy_confidence_boost(self):
        """Strong Buy (rec_mean ≤ 1.4) med många analytiker (≥15) ger konfidensförstärkning."""
        strong_buy = {"upside_pct": 15.0, "recommendation_mean": 1.2, "target_count": 30}
        az_strong = an.analyst_z(strong_buy)
        self.assertIsNotNone(az_strong)
        self.assertGreater(az_strong, 75.0)

    def test_peg_negative_growth_guard(self):
        """Negativ eller nära-noll tillväxt returnerar None för PEG och förbjuder CHEAP_PEG."""
        self.assertIsNone(mr.compute_peg(15.0, -0.05))
        self.assertIsNone(mr.compute_peg(15.0, 0.001))
        flags = mr.val_flags(85.0, 85.0, 85.0, peg=None, pe_hist_pctl=40.0, revenue_growth=-0.10)
        self.assertNotIn("CHEAP_PEG", flags)

    def test_analyst_dispersion_penalty(self):
        """Bred riktkursspridning (high-low/med > 0.5) dämpar analyst_z delbetyget."""
        consensus_tight = {"upside_pct": 25.0, "recommendation_mean": 1.8, "target_count": 12, "target_dispersion": 0.2}
        consensus_wide = {"upside_pct": 25.0, "recommendation_mean": 1.8, "target_count": 12, "target_dispersion": 1.2}
        z_tight = an.analyst_z(consensus_tight)
        z_wide = an.analyst_z(consensus_wide)
        self.assertIsNotNone(z_tight)
        self.assertIsNotNone(z_wide)
        self.assertGreater(z_tight, z_wide)

    def test_segment_percentile_computation(self):
        """compute_table beräknar segment-normaliserad master_rank_pctl inom varje segment."""
        table_input = [
            {"ticker": "L1", "segment": "large_cap", "quality_z": 90.0, "value_z": 70.0, "momentum_z": 80.0,
             "analyst_z": 70.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 50.0, "growth_z": 70.0,
             "val_flags": [], "tech_flags": [], "pit_status": "READY"},
            {"ticker": "L2", "segment": "large_cap", "quality_z": 60.0, "value_z": 40.0, "momentum_z": 50.0,
             "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 50.0, "growth_z": 50.0,
             "val_flags": [], "tech_flags": [], "pit_status": "READY"},
            {"ticker": "S1", "segment": "small_cap", "quality_z": 80.0, "value_z": 60.0, "momentum_z": 70.0,
             "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 50.0, "growth_z": 60.0,
             "val_flags": [], "tech_flags": [], "pit_status": "READY"},
        ]
        result = mr.compute_table(table_input, WEIGHTS)
        l1 = next(r for r in result if r["ticker"] == "L1")
        l2 = next(r for r in result if r["ticker"] == "L2")
        s1 = next(r for r in result if r["ticker"] == "S1")
        self.assertEqual(l1["master_rank_pctl"], 100.0)
        self.assertEqual(l2["master_rank_pctl"], 50.0)
        self.assertEqual(s1["master_rank_pctl"], 100.0)

    def test_bubble_pre_dampening_smooth(self):
        """RSI 73 vid EXTREME_OVERVAL dämpar mjukt utan att krascha direkt till 60."""
        row_73 = {"quality_z": 85.0, "value_z": 20.0, "momentum_z": 90.0,
                  "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 70.0,
                  "payout_z": 50.0, "growth_z": 70.0, "rsi_14": 73.0,
                  "val_flags": ["EXTREME_OVERVAL"], "tech_flags": [],
                  "pit_status": "READY"}
        f_73 = mr.fuse(row_73, WEIGHTS)
        self.assertIn("bubble_warning", f_73["data_missing"])
        self.assertGreater(f_73["master_rank"], 60.0)  # Inte hård-cappad vid 60 ännu

    def test_smallcap_runway_dilution_shield(self):
        """Olönsamt småbolag med kort kassa (<12 månader) cappas till T4 (<50) och flaggas."""
        burning_smallcap = {
            "segment": "small_cap", "quality_z": 30.0, "value_z": 40.0, "momentum_z": 80.0,
            "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 30.0, "growth_z": 40.0,
            "cash_runway_months": 5.0, "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(burning_smallcap, WEIGHTS)
        self.assertLess(f["master_rank"], 50.0)
        self.assertIn("cash_runway_risk", f["data_missing"])

    def test_smallcap_compounder_mews_synergy(self):
        """Kvalitets-småbolag (Quality >= 85) med insiderköp och MEWS-score erhåller vallgravsbonus."""
        harvia_like = {
            "segment": "small_cap", "quality_z": 88.0, "value_z": 60.0, "momentum_z": 70.0,
            "analyst_z": 65.0, "insider_z": 70.0, "catalyst_z": 60.0, "payout_z": 60.0, "growth_z": 70.0,
            "mews_score": 75.0, "insider_buying": True, "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(harvia_like, WEIGHTS)
        self.assertGreaterEqual(f["master_rank"], 65.0)

    def test_financial_structuring_volatility_cap(self):
        """Finansiell leasing/skattestrukturerare (FPG 7148.T) cappas vid max 58."""
        fpg = {
            "ticker": "7148.T", "segment": "small_cap", "sector": "Finans",
            "quality_z": 70.0, "value_z": 90.0, "momentum_z": 60.0,
            "analyst_z": 60.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 85.0, "growth_z": 40.0,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(fpg, WEIGHTS)
        self.assertLessEqual(f["master_rank"], 58.0)
        self.assertIn("earnings_volatility_cap", f["data_missing"])


    def test_segment_sector_normalization_fallback_chain(self):
        """D3: Normalisering inom (segment, sektor) >= 5, annars sektor >= 15, annars global."""
        seg_sec_maps = {
            "pe_trailing": {
                ("small_cap", "Tech"): [10.0, 20.0, 30.0, 40.0, 50.0],  # 5 peers -> group
                ("small_cap", "Bio"): [10.0, 20.0],                      # 2 peers (<5) -> fallback
            }
        }
        sec_maps = {
            "pe_trailing": {
                "Bio": [float(x) for x in range(1, 16)],                 # 15 peers -> sector
                "TinySec": [10.0, 20.0],                                  # 2 peers (<15) -> global
            }
        }
        # 1. (small_cap, Tech): 5 peers, val=10.0 (cheapest) -> z=100.0
        z_group = mr.group_percentile_z(10.0, "small_cap", "Tech", seg_sec_maps, sec_maps, "pe_trailing")
        self.assertEqual(z_group, 100.0)

        # 2. (small_cap, Bio): 2 peers -> fallback to Bio sector (15 peers)
        z_sec = mr.group_percentile_z(1.0, "small_cap", "Bio", seg_sec_maps, sec_maps, "pe_trailing")
        self.assertEqual(z_sec, 100.0)

        # 3. (micro_cap, TinySec): fallback to global
        z_global = mr.group_percentile_z(75.0, "micro_cap", "TinySec", seg_sec_maps, sec_maps, "pe_trailing")
        self.assertEqual(z_global, 75.0)

    def test_momentum_segment_percentile_compute_table(self):
        """D3: Momentum percentileras inom segment om >= 10 medlemmar."""
        # 10 large caps med olika momentum_z
        large_rows = [
            {"ticker": f"L{i}", "segment": "large_cap", "momentum_z": float(i * 10),
             "quality_z": 70.0, "value_z": 70.0, "pit_status": "READY"}
            for i in range(1, 11)
        ]
        res = mr.compute_table(large_rows, WEIGHTS)
        # Högsta råvärdet L10 (100) ska få percentil 100.0
        l10 = next(r for r in res if r["ticker"] == "L10")
        self.assertEqual(l10["momentum_z"], 100.0)
        # L1 (10) ska få 10.0 percentil
        l1 = next(r for r in res if r["ticker"] == "L1")
        self.assertEqual(l1["momentum_z"], 10.0)

    def test_weights_v2_and_segment_overrides(self):
        """D1: resolve_weights applicerar 0.18 value / 0.02 growth för small/micro."""
        w_small = mr.resolve_weights(WEIGHTS, "small_cap")
        w_micro = mr.resolve_weights(WEIGHTS, "micro_cap")
        w_large = mr.resolve_weights(WEIGHTS, "large_cap")

        self.assertAlmostEqual(w_small["value"], 0.18, places=3)
        self.assertAlmostEqual(w_small["growth"], 0.02, places=3)
        self.assertAlmostEqual(sum(w_small.values()), 1.0, places=3)

        self.assertAlmostEqual(w_micro["value"], 0.18, places=3)
        self.assertAlmostEqual(w_micro["growth"], 0.02, places=3)

        self.assertAlmostEqual(w_large["value"], 0.15, places=3)
        self.assertAlmostEqual(w_large["growth"], 0.05, places=3)

    def test_junk_gate_small_micro(self):
        """D2: small/micro med quality_z < 55 kan aldrig nå T1 (cap 61.999, junk_gate)."""
        junk_smallcap = {
            "segment": "small_cap", "quality_z": 45.0, "value_z": 95.0, "momentum_z": 95.0,
            "analyst_z": 80.0, "insider_z": 80.0, "catalyst_z": 80.0, "payout_z": 70.0, "growth_z": 70.0,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(junk_smallcap, WEIGHTS)
        self.assertLessEqual(f["master_rank"], 61.999)
        self.assertIn("junk_gate", f["data_missing"])
        self.assertNotEqual(f["tier"], "T1")

    def test_liquidity_gate_small_micro(self):
        """D5: small/micro med grade E/F cappas vid max T3 (<50.0)."""
        illiquid_smallcap = {
            "segment": "small_cap", "liquidity_grade": "E",
            "quality_z": 85.0, "value_z": 75.0, "momentum_z": 80.0,
            "analyst_z": 70.0, "insider_z": 70.0, "catalyst_z": 70.0, "payout_z": 70.0, "growth_z": 70.0,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(illiquid_smallcap, WEIGHTS)
        self.assertLessEqual(f["master_rank"], 49.999)
        self.assertIn("liquidity_gate", f["data_missing"])
        self.assertEqual(f["tier"], "T3")  # max T3 (38.0 <= 49.999 < 50.0)

    def test_regime_merge_preserves_segment_overrides(self):
        """Regime-merge bevarar segment_overrides och v2 metadata."""
        from backend_worker.macro_regime import compute_smoothed_regime_weights
        merged = compute_smoothed_regime_weights("EXPANSION_RISK_ON", WEIGHTS)
        self.assertIn("segment_overrides", merged)
        self.assertIn("small_cap", merged["segment_overrides"])
        self.assertIn("weights", merged)


class TestMasterRankR15StreetParity(unittest.TestCase):
    def test_bmy_revenue_decline_earnings_spike_guard(self):
        """BMY-fall: intäkter faller (-3%) medan vinst rusar (+137%) pga engångseffekter -> earnings_spike_watch & growth_z <= 45."""
        bmy_row = {
            "ticker": "BMY", "segment": "large_cap",
            "quality_z": 75.0, "value_z": 60.0, "momentum_z": 55.0,
            "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 60.0,
            "growth_z": 78.0, "revenue_growth": -0.03, "earnings_growth": 1.37,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(bmy_row, WEIGHTS)
        self.assertIn("earnings_spike_watch", f["data_missing"])
        # Check against baseline with growth_z=45
        bmy_baseline = dict(bmy_row)
        bmy_baseline["growth_z"] = 45.0
        f_base = mr.fuse(bmy_baseline, WEIGHTS)
        self.assertEqual(f["master_rank"], f_base["master_rank"])

    def test_text_olympus_value_trap_guard(self):
        """Value trap (Olympus/Text S.A.): value_z >= 85 parat med negativ tillväxt -> value_trap_watch & value_z <= 65."""
        trap_row = {
            "ticker": "TXT.WA", "segment": "small_cap",
            "quality_z": 70.0, "value_z": 92.0, "momentum_z": 45.0,
            "analyst_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 80.0, "growth_z": 40.0,
            "revenue_growth": -0.05, "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(trap_row, WEIGHTS)
        self.assertIn("value_trap_watch", f["data_missing"])
        # With value_z dampened to 65, master_rank is bounded
        trap_baseline = dict(trap_row)
        trap_baseline["value_z"] = 65.0
        f_base = mr.fuse(trap_baseline, WEIGHTS)
        self.assertEqual(f["master_rank"], f_base["master_rank"])

    def test_atoss_qarp_relief(self):
        """ATOSS-fall: exceptionell kvalitet (Quality 89, ROE 66%, PEG <= 3) -> qarp_relief ger synergibonus."""
        atoss_row = {
            "ticker": "AOF.DE", "segment": "small_cap",
            "quality_z": 89.0, "value_z": 22.0, "momentum_z": 60.0,
            "analyst_z": 43.5, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 65.0, "growth_z": 55.0,
            "roe_raw": 0.66, "pe_forward": 26.6, "revenue_growth": 0.13,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(atoss_row, WEIGHTS)
        self.assertIn("qarp_relief", f["data_missing"])
        # Without relief (e.g. roe_raw not provided), rank would be lower
        atoss_no_relief = dict(atoss_row)
        atoss_no_relief["roe_raw"] = None
        f_no_relief = mr.fuse(atoss_no_relief, WEIGHTS)
        self.assertGreater(f["master_rank"], f_no_relief["master_rank"])

    def test_mu_cycle_peak_moderation(self):
        """MU-fall: cykeltopp med ROE > 50% och låg forward P/E (<10) -> cycle_peak dämpar quality och neutraliserar value-bonus."""
        mu_row = {
            "ticker": "MU", "segment": "large_cap",
            "quality_z": 96.0, "value_z": 88.0, "momentum_z": 75.0,
            "analyst_z": 75.0, "insider_z": 50.0, "catalyst_z": 50.0, "payout_z": 50.0, "growth_z": 75.0,
            "pe_forward": 8.5, "roe_raw": 0.67,
            "val_flags": [], "tech_flags": [], "pit_status": "READY"
        }
        f = mr.fuse(mu_row, WEIGHTS)
        self.assertIn("cycle_peak", f["data_missing"])
        # Quality capped to 75 and value to 65
        mu_baseline = dict(mu_row)
        mu_baseline["quality_z"] = 75.0
        mu_baseline["value_z"] = 65.0
        f_base = mr.fuse(mu_baseline, WEIGHTS)
        self.assertEqual(f["master_rank"], f_base["master_rank"])

    def test_upsert_master_sql_contains_pctl(self):
        """Verifiera att upsert_master inkluderar master_rank_pctl i SQL och bindings."""
        executed_sqls = []
        executed_params = []

        class MockCursor:
            def execute(self, sql, params=None):
                executed_sqls.append(sql)
                executed_params.append(params)

        cur = MockCursor()
        table = [{
            "ticker": "AOF.DE", "master_rank": 52.0, "master_rank_pctl": 88.5,
            "tier": "T2", "quality_z": 89.0, "value_z": 22.0, "momentum_z": 60.0,
            "analyst_z": 43.5, "tech_z": 50.0, "insider_z": 50.0, "catalyst_z": 50.0,
            "payout_z": 65.0, "growth_z": 55.0, "val_hist_z": None, "val_peers_z": None,
            "val_abs_z": None, "val_flags": [], "analyst_upside": 19.3, "analyst_count": 8,
            "analyst_flags": [], "rsi_14": 55.0, "ma50_dist_pct": 2.0, "ma200_dist_pct": 5.0,
            "dist_52w_high_pct": -5.0, "trend_tech": "Upptrend", "tech_flags": [],
            "catalyst_next": None, "catalyst_days": None, "pit_status": "READY",
            "pit_reason": "", "exclusion_reason": None, "data_missing": "[]",
            "currency": "EUR", "insider_source": "proxy", "entry_signal": "OK"
        }]
        written = mr.upsert_master(cur, table, date.today(), {})
        self.assertEqual(written, 1)
        self.assertIn("master_rank_pctl", executed_sqls[0])
        self.assertIn("EXCLUDED.master_rank_pctl", executed_sqls[0])
        self.assertEqual(executed_params[0][2], 52.0)    # master_rank
        self.assertEqual(executed_params[0][3], 88.5)    # master_rank_pctl


if __name__ == "__main__":
    unittest.main()


