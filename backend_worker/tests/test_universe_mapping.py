"""Tester för universe_mapping.py ISIN→ticker-seed-mappning.

Rent uppspelat (ingen DB, inga externa anrop): SEED_TICKERS →
seed_ticker_for_isin (pure) + _map_isin_to_ticker (DB-wiring, fake cursor).

Verifierat 2026-08-28 med yfinance: "TAGM-B.ST" resolvar (TagMaster AB ser. B),
"TAGM B.ST" gör det INTE; "NCAB.ST" resolvar (NCAB Group AB).
"""
import unittest
from unittest import mock

from backend_worker.universe_mapping import (
    SEED_TICKERS, _map_isin_to_ticker, seed_ticker_for_isin,
)


class TestSeedTickerForIsin(unittest.TestCase):
    """Pure seed-uppslag — inga DB- eller nätverksberoenden."""

    def test_ncab_isin_maps(self):
        self.assertEqual(seed_ticker_for_isin("SE0015671995"), "NCAB.ST")

    def test_tagmaster_isin_maps(self):
        # TAGM-B.ST (bindestreck) — "TAGM B.ST" resolvar inte hos Yahoo.
        self.assertEqual(seed_ticker_for_isin("SE0015950399"), "TAGM-B.ST")

    def test_lowercase_isin_uppercasas(self):
        self.assertEqual(seed_ticker_for_isin("se0015671995"), "NCAB.ST")

    def test_okand_isin_returns_none(self):
        self.assertIsNone(seed_ticker_for_isin("SE0000000000"))

    def test_tom_isin_returns_none(self):
        self.assertIsNone(seed_ticker_for_isin(""))
        self.assertIsNone(seed_ticker_for_isin(None))

    def test_seed_dict_contains_both_entries(self):
        self.assertEqual(SEED_TICKERS["SE0015671995"], "NCAB.ST")
        self.assertEqual(SEED_TICKERS["SE0015950399"], "TAGM-B.ST")


class _FakeCursor:
    """Cursor som aldrig anropas — seed-vägen returnerar före DB-anrop."""

    def __init__(self):
        self.called = False

    def execute(self, sql, params=None):
        self.called = True
        return self

    def fetchone(self):
        return None


class TestMapIsinToTickerSeedPath(unittest.TestCase):
    """DB-wiring: seed-vägen i _map_isin_to_ticker vinner över DB-källorna."""

    def test_seed_isin_returns_ticker_without_db(self):
        cur = _FakeCursor()
        self.assertEqual(_map_isin_to_ticker(cur, "SE0015671995"), "NCAB.ST")
        self.assertFalse(cur.called)  # seed-vägen gör inga DB-anrop

    def test_seed_isin_tagmaster(self):
        cur = _FakeCursor()
        self.assertEqual(_map_isin_to_ticker(cur, "SE0015950399"), "TAGM-B.ST")

    def test_seed_isin_lowercase(self):
        cur = _FakeCursor()
        self.assertEqual(_map_isin_to_ticker(cur, "se0015671995"), "NCAB.ST")

    def test_unknown_isin_falls_through_to_db(self):
        # Okänd ISIN → seed ger None → DB-vägen anropas (company_profiles).
        cur = _FakeCursor()
        with mock.patch("backend_worker.universe_mapping.lookup_finnhub_isin",
                        return_value=None), \
             mock.patch("backend_worker.universe_mapping.lookup_isin_via_yfinance",
                        return_value=None):
            self.assertIsNone(_map_isin_to_ticker(cur, "SE0000000000"))
        self.assertTrue(cur.called)

    def test_tom_isin(self):
        self.assertIsNone(_map_isin_to_ticker(_FakeCursor(), ""))
        self.assertIsNone(_map_isin_to_ticker(_FakeCursor(), None))


if __name__ == "__main__":
    unittest.main()