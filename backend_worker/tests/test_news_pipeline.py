"""Tester för nyhetskedjan — surge-beräkning, bearing-normalisering, offset-loop.

Täcker news_discovery.py, news_classifier.py och news_events.py (ingen DB).
"""
import unittest
from unittest import mock

from backend_worker.news_classifier import (clamp_confidence, normalize_bearing)
from backend_worker.news_discovery import compute_surge
from backend_worker.news_events import fetch_nasdaq


class TestComputeSurge(unittest.TestCase):
    """FIX 1: surge = now_hits / max(baseline_per_hour * window_hours, 1)."""

    def test_3_in_30d_1_in_48h(self):
        # baseline_per_hour = 3/720 = 0.00417; förväntat i 48h = 0.2
        # → max(0.2, 1) = 1 → surge = 1/1 = 1.0
        self.assertEqual(compute_surge(3, 1), 1.0)

    def test_30_in_30d_3_in_48h(self):
        # förväntat i 48h = 30/720*48 = 2.0 → surge = 3/2 = 1.5
        self.assertEqual(compute_surge(30, 3), 1.5)

    def test_zero_hits_returns_none(self):
        # inaktiv ticker → radarn ska inte visa surge
        self.assertIsNone(compute_surge(30, 0))

    def test_cold_start_guard(self):
        # baslinjen < 3 observationer → None (en enda nyhet får inte blåsa upp)
        self.assertIsNone(compute_surge(2, 1))

    def test_custom_window(self):
        # 24h-fönster: förväntat = 30/720*24 = 1.0 → surge = 2/1 = 2.0
        self.assertEqual(compute_surge(30, 2, window_hours=24), 2.0)


class TestNormalizeBearing(unittest.TestCase):
    """FIX 4: ogiltig bearing → neutral."""

    def test_valid_lowercased(self):
        self.assertEqual(normalize_bearing("Positive"), "positive")
        self.assertEqual(normalize_bearing("NEGATIVE"), "negative")
        self.assertEqual(normalize_bearing("Neutral"), "neutral")
        self.assertEqual(normalize_bearing("Conditional"), "conditional")

    def test_garbage_to_neutral(self):
        self.assertEqual(normalize_bearing("bullish"), "neutral")
        self.assertEqual(normalize_bearing(""), "neutral")
        self.assertEqual(normalize_bearing(None), "neutral")

    def test_truncated_to_24(self):
        # långt svar klipps till 24 tecken innan validering
        self.assertEqual(normalize_bearing("x" * 40), "neutral")


class TestClampConfidence(unittest.TestCase):
    """FIX 3: 0.0 får vara 0.0; None → 0.3; tak 0.85."""

    def test_zero_stays_zero(self):
        self.assertEqual(clamp_confidence(0.0), 0.0)

    def test_none_defaults_to_03(self):
        self.assertEqual(clamp_confidence(None), 0.3)

    def test_cap_at_085(self):
        self.assertEqual(clamp_confidence(0.99), 0.85)

    def test_normal_value_passthrough(self):
        self.assertEqual(clamp_confidence(0.4), 0.4)


class TestFetchNasdaqPagination(unittest.TestCase):
    """FIX 5: start-paginering (API:et ignorerar 'offset')."""

    def test_offset_loop_stops_when_short_page(self):
        seen_starts = []

        def fake_get(url, params=None, timeout=None):
            start = params.get("start", 0)
            limit = params.get("limit", 200)
            seen_starts.append(start)
            n = limit if start < 2 * limit else 3  # sista sidan kort
            resp = mock.Mock()
            resp.json.return_value = {
                "results": {"item": [{"disclosureId": start + i} for i in range(n)]}
            }
            return resp

        with mock.patch("backend_worker.news_events.requests.get",
                        side_effect=fake_get):
            items = fetch_nasdaq("SSE", limit=200)

        self.assertEqual(seen_starts, [0, 200, 400])
        self.assertEqual(len(items), 200 + 200 + 3)

    def test_stops_early_on_short_first_page(self):
        def fake_get(url, params=None, timeout=None):
            resp = mock.Mock()
            resp.json.return_value = {"results": {"item": [{"disclosureId": 1}]}}
            return resp

        with mock.patch("backend_worker.news_events.requests.get",
                        side_effect=fake_get):
            items = fetch_nasdaq("SSE", limit=200)

        self.assertEqual(len(items), 1)

    def test_dict_item_fallback(self):
        # API:et kan svara med ett enda dict i stället för lista
        def fake_get(url, params=None, timeout=None):
            resp = mock.Mock()
            resp.json.return_value = {"results": {"item": {"disclosureId": 7}}}
            return resp

        with mock.patch("backend_worker.news_events.requests.get",
                        side_effect=fake_get):
            items = fetch_nasdaq("SSE", limit=200)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["disclosureId"], 7)


if __name__ == "__main__":
    unittest.main()