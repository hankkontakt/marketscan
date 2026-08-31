"""Tester för Portfolio Stress-Testing Engine."""
import unittest
from backend_worker.stress_lab import stress_test_portfolio


class TestStressLab(unittest.TestCase):
    def setUp(self):
        self.portfolio = [
            {"ticker": "MSFT", "weight": 0.25, "segment": "large_cap", "sector": "Technology", "pe": 25.0, "gross_margin": 0.68, "beta": 0.95},
            {"ticker": "JNJ", "weight": 0.25, "segment": "large_cap", "sector": "Healthcare", "pe": 15.0, "gross_margin": 0.68, "beta": 0.60},
            {"ticker": "PLEJD.ST", "weight": 0.25, "segment": "small_cap", "sector": "Technology", "pe": 41.0, "gross_margin": 0.71, "beta": 1.20},
            {"ticker": "RAY-B.ST", "weight": 0.25, "segment": "small_cap", "sector": "Healthcare", "pe": 19.0, "gross_margin": 0.85, "beta": 0.90},
        ]

    def test_stress_scenarios_exist(self):
        """Samtliga 4 kris-scenarier beräknas och rapporteras."""
        res = stress_test_portfolio(self.portfolio)
        scenarios = res["scenarios"]
        self.assertIn("RATE_SHOCK_150BPS", scenarios)
        self.assertIn("TECH_SEMI_DRAWDOWN_25PCT", scenarios)
        self.assertIn("SMALLCAP_LIQUIDITY_CRUNCH", scenarios)
        self.assertIn("STAGFLATION_ENERGY_SPIKE", scenarios)

    def test_resilience_summary(self):
        """Sammanfattande resiliensbetyg och VaR beräknas inom rimliga intervall."""
        res = stress_test_portfolio(self.portfolio)
        summary = res["summary"]
        self.assertGreater(summary["resilience_score"], 0.0)
        self.assertLessEqual(summary["resilience_score"], 100.0)
        self.assertLess(summary["worst_case_drawdown_pct"], 0.0)
        self.assertGreater(summary["estimated_10d_var_95_pct"], 0.0)

    def test_empty_portfolio_graceful(self):
        """Tom portfölj hanteras utan undantag."""
        res = stress_test_portfolio([])
        self.assertEqual(res["scenarios"], {})
        self.assertEqual(res["summary"]["resilience_score"], 50.0)


if __name__ == "__main__":
    unittest.main()
