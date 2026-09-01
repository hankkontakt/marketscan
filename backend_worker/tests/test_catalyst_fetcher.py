"""Unit tests for catalyst_fetcher.py — confidence weighting, earnings dominance, next event."""
import unittest
from datetime import date, timedelta

from backend_worker.catalyst_fetcher import (
    catalyst_z, catalyst_boost, next_event, days_until
)


class TestCatalystFetcher(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 9, 1)

    def test_days_until(self):
        target = self.today + timedelta(days=10)
        self.assertEqual(days_until(target, self.today), 10)

    def test_earnings_high_confidence_dominates_dividend_low(self):
        event_earnings = {
            "ticker": "MSFT",
            "event_type": "earnings",
            "days_until": 10,
            "confidence": "high",
        }
        event_dividend = {
            "ticker": "MSFT",
            "event_type": "dividend_ex",
            "days_until": 10,
            "confidence": "low",
        }
        # Earnings alone
        z_earn = catalyst_z([event_earnings], self.today)
        # Dividend alone
        z_div = catalyst_z([event_dividend], self.today)
        # Both combined -> earnings should dominate
        z_both = catalyst_z([event_earnings, event_dividend], self.today)

        self.assertIsNotNone(z_earn)
        self.assertIsNotNone(z_div)
        self.assertAlmostEqual(z_earn, (45 - 10) / 45.0 * 100.0 * 1.0, places=2)
        self.assertAlmostEqual(z_div, (45 - 10) / 45.0 * 100.0 * 0.25, places=2)
        self.assertGreater(z_earn, z_div)
        self.assertEqual(z_both, z_earn)

    def test_catalyst_boost(self):
        event = {
            "ticker": "MSFT",
            "event_type": "earnings",
            "days_until": 0,
            "confidence": "high",
        }
        # 0 days, high conf -> catalyst_z = 100 -> boost = +5.0
        boost = catalyst_boost([event], self.today)
        self.assertAlmostEqual(boost, 5.0, places=2)

    def test_empty_or_past_events_return_none(self):
        self.assertIsNone(catalyst_z([], self.today))
        past_event = {
            "ticker": "MSFT",
            "event_type": "earnings",
            "days_until": -5,
            "confidence": "high",
        }
        self.assertIsNone(catalyst_z([past_event], self.today))

    def test_next_event_picks_earliest(self):
        ev1 = {"event_type": "dividend_ex", "days_until": 20}
        ev2 = {"event_type": "earnings", "days_until": 5}
        ev3 = {"event_type": "earnings", "days_until": -2}
        best = next_event([ev1, ev2, ev3])
        self.assertEqual(best["days_until"], 5)
        self.assertEqual(best["event_type"], "earnings")


if __name__ == "__main__":
    unittest.main()