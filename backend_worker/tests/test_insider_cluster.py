"""Tester för insider_cluster.py — dedupe_trades (FI/Finnhub-dubbelräkning),
mcap-fallback (score=None), cutoff vid midnatt (samma-dags-trades inkluderas).

Inga DB-beroenden — testar PURE-funktionen dedupe_trades + calculate_clusters
med en stub-conn som serverar syntetiska DataFrames.
"""
import unittest
import warnings
from datetime import datetime, timedelta

import pandas as pd

from backend_worker.insider_cluster import calculate_clusters, dedupe_trades


def _run_clusters(conn, lookback_days=30):
    """Kör calculate_clusters med pandas-varningen om stub-conn tystad."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
        return calculate_clusters(conn, lookback_days=lookback_days)


class _FakeCursor:
    """Serverar en förvald DataFrame per SQL-fråga (matchad på innehåll)."""

    def __init__(self, tables):
        self.tables = tables
        self.description = None
        self._rows = []

    def execute(self, sql, params=None):
        if "scan_results" in sql:
            df = self.tables["mcap"]
        elif "trade_date >=" in sql:
            df = self.tables["buys_90d"]
        else:
            df = self.tables["history"]
        self.description = [(c, None, None, None, None, None, None) for c in df.columns]
        self._rows = [tuple(r) for r in df.itertuples(index=False)]
        return self

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _FakeConn:
    def __init__(self, tables):
        self.tables = tables

    def cursor(self):
        return _FakeCursor(self.tables)


def _make_conn(buys, history=None, mcap=None):
    """Stub-conn med syntetiska DataFrames för calculate_clusters."""
    return _FakeConn({
        "buys_90d": buys,
        "history": history if history is not None else buys,
        "mcap": mcap if mcap is not None else pd.DataFrame({"ticker": [], "market_cap": []}),
    })


class TestDedupeTrades(unittest.TestCase):
    """Pure-funktion: samma transaktion från två källor → en rad."""

    def test_two_sources_same_volume_deduped(self):
        # FI-format ("Andersson, Lars") + Finnhub-format ("Lars Andersson"),
        # samma dag, samma volym → samma transaktion → 1 rad.
        rows = pd.DataFrame([
            {"ticker": "ERIC-B.ST", "name": "Andersson, Lars", "role": "VD",
             "shares": 20000.0, "price": 100.0, "amount": 2000000.0,
             "trade_date": "2026-08-25", "type": "buy"},
            {"ticker": "ERIC-B.ST", "name": "Lars Andersson", "role": "CEO",
             "shares": 20000.0, "price": 100.0, "amount": 2000000.0,
             "trade_date": "2026-08-25", "type": "buy"},
        ])
        out = dedupe_trades(rows)
        self.assertEqual(len(out), 1)

    def test_different_volumes_kept(self):
        rows = pd.DataFrame([
            {"ticker": "A.ST", "name": "X", "shares": 1000.0,
             "trade_date": "2026-08-25", "type": "buy"},
            {"ticker": "A.ST", "name": "Y", "shares": 2000.0,
             "trade_date": "2026-08-25", "type": "buy"},
        ])
        out = dedupe_trades(rows)
        self.assertEqual(len(out), 2)

    def test_rounding_groups_near_identical_volumes(self):
        # ROUND(shares) i nyckeln: 1000.4 och 999.6 → båda 1000 → samma grupp.
        rows = pd.DataFrame([
            {"ticker": "A.ST", "name": "X", "shares": 1000.4,
             "trade_date": "2026-08-25", "type": "buy"},
            {"ticker": "A.ST", "name": "Y", "shares": 999.6,
             "trade_date": "2026-08-25", "type": "buy"},
        ])
        out = dedupe_trades(rows)
        self.assertEqual(len(out), 1)

    def test_keeps_most_informative_row(self):
        rows = pd.DataFrame([
            {"ticker": "A.ST", "name": "X", "role": None, "price": None, "amount": None,
             "shares": 1000.0, "trade_date": "2026-08-25", "type": "buy"},
            {"ticker": "A.ST", "name": "X", "role": "VD", "price": 100.0, "amount": 100000.0,
             "shares": 1000.0, "trade_date": "2026-08-25", "type": "buy"},
        ])
        out = dedupe_trades(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["role"], "VD")

    def test_empty_input(self):
        out = dedupe_trades(pd.DataFrame())
        self.assertTrue(out.empty)


class TestMcapMissing(unittest.TestCase):
    """Saknad market_cap → cluster_score None (ingen mcap=1-fallback-inflation)."""

    def _buys(self, cutoff_date):
        return pd.DataFrame([
            {"ticker": "NO_MCAP.ST", "name": "Anna Andersson", "role": "VD",
             "shares": 1000.0, "price": 100.0, "amount": 100000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "NO_MCAP.ST", "name": "Bengt Berg", "role": "CFO",
             "shares": 2000.0, "price": 100.0, "amount": 200000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "NO_MCAP.ST", "name": "Cecilia Ceder", "role": "Styrelseledamot",
             "shares": 3000.0, "price": 100.0, "amount": 300000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "HAS_MCAP.ST", "name": "David Dahl", "role": "VD",
             "shares": 1000.0, "price": 100.0, "amount": 100000.0,
             "trade_date": cutoff_date, "type": "buy"},
        ])

    def test_missing_mcap_gives_none_score(self):
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        buys = self._buys(cutoff_date)
        mcap = pd.DataFrame({"ticker": ["HAS_MCAP.ST"], "market_cap": [1_000_000_000.0]})
        out = _run_clusters(_make_conn(buys, mcap=mcap))

        row_nomcap = out.loc[out["ticker"] == "NO_MCAP.ST"].iloc[0]
        row_hasmcap = out.loc[out["ticker"] == "HAS_MCAP.ST"].iloc[0]

        # Ingen mcap → score None (inte artificiellt hög via mcap=1-fallback)
        self.assertIsNone(row_nomcap["cluster_score"])
        self.assertIsNotNone(row_hasmcap["cluster_score"])
        self.assertGreater(row_hasmcap["cluster_score"], 0)

        # is_cluster har ingen score-tröskel — bara unika köpare ≥ 3
        self.assertTrue(bool(row_nomcap["is_cluster"]))
        self.assertFalse(bool(row_hasmcap["is_cluster"]))

    def test_zero_mcap_treated_as_missing(self):
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        buys = self._buys(cutoff_date)
        mcap = pd.DataFrame({"ticker": ["NO_MCAP.ST"], "market_cap": [0.0]})
        out = _run_clusters(_make_conn(buys, mcap=mcap))
        row = out.loc[out["ticker"] == "NO_MCAP.ST"].iloc[0]
        self.assertIsNone(row["cluster_score"])


class TestCutoffSameDay(unittest.TestCase):
    """Cutoff vid midnatt: trades på gränsdagen ska INGÅ i 30d-fönstret."""

    def test_boundary_day_trades_included(self):
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        buys = pd.DataFrame([
            {"ticker": "A.ST", "name": "Anna Andersson", "role": "VD",
             "shares": 1000.0, "price": 100.0, "amount": 100000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "A.ST", "name": "Bengt Berg", "role": "CFO",
             "shares": 2000.0, "price": 100.0, "amount": 200000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "A.ST", "name": "Cecilia Ceder", "role": "Styrelseledamot",
             "shares": 3000.0, "price": 100.0, "amount": 300000.0,
             "trade_date": cutoff_date, "type": "buy"},
        ])
        mcap = pd.DataFrame({"ticker": ["A.ST"], "market_cap": [1_000_000_000.0]})
        out = _run_clusters(_make_conn(buys, mcap=mcap))

        self.assertFalse(out.empty)
        self.assertIn("A.ST", set(out["ticker"]))
        self.assertEqual(int(out.loc[out["ticker"] == "A.ST", "unique_buyers_30d"].iloc[0]), 3)


class TestPipelineDedupe(unittest.TestCase):
    """Dubbelräkning FI/Finnhub i hela calculate_clusters-flödet."""

    def test_duplicate_rows_not_double_counted(self):
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        buys = pd.DataFrame([
            {"ticker": "DUP.ST", "name": "Andersson, Lars", "role": "VD",
             "shares": 20000.0, "price": 100.0, "amount": 2000000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "DUP.ST", "name": "Lars Andersson", "role": "CEO",
             "shares": 20000.0, "price": 100.0, "amount": 2000000.0,
             "trade_date": cutoff_date, "type": "buy"},
            {"ticker": "DUP.ST", "name": "Erik Ek", "role": "Styrelseledamot",
             "shares": 5000.0, "price": 100.0, "amount": 500000.0,
             "trade_date": cutoff_date, "type": "buy"},
        ])
        mcap = pd.DataFrame({"ticker": ["DUP.ST"], "market_cap": [1_000_000_000.0]})
        out = _run_clusters(_make_conn(buys, mcap=mcap))

        row = out.loc[out["ticker"] == "DUP.ST"].iloc[0]
        # 2 unika köpare (inte 3) — samma transaktion från två källor räknas en gång
        self.assertEqual(int(row["unique_buyers_30d"]), 2)
        self.assertEqual(float(row["total_buy_amount_30d"]), 2_500_000.0)


if __name__ == "__main__":
    unittest.main()