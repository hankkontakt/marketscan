"""
test_forensic_shield.py — Enhetstester för den forensiska skyddsmotorn.
"""
import unittest
from backend_worker import forensic_shield as fs


class TestForensicShield(unittest.TestCase):
    def test_clean_compounder_no_penalties(self):
        """Ett bolag med negativt accruals och god kassa får bonus och full T1-behörighet."""
        fund = {
            "sloan_accrual_ratio": -0.06,
            "cash_runway_months": None,
            "dilution_rate_pct": 1.2,
            "gross_margin_trend_pct": 2.5,
            "fcf_yield": 0.09,
            "forensic_flags": ["HIGH_FCF_YIELD"]
        }
        res = fs.audit_company_forensics(fund, None, ticker="PLEJD.ST")
        self.assertGreaterEqual(res["forensic_health_score"], 85.0)
        self.assertEqual(res["tier_cap"], "T1")
        self.assertFalse(res["is_distressed"])
        self.assertGreater(res["rank_bonus"], 0.0)

    def test_sloan_accrual_warning_penalized(self):
        """Höga accruals (>10% av tillgångarna) straffas med varningsflagga och poängavdrag."""
        fund = {
            "sloan_accrual_ratio": 0.15,
            "cash_runway_months": None,
            "dilution_rate_pct": 2.0,
            "gross_margin_trend_pct": 0.0,
            "fcf_yield": 0.02
        }
        res = fs.audit_company_forensics(fund, None, ticker="TRAP.ST")
        self.assertIn("ACCRUAL_WARNING", res["forensic_flags"])
        self.assertGreater(res["rank_penalty"], 0.0)

    def test_critical_cash_runway_caps_to_t3_or_disqualified(self):
        """Ett bolag med <6 månaders kassa och massiv utspädning flaggas och diskvalificeras från T1/T2."""
        fund = {
            "sloan_accrual_ratio": 0.02,
            "cash_runway_months": 4.5,
            "dilution_rate_pct": 15.0,
            "gross_margin_trend_pct": -4.0,
            "fcf_yield": -0.20
        }
        res = fs.audit_company_forensics(fund, None, ticker="BURN.ST")
        self.assertIn("DILUTION_EMISSION_RISK", res["forensic_flags"])
        self.assertIn("SHARE_DILUTION_WARNING", res["forensic_flags"])
        self.assertIn("MARGIN_EROSION", res["forensic_flags"])
        self.assertIn(res["tier_cap"], ["T3", "DISQUALIFIED"])
        self.assertTrue(res["is_distressed"])

    def test_ai_capitalized_rd_disqualifies_false_profits(self):
        """AI-detekterad dolda FoU-kostnader sänker betyget och cappas."""
        fund = {"sloan_accrual_ratio": 0.01}
        ai = {
            "ebit_reported_msek": 5.0,
            "real_ebit_without_capitalization_msek": -8.0,
            "dilution_emission_risk_level": "MYCKET_HÖG",
            "forensic_red_flags": ["Hög kapitalisering"]
        }
        res = fs.audit_company_forensics(fund, ai, ticker="FAKEPROFIT.ST")
        self.assertIn("CAPITALIZED_EXPENSE_WARNING", res["forensic_flags"])
        self.assertIn("AI_HIGH_DILUTION_RISK", res["forensic_flags"])
        self.assertIn(res["tier_cap"], ["T3", "DISQUALIFIED"])


if __name__ == "__main__":
    unittest.main()
