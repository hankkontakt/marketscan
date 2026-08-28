"""Tester för fi_insider_bulk.py ISIN→ticker-mappningskedjan.

Rent uppspelat (ingen DB, inga externa anrop): SEED_TICKERS →
company_profiles.isin → universe_registry.isin → isin_symbol_cache.json → None.

Kärnan testas via den RENA hjälpfunktionen extract_map_isin (in-memory-dicts);
_map_isin_to_ticker testas som DB-wiring (fake cursor).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend_worker import fi_insider_bulk
from backend_worker.fi_insider_bulk import _map_isin_to_ticker, extract_map_isin


class TestExtractMapIsin(unittest.TestCase):
    """Ren kedja: seed_map → profiles_set → registry_set → cache → None."""

    def test_isin_i_seed(self):
        # ISIN i SEED_TICKERS → ticker direkt (även om övriga källor är tomma).
        self.assertEqual(
            extract_map_isin("SE0000000001", {"SE0000000001": "SEED.ST"}, {}, {}, None),
            "SEED.ST",
        )

    def test_isin_endast_i_universe_registry(self):
        # ISIN saknas i company_profiles men finns i universe_registry → ticker.
        self.assertEqual(
            extract_map_isin("SE0000000002", {}, {}, {"SE0000000002": "REG.ST"}, None),
            "REG.ST",
        )

    def test_isin_i_company_profiles(self):
        # Befintlig källa först i DB-kedjan (company_profiles vinner över registry).
        self.assertEqual(
            extract_map_isin(
                "SE0000000003", {},
                {"SE0000000003": "CP.ST"}, {"SE0000000003": "REG.ST"}, None,
            ),
            "CP.ST",
        )

    def test_isin_i_ingenstans(self):
        # Ingenstans → None (kostar aldrig Finnhub/yfinance per transaktion).
        self.assertIsNone(extract_map_isin("SE0000000004", {}, {}, {}, None))

    def test_isin_endast_i_cache(self):
        # Nyligen-cachad mappning (isin_symbol_cache.json-innehåll) som sista steg.
        cache = {"SE0000000005": {"symbol": "CACHE.ST", "ts": "2026-08-28"}}
        self.assertEqual(extract_map_isin("SE0000000005", {}, {}, {}, cache), "CACHE.ST")

    def test_cache_miss_med_symbol_null(self):
        # Cache-träff med symbol=None (miss) → None, inte falsk ticker.
        cache = {"SE0000000006": {"symbol": None, "ts": "2026-08-28"}}
        self.assertIsNone(extract_map_isin("SE0000000006", {}, {}, {}, cache))

    def test_lowercase_isin_uppercasas(self):
        # ISIN normaliseras till versaler innan uppslag.
        self.assertEqual(
            extract_map_isin("se0000000001", {"SE0000000001": "SEED.ST"}, {}, {}, None),
            "SEED.ST",
        )

    def test_tom_isin(self):
        self.assertIsNone(extract_map_isin("", {}, {}, {}, None))
        self.assertIsNone(extract_map_isin(None, {}, {}, {}, None))


class _FakeCursor:
    """Cursor som svarar per tabell (company_profiles / universe_registry)."""

    def __init__(self, company_ticker=None, registry_ticker=None):
        self.company_ticker = company_ticker
        self.registry_ticker = registry_ticker
        self.last_query = ""

    def execute(self, sql, params=None):
        self.last_query = sql
        return self

    def fetchone(self):
        if "company_profiles" in self.last_query:
            return (self.company_ticker,) if self.company_ticker else None
        if "universe_registry" in self.last_query:
            return (self.registry_ticker,) if self.registry_ticker else None
        return None


class _FakeConn:
    def __init__(self, company_ticker=None, registry_ticker=None):
        self._cursor = _FakeCursor(company_ticker, registry_ticker)

    def cursor(self):
        return self._cursor


class TestMapIsinToTicker(unittest.TestCase):
    """DB-wiring: _map_isin_to_ticker bygger in-memory-dicts → extract_map_isin."""

    def test_isin_i_seed(self):
        # ISIN i SEED_TICKERS → ticker direkt (även om DB saknar raden).
        with mock.patch.object(fi_insider_bulk, "SEED_TICKERS", {"SE0000000001": "SEED.ST"}):
            conn = _FakeConn()  # inget i company_profiles/universe_registry
            self.assertEqual(_map_isin_to_ticker("SE0000000001", conn), "SEED.ST")

    def test_isin_endast_i_universe_registry(self):
        # ISIN saknas i company_profiles men finns i universe_registry → ticker.
        conn = _FakeConn(company_ticker=None, registry_ticker="REG.ST")
        self.assertEqual(_map_isin_to_ticker("SE0000000002", conn), "REG.ST")

    def test_isin_i_company_profiles(self):
        # Befintlig källa först i DB-kedjan (company_profiles vinner över registry).
        conn = _FakeConn(company_ticker="CP.ST", registry_ticker="REG.ST")
        self.assertEqual(_map_isin_to_ticker("SE0000000003", conn), "CP.ST")

    def test_isin_i_ingenstans(self):
        # Ingenstans → None (kostar aldrig Finnhub/yfinance per transaktion).
        conn = _FakeConn()
        with mock.patch.object(fi_insider_bulk, "_load_isin_symbol_cache", return_value={}):
            self.assertIsNone(_map_isin_to_ticker("SE0000000004", conn))

    def test_isin_endast_i_cache(self):
        # Nyligen-cachad mappning (isin_symbol_cache.json) som sista steg.
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "isin_symbol_cache.json"
            cache_path.write_text(
                json.dumps({"SE0000000005": {"symbol": "CACHE.ST", "ts": "2026-08-28"}}),
                encoding="utf-8",
            )
            with mock.patch.object(fi_insider_bulk, "ISIN_SYMBOL_CACHE_PATH", cache_path):
                conn = _FakeConn()
                self.assertEqual(_map_isin_to_ticker("SE0000000005", conn), "CACHE.ST")

    def test_tom_isin(self):
        self.assertIsNone(_map_isin_to_ticker("", _FakeConn()))
        self.assertIsNone(_map_isin_to_ticker(None, _FakeConn()))


if __name__ == "__main__":
    unittest.main()