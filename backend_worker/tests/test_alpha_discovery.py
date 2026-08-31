import unittest
from datetime import date
from backend_worker.alpha_discovery import (
    WarrantSeries, audit_warrant_overhang, extract_warrant_mentions_from_text,
    classify_press_release, extract_order_amount_msek,
    HoldingChange, score_smart_money_cluster,
    AnalystReportItem, score_analyst_revisions,
    detect_wyckoff_divergence,
    evaluate_fcf_inflection,
    compute_alpha_score
)


class TestWarrantDetector(unittest.TestCase):
    def test_clean_warrants_no_overhang(self):
        res = audit_warrant_overhang(100.0, 10_000_000, [])
        self.assertEqual(res["warrant_risk"], "CLEAN")
        self.assertFalse(res["overhang_flag"])
        self.assertEqual(res["dilution_penalty"], 0.0)

    def test_in_the_money_near_expiry_triggers_overhang(self):
        # Current price 10.0 SEK, Strike 8.0 SEK, expiry in 30 days
        w = WarrantSeries(
            series_name="TO2",
            strike_price=8.0,
            subscription_start=date(2026, 9, 1),
            subscription_end=date(2026, 9, 20),
            warrants_outstanding=2_000_000
        )
        res = audit_warrant_overhang(10.0, 10_000_000, [w], as_of=date(2026, 8, 31))
        self.assertTrue(res["overhang_flag"])
        self.assertGreater(res["dilution_penalty"], 0.0)
        self.assertIn("TO2", res["reason"])

    def test_out_of_the_money_is_clean(self):
        # Current price 5.0 SEK, Strike 15.0 SEK (deep OTM)
        w = WarrantSeries(
            series_name="TO1",
            strike_price=15.0,
            subscription_start=date(2026, 9, 1),
            subscription_end=date(2026, 9, 20),
            warrants_outstanding=1_000_000
        )
        res = audit_warrant_overhang(5.0, 10_000_000, [w], as_of=date(2026, 8, 31))
        self.assertEqual(res["warrant_risk"], "CLEAN")
        self.assertFalse(res["overhang_flag"])

    def test_text_warrant_extractor(self):
        txt = "Bolaget genomför företrädesemission av units innehållande teckningsoptioner av serie TO 3 med teckningskurs om 4,20 SEK per aktie."
        mentions = extract_warrant_mentions_from_text(txt)
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0]["series_name"], "TO3")
        self.assertEqual(mentions[0]["strike_price"], 4.20)


class TestCatalystNLP(unittest.TestCase):
    def test_binding_order_with_high_revenue_impact(self):
        hl = "Plejd erhåller bindande order värd 45 MSEK från internationell grossist"
        body = "Ordern levereras under Q4."
        res = classify_press_release(hl, body, ttm_revenue_msek=150.0)
        self.assertEqual(res["category"], "BINDING_FIRM_ORDER")
        self.assertTrue(res["is_binding"])
        self.assertEqual(res["order_value_msek"], 45.0)
        self.assertGreaterEqual(res["catalyst_score"], 88.0)
        self.assertIn("TRANSFORMATIV", res["badge"])

    def test_non_binding_loi_flagged(self):
        hl = "BioTech AB tecknar avsiktsförklaring (LOI) med global partner"
        body = "Parterna utvärderar samarbete."
        res = classify_press_release(hl, body, ttm_revenue_msek=50.0)
        self.assertEqual(res["category"], "NON_BINDING_LOI")
        self.assertFalse(res["is_binding"])
        self.assertLessEqual(res["catalyst_score"], 30.0)

    def test_regulatory_approval(self):
        hl = "Bonesupport erhåller FDA 510(k) marknadsgodkännande i USA"
        body = "Godkännandet öppnar för försäljning i USA."
        res = classify_press_release(hl, body)
        self.assertEqual(res["category"], "REGULATORY_APPROVAL")
        self.assertGreaterEqual(res["catalyst_score"], 90.0)


class TestSmartMoneyFundTracker(unittest.TestCase):
    def test_multi_fund_cluster(self):
        c1 = HoldingChange("TIN Fonder", "TEST.ST", "NEW_POSITION", 500_000, 3.5, date.today())
        c2 = HoldingChange("Svolder", "TEST.ST", "FLAGGING_5PCT", 800_000, 5.2, date.today())
        res = score_smart_money_cluster([c1, c2])
        self.assertTrue(res["smart_money_cluster"])
        self.assertGreaterEqual(res["smart_money_score"], 80.0)
        self.assertIn("SMART MONEY KLUSTER", res["badge"])


class TestAnalystCredibility(unittest.TestCase):
    def test_tier_1_bank_vs_commissioned_discount(self):
        # Carnegie initiation with target 150 vs current 100 (+50%)
        r1 = AnalystReportItem("Carnegie", "TEST.ST", 150.0, None, "BUY", is_initiation=True)
        res = score_analyst_revisions(100.0, [r1])
        self.assertTrue(res["has_initiation"])
        self.assertGreaterEqual(res["analyst_surge_score"], 80.0)
        self.assertIn("NYBEVAKNING", res["badge"])

    def test_commissioned_research_calibration(self):
        # Redeye base case 200 vs current 100 (+100% raw) -> calibrated to +60%
        r1 = AnalystReportItem("Redeye", "TEST.ST", 200.0, 180.0, "BASE_CASE")
        res = score_analyst_revisions(100.0, [r1])
        self.assertEqual(res["calibrated_upside_pct"], 60.0)


class TestWyckoffDivergence(unittest.TestCase):
    def test_stealth_accumulation(self):
        # Retail owners fell from 5000 to 4500 (-10%), insiders bought 2.5 MSEK
        res = detect_wyckoff_divergence(4500, 5000, insider_net_buy_msek_90d=2.5)
        self.assertEqual(res["wyckoff_signal"], "STEALTH_ACCUMULATION")
        self.assertGreaterEqual(res["divergence_score"], 88.0)
        self.assertIn("STEALTH-ACKUMULATION", res["badge"])

    def test_retail_euphoria(self):
        # Retail owners surged +100%, insiders sold / 0 buy
        res = detect_wyckoff_divergence(10000, 5000, insider_net_buy_msek_90d=-1.0)
        self.assertEqual(res["wyckoff_signal"], "RETAIL_EUPHORIA")
        self.assertLessEqual(res["divergence_score"], 30.0)


class TestFCFInflection(unittest.TestCase):
    def test_fcf_turnaround_and_operating_leverage(self):
        # Was -20 MSEK, now +30 MSEK, revenue growth +25%, EBIT margin expanded from 2% to 12% (+1000 bps)
        res = evaluate_fcf_inflection(
            fcf_ttm=30_000_000,
            fcf_prior_year_ttm=-20_000_000,
            revenue_growth_yoy=0.25,
            ebit_margin_current=0.12,
            ebit_margin_prior=0.02,
            sloan_accrual_ratio=-0.04
        )
        self.assertTrue(res["is_fcf_inflection"])
        self.assertTrue(res["has_operating_leverage"])
        self.assertGreaterEqual(res["inflection_score"], 90.0)
        self.assertIn("DUBBEL INFLEKTION", res["badge"])


class TestAlphaFusion(unittest.TestCase):
    def test_guldkorn_tier_1(self):
        fcf = {"inflection_score": 95.0, "badge": "🚀 FCF INFLEKTION", "reason": "FCF positiv"}
        sm = {"smart_money_score": 90.0, "badge": "💼 SMART MONEY KLUSTER", "reason": "TIN & Svolder köper"}
        cat = {"catalyst_score": 88.0, "badge": "📦 FAST BINDANDE ORDER", "category": "BINDING_FIRM_ORDER", "summary": "Order 45 Mkr"}
        an = {"analyst_surge_score": 85.0, "badge": "📈 RIKTKURS HÖJS", "summary": "Carnegie höjer"}
        wyck = {"divergence_score": 88.0, "badge": "💎 STEALTH ACKUMULATION", "reason": "Insiders köper"}
        warr = {"warrant_risk": "CLEAN", "overhang_flag": False, "dilution_penalty": 0.0, "reason": "Inga TO"}
        
        alpha = compute_alpha_score("BONEX.ST", "Bonesupport", fcf, sm, cat, an, wyck, warr, adtv_sek_20d=2_500_000)
        self.assertEqual(alpha["alpha_tier"], "TIER_1_ALPHA")
        self.assertGreaterEqual(alpha["alpha_score"], 85.0)
        self.assertIn("GULDKORN", alpha["verdict"])
        self.assertIn("Bonesupport", alpha["thesis_memo"])


if __name__ == "__main__":
    unittest.main()
