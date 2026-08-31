"""Tester för Barbell Portfolio & Risk Optimizer Engine."""
import unittest
from backend_worker.portfolio_optimizer import build_barbell_portfolio


class TestPortfolioOptimizer(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"ticker": "MSFT", "name": "Microsoft", "segment": "large_cap", "sector": "Technology", "master_rank": 78.0, "roe": 0.34, "pe_forward": 25.0, "fcf_yield": 0.025},
            {"ticker": "TSM", "name": "TSMC", "segment": "large_cap", "sector": "Technology", "master_rank": 84.0, "roe": 0.40, "pe_forward": 22.0, "fcf_yield": 0.035},
            {"ticker": "MU", "name": "Micron", "segment": "large_cap", "sector": "Technology", "master_rank": 88.0, "roe": 0.67, "pe_forward": 6.5, "fcf_yield": 0.045},
            {"ticker": "JNJ", "name": "Johnson & Johnson", "segment": "large_cap", "sector": "Healthcare", "master_rank": 70.0, "roe": 0.20, "pe_forward": 15.0, "fcf_yield": 0.055},
            {"ticker": "PLEJD.ST", "name": "Plejd", "segment": "small_cap", "sector": "Technology", "master_rank": 75.0, "roe": 0.28, "pe_forward": 41.0, "fcf_yield": 0.020},
            {"ticker": "RAY-B.ST", "name": "RaySearch", "segment": "small_cap", "sector": "Healthcare", "master_rank": 80.0, "roe": 0.25, "pe_forward": 19.0, "fcf_yield": 0.050},
            {"ticker": "BONEX.ST", "name": "Bonesupport", "segment": "small_cap", "sector": "Healthcare", "master_rank": 75.0, "roe": 0.23, "pe_forward": 42.0, "fcf_yield": 0.015},
            {"ticker": "HANZA.ST", "name": "Hanza", "segment": "small_cap", "sector": "Industrials", "master_rank": 75.0, "roe": 0.16, "pe_forward": 11.0, "fcf_yield": 0.080},
        ]

    def test_barbell_allocation_balance(self):
        """Barbell-portföljen fördelas ~60% till Core och ~40% till Satelliter."""
        res = build_barbell_portfolio(self.candidates)
        metrics = res["metrics"]
        self.assertAlmostEqual(metrics["core_share_pct"] + metrics["satellite_share_pct"], 100.0, places=0)
        self.assertGreaterEqual(metrics["core_share_pct"], 50.0)
        self.assertLessEqual(metrics["core_share_pct"], 70.0)

    def test_weighted_metrics(self):
        """Portföljens viktade ROE och P/E beräknas korrekt."""
        res = build_barbell_portfolio(self.candidates)
        metrics = res["metrics"]
        self.assertGreater(metrics["weighted_roe_pct"], 20.0)
        self.assertIsNotNone(metrics["weighted_pe"])
        self.assertGreater(metrics["weighted_fcf_yield_pct"], 2.0)

    def test_empty_candidates_graceful(self):
        """Tom lista kraschar inte."""
        res = build_barbell_portfolio([])
        self.assertEqual(res["holdings"], [])
        self.assertEqual(res["metrics"], {})


if __name__ == "__main__":
    unittest.main()
