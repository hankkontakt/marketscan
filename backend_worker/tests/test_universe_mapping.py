"""Tester för universe_mapping.py ISIN→ticker-seed-mappning.

Rent uppspelat (ingen DB, inga externa anrop): SEED_TICKERS →
seed_ticker_for_isin (pure) + _map_isin_to_ticker (DB-wiring, fake cursor).

Verifierat 2026-08-28 med yfinance: "TAGM-B.ST" resolvar (TagMaster AB ser. B),
"TAGM B.ST" gör det INTE; "NCAB.ST" resolvar (NCAB Group AB).
"""
import unittest
from datetime import date
from unittest import mock

from backend_worker.universe_mapping import (
    SEED_TICKERS, _map_isin_to_ticker, probe_yahoo_ticker,
    run_delisting_detector, seed_from_existing, seed_ticker_for_isin,
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


class _FakeProbeTicker:
    """Fake yf.Ticker-resultat: styr history() per test."""

    def __init__(self, history_result=None, history_error=None):
        self._history_result = history_result
        self._history_error = history_error

    def history(self, period="5d"):
        if self._history_error is not None:
            raise self._history_error
        return self._history_result


class TestProbeYahooTicker(unittest.TestCase):
    """FIX 1: True (data) / False (tom historik) / None (undantag, ingen cache)."""

    def test_exception_returns_none_without_cache_write(self):
        cache = {}
        with mock.patch("backend_worker.universe_mapping._save_probe_cache") as save, \
             mock.patch("yfinance.Ticker", side_effect=Exception("timeout")):
            result = probe_yahoo_ticker("FOO.ST", cache)
        self.assertIsNone(result)
        self.assertEqual(cache, {})          # None skrivs aldrig till cache
        save.assert_not_called()

    def test_empty_history_returns_false(self):
        cache = {}
        with mock.patch("backend_worker.universe_mapping._save_probe_cache") as save, \
             mock.patch("yfinance.Ticker",
                        return_value=_FakeProbeTicker(history_result=mock.Mock(empty=True))):
            result = probe_yahoo_ticker("FOO.ST", cache)
        self.assertIs(result, False)
        self.assertIs(cache["FOO.ST"]["alive"], False)
        save.assert_called_once()

    def test_data_returns_true(self):
        cache = {}
        with mock.patch("backend_worker.universe_mapping._save_probe_cache") as save, \
             mock.patch("yfinance.Ticker",
                        return_value=_FakeProbeTicker(history_result=mock.Mock(empty=False))):
            result = probe_yahoo_ticker("FOO.ST", cache)
        self.assertIs(result, True)
        self.assertIs(cache["FOO.ST"]["alive"], True)
        save.assert_called_once()

    def test_fresh_cache_entry_skips_yf_call(self):
        cache = {"FOO.ST": {"alive": False, "probed_at": date.today().isoformat()}}
        with mock.patch("backend_worker.universe_mapping._save_probe_cache") as save, \
             mock.patch("yfinance.Ticker", side_effect=AssertionError("ska inte anropas")):
            result = probe_yahoo_ticker("FOO.ST", cache)
        self.assertIs(result, False)
        save.assert_not_called()


class _FakeDetectorConn:
    def __init__(self, rows):
        self.cur = _FakeDetectorCursor(rows)
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class _FakeDetectorCursor:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def execute(self, sql, params=None):
        self.updates.append((sql, params))
        return self

    def fetchall(self):
        return self.rows


class TestRunDelistingDetector(unittest.TestCase):
    """FIX 1: verify ENDAST för False; listed kvar för None (probe_unknown)."""

    def _run(self, rows, probe_results):
        conn = _FakeDetectorConn(rows)
        with mock.patch("backend_worker.universe_mapping._connect", return_value=conn), \
             mock.patch("backend_worker.universe_mapping._load_probe_cache", return_value={}), \
             mock.patch("backend_worker.universe_mapping._save_probe_cache"), \
             mock.patch("backend_worker.universe_mapping.probe_yahoo_ticker",
                        side_effect=lambda ticker, cache: probe_results[ticker]):
            stats = run_delisting_detector()
        return stats, conn

    def test_false_probe_moves_listed_to_verify(self):
        rows = [("ISIN1", "AAA.ST", "listed", None)]
        stats, conn = self._run(rows, {"AAA.ST": False})
        self.assertEqual(stats["to_verify"], 1)
        self.assertEqual(stats["probe_unknown"], 0)
        self.assertTrue(any("status='verify'" in sql for sql, _ in conn.cur.updates))

    def test_none_probe_keeps_listed_and_counts_unknown(self):
        rows = [("ISIN1", "AAA.ST", "listed", None)]
        stats, conn = self._run(rows, {"AAA.ST": None})
        self.assertEqual(stats["to_verify"], 0)
        self.assertEqual(stats["probe_unknown"], 1)
        # ingen statusändring alls (bara den inledande SELECT:en)
        self.assertFalse(any(sql.strip().upper().startswith("UPDATE")
                             for sql, _ in conn.cur.updates))

    def test_true_probe_restores_listed(self):
        rows = [("ISIN1", "AAA.ST", "verify", None)]
        stats, conn = self._run(rows, {"AAA.ST": True})
        self.assertEqual(stats["listed_ok"], 1)
        self.assertTrue(any("status='listed'" in sql for sql, _ in conn.cur.updates))


class _FakeSeedCursor:
    """Fake cursor för seed_from_existing: styr fetchall per tabell + guard-träff."""

    def __init__(self, fetchall_by_table=None, guard_hit=False):
        self.fetchall_by_table = fetchall_by_table or {}
        self.guard_hit = guard_hit
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        return self

    def fetchall(self):
        sql = self.executed[-1][0]
        for table, rows in self.fetchall_by_table.items():
            if table in sql:
                return rows
        return []

    def fetchone(self):
        return ("hit",) if self.guard_hit else None


class TestSeedFromExistingDuplicateGuard(unittest.TestCase):
    """FIX 3: kandidat skippas när tickern redan finns med riktig ISIN."""

    def test_ticker_with_real_registry_row_is_skipped(self):
        cur = _FakeSeedCursor(
            fetchall_by_table={
                "company_profiles": [("AAA.ST", "SE0000000001")],
                "scan_results": [],
                "smallcap_results": [],
            },
            guard_hit=True,
        )
        rows = seed_from_existing(cur)
        self.assertEqual(rows, [])             # alla kandidater skippade
        # guard-frågan kördes mot universe_registry med kandidatens ticker
        guard_calls = [p for sql, p in cur.executed
                       if "universe_registry" in sql and "NOT LIKE" in sql]
        self.assertTrue(guard_calls)
        self.assertEqual(guard_calls[0][0], "AAA.ST")

    def test_ticker_without_registry_row_is_seeded(self):
        cur = _FakeSeedCursor(
            fetchall_by_table={
                "company_profiles": [("AAA.ST", "SE0000000001")],
                "scan_results": [],
                "smallcap_results": [],
            },
            guard_hit=False,
        )
        rows = seed_from_existing(cur)
        tickers = [r["ticker"] for r in rows]
        self.assertIn("AAA.ST", tickers)       # kandidaten seedas
        self.assertEqual(rows[0]["isin"], "SE0000000001")


if __name__ == "__main__":
    unittest.main()