"""Tester för news_bias.py — compute_news_bias (ren funktion, ingen DB)."""
import unittest
from datetime import datetime, timedelta

from backend_worker.news_bias import compute_news_bias


def _ev(bearing, confidence, published_at, direction=None):
    return {
        "ticker": "TEST.ST",
        "bearing": bearing,
        "confidence": confidence,
        "direction": direction,
        "published_at": published_at,
    }


class TestComputeNewsBias(unittest.TestCase):
    NOW = datetime(2026, 8, 29, 12, 0, 0)

    def test_empty_list_returns_none(self):
        self.assertIsNone(compute_news_bias([], self.NOW))

    def test_all_negative_bias_below_half(self):
        # 3 negativa (conf 0.8/0.5/0.3): weighted = -1.6, conf_sum = 1.6 → -1.0
        events = [
            _ev("negative", 0.8, self.NOW - timedelta(hours=1)),
            _ev("negative", 0.5, self.NOW - timedelta(hours=2)),
            _ev("negative", 0.3, self.NOW - timedelta(hours=3)),
        ]
        bias = compute_news_bias(events, self.NOW)
        self.assertIsNotNone(bias)
        self.assertLess(bias["news_bias"], -0.5)
        self.assertEqual(bias["news_bias_n"], 3)
        self.assertEqual(bias["ticker"], "TEST.ST")

    def test_mixed_pos_neg_within_unit(self):
        # +0.8 och -0.5 → weighted 0.3 / conf_sum 1.3 ≈ 0.23 → |bias| < 1
        events = [
            _ev("positive", 0.8, self.NOW - timedelta(hours=1)),
            _ev("negative", 0.5, self.NOW - timedelta(hours=2)),
        ]
        bias = compute_news_bias(events, self.NOW)
        self.assertIsNotNone(bias)
        self.assertLess(abs(bias["news_bias"]), 1.0)

    def test_neutral_plus_positive_is_positive(self):
        # neutral (0.0) + positive (0.7) → weighted 0.7 / conf_sum 1.6 ≈ 0.44 > 0
        events = [
            _ev("neutral", 0.9, self.NOW - timedelta(hours=1)),
            _ev("positive", 0.7, self.NOW - timedelta(hours=2)),
        ]
        bias = compute_news_bias(events, self.NOW)
        self.assertIsNotNone(bias)
        self.assertGreater(bias["news_bias"], 0.0)

    def test_older_than_window_returns_none(self):
        # 73h gammal → utanför 72h-fönstret → None
        events = [
            _ev("positive", 0.9, self.NOW - timedelta(hours=73)),
        ]
        self.assertIsNone(compute_news_bias(events, self.NOW))


if __name__ == "__main__":
    unittest.main()