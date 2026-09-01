"""Tests for segment classification, unit guards, and downstream consumer safety."""
import unittest
from apps.api.core.segments import (
    segment_from_market_cap,
    segment_from_finnhub_mcap,
    SEGMENT_THRESHOLDS,
)
from apps.api.routers.stocks import _segment_from_market
from backend_worker.db_loader import _derive_segment, SEGMENT_THRESHOLDS as WORKER_THRESHOLDS
from backend_worker.portfolio_optimizer import build_barbell_portfolio
from backend_worker.stress_lab import stress_test_portfolio


class TestSegmentClassification(unittest.TestCase):
    def test_threshold_parity(self):
        """API and worker threshold dictionaries must be identical."""
        self.assertEqual(SEGMENT_THRESHOLDS, WORKER_THRESHOLDS)

    def test_derive_segment_guard_and_fallbacks(self):
        """Test _derive_segment unit guard, none fallback, and thresholds."""
        # None and non-positive fall back to 'unknown'
        self.assertEqual(_derive_segment(None), "unknown")
        self.assertEqual(_derive_segment(0), "unknown")
        self.assertEqual(_derive_segment(-100), "unknown")

        # Probable million unit (2e5 = 200,000 scaled by 1e6 -> 200B USD = large_cap)
        self.assertEqual(_derive_segment(200_000), "large_cap")
        self.assertEqual(_derive_segment(2e5), "large_cap")

        # True small/micro cap USD values
        self.assertEqual(_derive_segment(50_000_000), "micro_cap")   # 50M < 300M
        self.assertEqual(_derive_segment(500_000_000), "small_cap")  # 500M >= 300M
        self.assertEqual(_derive_segment(5_000_000_000), "mid_cap")  # 5B >= 2B
        self.assertEqual(_derive_segment(50_000_000_000), "large_cap") # 50B >= 10B

    def test_api_segment_functions(self):
        """Test apps/api/core/segments.py functions."""
        self.assertEqual(segment_from_market_cap(None), "unknown")
        self.assertEqual(segment_from_market_cap(0), "unknown")
        self.assertEqual(segment_from_market_cap(200_000), "large_cap")
        self.assertEqual(segment_from_market_cap(500_000_000), "small_cap")

        # Finnhub mcap is in millions
        self.assertEqual(segment_from_finnhub_mcap(None), "unknown")
        self.assertEqual(segment_from_finnhub_mcap(0), "unknown")
        self.assertEqual(segment_from_finnhub_mcap(200_000), "large_cap") # 200,000M = 200B
        self.assertEqual(segment_from_finnhub_mcap(500), "small_cap")     # 500M
        self.assertEqual(segment_from_finnhub_mcap(50), "micro_cap")      # 50M

    def test_segment_from_market(self):
        """Test market-string to segment derivation."""
        self.assertEqual(_segment_from_market("Large Cap SE"), "large_cap")
        self.assertEqual(_segment_from_market("Mid Cap SE"), "mid_cap")
        self.assertEqual(_segment_from_market("Small Cap SE"), "small_cap")
        self.assertEqual(_segment_from_market("First North Sweden"), "micro_cap")
        self.assertEqual(_segment_from_market("Spotlight Stock Market"), "micro_cap")
        self.assertEqual(_segment_from_market(None), "unknown")
        self.assertEqual(_segment_from_market(""), "unknown")

    def test_portfolio_optimizer_with_unknown_segment(self):
        """Portfolio optimizer must handle unknown segments safely without crashing."""
        candidates = [
            {"ticker": "MSFT", "name": "Microsoft", "segment": "large_cap", "sector": "Technology", "master_rank": 78.0, "roe": 0.34, "pe_forward": 25.0, "fcf_yield": 0.025},
            {"ticker": "TSM", "name": "TSMC", "segment": "large_cap", "sector": "Technology", "master_rank": 84.0, "roe": 0.40, "pe_forward": 22.0, "fcf_yield": 0.035},
            {"ticker": "MU", "name": "Micron", "segment": "large_cap", "sector": "Technology", "master_rank": 88.0, "roe": 0.67, "pe_forward": 6.5, "fcf_yield": 0.045},
            {"ticker": "JNJ", "name": "Johnson & Johnson", "segment": "large_cap", "sector": "Healthcare", "master_rank": 70.0, "roe": 0.20, "pe_forward": 15.0, "fcf_yield": 0.055},
            {"ticker": "UNK1", "name": "Unknown Corp 1", "segment": "unknown", "sector": "Technology", "master_rank": 75.0, "roe": 0.28, "pe_forward": 41.0, "fcf_yield": 0.020},
            {"ticker": "UNK2", "name": "Unknown Corp 2", "segment": None, "sector": "Healthcare", "master_rank": 80.0, "roe": 0.25, "pe_forward": 19.0, "fcf_yield": 0.050},
        ]
        res = build_barbell_portfolio(candidates)
        self.assertIn("holdings", res)
        self.assertGreater(len(res["holdings"]), 0)

    def test_stress_lab_with_unknown_segment(self):
        """Stress lab must handle unknown segments without crashing."""
        portfolio = [
            {"ticker": "MSFT", "weight": 0.50, "segment": "large_cap", "sector": "Technology", "pe": 25.0, "gross_margin": 0.68, "beta": 0.95},
            {"ticker": "UNK1", "weight": 0.50, "segment": "unknown", "sector": "Healthcare", "pe": 20.0, "gross_margin": 0.50, "beta": 1.0},
        ]
        res = stress_test_portfolio(portfolio)
        self.assertIn("scenarios", res)
        self.assertIn("RATE_SHOCK_150BPS", res["scenarios"])
        self.assertIn("SMALLCAP_LIQUIDITY_CRUNCH", res["scenarios"])


if __name__ == "__main__":
    unittest.main()
