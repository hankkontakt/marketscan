"""Unit tests for liquidity.py — segment turnover floors, FX conversion, and grades A–F."""
import unittest

from backend_worker.liquidity import (
    compute_liquidity_grade,
    compute_turnover_20d,
    turnover_to_sek,
    is_low_liquidity,
    FX_TO_SEK,
    SEGMENT_FLOORS_SEK,
)


class TestLiquidityEngine(unittest.TestCase):
    def test_fx_to_sek_conversion(self):
        self.assertEqual(turnover_to_sek(100.0, "SEK"), 100.0)
        self.assertEqual(turnover_to_sek(100.0, "USD"), 100.0 * FX_TO_SEK["USD"])
        self.assertEqual(turnover_to_sek(100.0, "EUR"), 100.0 * FX_TO_SEK["EUR"])
        self.assertEqual(turnover_to_sek(100.0, "NOK"), 100.0 * FX_TO_SEK["NOK"])
        self.assertIsNone(turnover_to_sek(None, "USD"))

    def test_unknown_when_turnover_none(self):
        self.assertEqual(compute_liquidity_grade(None, "large_cap"), "unknown")
        self.assertEqual(compute_liquidity_grade(float("nan"), "small_cap"), "unknown")

    def test_large_cap_grades(self):
        # Large cap floor = 20M SEK
        floor = SEGMENT_FLOORS_SEK["large_cap"]  # 20_000_000
        # A: >= 20x floor = 400M
        self.assertEqual(compute_liquidity_grade(450_000_000, "large_cap"), "A")
        # B: >= 5x floor = 100M
        self.assertEqual(compute_liquidity_grade(120_000_000, "large_cap"), "B")
        # C: >= floor = 20M
        self.assertEqual(compute_liquidity_grade(25_000_000, "large_cap"), "C")
        # D: < floor = 20M, >= 0.5x floor = 10M
        self.assertEqual(compute_liquidity_grade(15_000_000, "large_cap"), "D")
        # E: < 0.5x floor = 10M, >= 0.1x floor = 2M
        self.assertEqual(compute_liquidity_grade(5_000_000, "large_cap"), "E")
        # F: < 0.1x floor = 2M
        self.assertEqual(compute_liquidity_grade(1_000_000, "large_cap"), "F")

    def test_small_cap_grades(self):
        # Small cap floor = 2M SEK
        self.assertEqual(compute_liquidity_grade(50_000_000, "small_cap"), "A")  # >= 40M
        self.assertEqual(compute_liquidity_grade(12_000_000, "small_cap"), "B")  # >= 10M
        self.assertEqual(compute_liquidity_grade(2_500_000, "small_cap"), "C")   # >= 2M
        self.assertEqual(compute_liquidity_grade(1_500_000, "small_cap"), "D")   # < 2M
        self.assertEqual(compute_liquidity_grade(800_000, "small_cap"), "E")     # < 1M
        self.assertEqual(compute_liquidity_grade(100_000, "small_cap"), "F")     # < 200k

    def test_micro_cap_grades(self):
        # Micro cap floor = 500k SEK
        self.assertEqual(compute_liquidity_grade(15_000_000, "micro_cap"), "A")  # >= 10M
        self.assertEqual(compute_liquidity_grade(3_000_000, "micro_cap"), "B")   # >= 2.5M
        self.assertEqual(compute_liquidity_grade(600_000, "micro_cap"), "C")     # >= 500k
        self.assertEqual(compute_liquidity_grade(350_000, "micro_cap"), "D")     # < 500k
        self.assertEqual(compute_liquidity_grade(150_000, "micro_cap"), "E")     # < 250k
        self.assertEqual(compute_liquidity_grade(30_000, "micro_cap"), "F")      # < 50k

    def test_penny_stock_and_active_days_guard(self):
        # Price < 1.0 -> F regardless of turnover
        self.assertEqual(compute_liquidity_grade(50_000_000, "small_cap", price=0.85), "F")
        # Active days < 10 -> F
        self.assertEqual(compute_liquidity_grade(50_000_000, "small_cap", active_days=8), "F")

    def test_low_liquidity_flag(self):
        self.assertTrue(is_low_liquidity("F"))
        self.assertTrue(is_low_liquidity("E"))
        self.assertTrue(is_low_liquidity("D"))
        self.assertFalse(is_low_liquidity("C"))
        self.assertFalse(is_low_liquidity("B"))
        self.assertFalse(is_low_liquidity("A"))
        self.assertFalse(is_low_liquidity("unknown"))
        self.assertFalse(is_low_liquidity(None))

    def test_compute_turnover_20d(self):
        closes = [10.0] * 20
        volumes = [1000.0] * 20  # 10 * 1000 = 10,000 native
        med_sek, active = compute_turnover_20d(closes, volumes, "SEK")
        self.assertEqual(active, 20)
        self.assertEqual(med_sek, 10000.0)


if __name__ == "__main__":
    unittest.main()