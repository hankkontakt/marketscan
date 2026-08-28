"""Tester för news_common.py — namnmatchning, normalisering, event-IDs."""
import unittest

from backend_worker.news_common import norm, event_id, match_ticker


class TestNorm(unittest.TestCase):
    def test_names(self):
        # åäö behålls (svenska företagsnamn matchar bäst med åäö)
        self.assertEqual(norm("AB Säkerhetsgruppen (publ)"), "säkerhetsgruppen")
        self.assertEqual(norm("BioGaia AB"), "biogaia")
        self.assertIn("nanexa", norm("Nanexa AB (publ)"))

    def test_ascii(self):
        self.assertEqual(norm("H&M Group"), "h m")


class TestEventId(unittest.TestCase):
    def test_stable(self):
        self.assertEqual(event_id("gnews", "https://x.se/1"),
                         event_id("gnews", "https://x.se/1"))
        self.assertNotEqual(event_id("gnews", "https://x.se/1"),
                            event_id("gnews", "https://x.se/2"))


class TestMatchTicker(unittest.TestCase):
    REG = {
        "biogaia": ("BIOG-B.ST", "BioGaia AB"),
        "siverssemiconductors": ("SIVE.ST", "Sivers Semiconductors AB"),
        "nanexa": ("NANEXA.ST", "Nanexa AB"),
    }

    def test_norm_name_match(self):
        self.assertEqual(
            match_ticker("Sivers Semiconductors får order värd 77 miljoner", self.REG),
            "SIVE.ST")

    def test_ticker_base_fallback(self):
        # reg-rad som bara har ticker som 'namn' (X- fall)
        reg = {"sivedummy": ("SIVE.ST", "SIVE.ST")}
        self.assertEqual(
            match_ticker("Sivers säkrar stor order", reg), "SIVE.ST")

    def test_no_false_positive_passiv(self):
        # 'sive' får INTE matcha 'passiv' — ordgräns gäller
        reg = {"sivedummy": ("SIVE.ST", "SIVE.ST")}
        self.assertIsNone(match_ticker("Bolaget redovisar passiv post", reg))


if __name__ == "__main__":
    unittest.main()
