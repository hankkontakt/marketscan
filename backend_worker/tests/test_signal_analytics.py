"""Tester för signal_analytics.py — terminalpris-fallback i _forward_return_at
(survivorship-bias-fix, audit P2-7) + flagg-propagation i compute_factor_metrics.

Inga DB-beroenden: fake-cursor svarar per query-typ (mönster från
fi_short_positions-testen); compute_factor_metrics körs med mockad
_forward_return_at_flagged + fake-conn.
"""
import inspect
import unittest
from datetime import date
from unittest import mock

from backend_worker import signal_analytics as sa


class _ScriptedCursor:
    """Fake-cursor som svarar per query-typ för _forward_return_at_flagged.

    after    → pris i utfallsfönstret [target, target+14] (BETWEEN)
    at_date  → pris på from_date (scan_date =)
    terminal → senast tillgängliga pris före target (ORDER BY ... DESC)
    """

    def __init__(self, after=None, at_date=None, terminal=None):
        self.after = after
        self.at_date = at_date
        self.terminal = terminal
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if "BETWEEN" in sql:
            self._next = self.after
        elif "scan_date =" in sql:
            self._next = self.at_date
        elif "ORDER BY scan_date DESC" in sql:
            self._next = self.terminal
        else:
            self._next = None
        return self

    def fetchone(self):
        return self._next


class TestForwardReturnAtTerminalFallback(unittest.TestCase):
    """(a) Delisted-ticker: observation behålls med terminalpris, flaggad."""

    def test_terminal_fallback_behaller_observation(self):
        # 90-dagars utfall, sista prisdag före target → terminalpris används,
        # observationen behålls (inte droppad) och flaggas.
        cur = _ScriptedCursor(after=None, at_date=(100.0,), terminal=(50.0,))
        ret, used_terminal = sa._forward_return_at_flagged(
            cur, "DELIST", date(2024, 1, 3), 90
        )
        self.assertIsNotNone(ret)
        self.assertAlmostEqual(ret, -0.5)  # (50-100)/100
        self.assertTrue(used_terminal)

    def test_terminal_fallback_via_forward_return_at(self):
        # _forward_return_at (anropare-kompatibel) returnerar samma float.
        cur = _ScriptedCursor(after=None, at_date=(100.0,), terminal=(50.0,))
        ret = sa._forward_return_at(cur, "DELIST", date(2024, 1, 3), 90)
        self.assertAlmostEqual(ret, -0.5)

    def test_terminal_fallback_aldre_an_365_dagar(self):
        # Terminalpris > 365 dagar gammalt (utfallsfönstret långt överskridet)
        # → behålls ändå (terminal är vad som finns).
        cur = _ScriptedCursor(after=None, at_date=(100.0,), terminal=(25.0,))
        ret, used_terminal = sa._forward_return_at_flagged(
            cur, "GAMMAL", date(2024, 1, 3), 365
        )
        self.assertAlmostEqual(ret, -0.75)
        self.assertTrue(used_terminal)

    def test_terminal_query_bunden_vid_target(self):
        # Terminal-sökningen är bunden vid utfallsdagen (scan_date <= target).
        cur = _ScriptedCursor(after=None, at_date=(100.0,), terminal=(50.0,))
        sa._forward_return_at_flagged(cur, "DELIST", date(2024, 1, 3), 90)
        sql, params = cur.queries[-1]
        self.assertIn("scan_date <=", sql)
        self.assertIn("ORDER BY scan_date DESC", sql)
        self.assertEqual(params, ("DELIST", date(2024, 4, 2).isoformat()))

    def test_normal_path_oforandrad(self):
        # (b) Target finns i fönstret → vanlig path, ingen terminal-flagga.
        cur = _ScriptedCursor(after=(110.0,), at_date=(100.0,), terminal=None)
        ret, used_terminal = sa._forward_return_at_flagged(
            cur, "AKTIV", date(2024, 1, 3), 90
        )
        self.assertAlmostEqual(ret, 0.1)
        self.assertFalse(used_terminal)

    def test_ingen_prisdata_alls_droppas(self):
        # (c) Ingen prisdata för tickern → None (drop som förr).
        cur = _ScriptedCursor(after=None, at_date=(100.0,), terminal=None)
        self.assertIsNone(
            sa._forward_return_at_flagged(cur, "OKAND", date(2024, 1, 3), 90)
        )
        self.assertIsNone(sa._forward_return_at(cur, "OKAND", date(2024, 1, 3), 90))

    def test_saknad_startpris_droppas(self):
        # Ingen rad på from_date → None (kan inte mäta utan startpris).
        cur = _ScriptedCursor(after=(110.0,), at_date=None, terminal=(50.0,))
        self.assertIsNone(
            sa._forward_return_at_flagged(cur, "X", date(2024, 1, 3), 90)
        )

    def test_nollpris_start_droppas(self):
        # p0 = 0 → division med noll → None.
        cur = _ScriptedCursor(after=(110.0,), at_date=(0.0,), terminal=None)
        self.assertIsNone(
            sa._forward_return_at_flagged(cur, "X", date(2024, 1, 3), 90)
        )

    def test_signatur_kompatibel_med_anropare(self):
        # (d) _forward_return_at behåller signaturen (cur, ticker, from_date,
        # days) och returnerar float | None — exakt vad compute_factor_metrics
        # anropar.
        sig = inspect.signature(sa._forward_return_at)
        self.assertEqual(list(sig.parameters), ["cur", "ticker", "from_date", "days"])
        cur = _ScriptedCursor(after=(110.0,), at_date=(100.0,), terminal=None)
        ret = sa._forward_return_at(cur, "AKTIV", date(2024, 1, 3), 90)
        self.assertIsInstance(ret, float)
        self.assertAlmostEqual(ret, 0.1)


class _FakeFactorMetricsConn:
    """Fake-conn för compute_factor_metrics: scriptade svar per query."""

    def __init__(self, rows):
        self.rows = rows
        self.committed = False
        self.inserts = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self, cursor_factory=None):
        return _FakeFactorMetricsCursor(self)

    def commit(self):
        self.committed = True


class _FakeFactorMetricsCursor:
    def __init__(self, conn):
        self.conn = conn
        self._mode = None

    def execute(self, sql, params=None):
        if "to_regclass" in sql:
            self._mode = "regclass"
        elif "EXTRACT(DOW" in sql:
            self._mode = "rows"
        elif "INSERT INTO factor_metrics" in sql:
            self._mode = "insert"
            self.conn.inserts.append((sql, params))
        else:
            self._mode = "other"
        return self

    def fetchone(self):
        if self._mode == "regclass":
            return (True,)
        return None

    def fetchall(self):
        if self._mode == "rows":
            return self.conn.rows
        return []


class TestComputeFactorMetricsTerminalCounted(unittest.TestCase):
    """Terminalpris-observationer räknas med i factor_metrics (n) och loggas."""

    def _rows(self):
        rows = []
        for i in range(1, 25):
            ticker = f"DELIST{i}" if i <= 4 else f"T{i:02d}"
            rows.append({
                "ticker": ticker,
                "scan_date": date(2024, 1, 3),  # onsdag (EXTRACT(DOW)=3)
                "score_total": float(i),
                "score_quality": float(i),
                "score_momentum": float(i),
                "score_growth": float(i),
                "score_value": float(i),
                "price": 100.0,
            })
        return rows

    def test_terminal_observationer_raknas_i_n(self):
        conn = _FakeFactorMetricsConn(self._rows())

        def fake_flagged(cur, ticker, from_date, days):
            if days == 90 and ticker.startswith("DELIST"):
                return (-0.5, True)  # terminalpris-fallback
            return (0.1, False)

        with mock.patch(
            "backend_worker.signal_analytics.psycopg2.connect", return_value=conn
        ), mock.patch.object(sa, "_forward_return_at_flagged", side_effect=fake_flagged):
            written = sa.compute_factor_metrics("postgresql://fake")

        self.assertEqual(written, 15)  # 5 faktorer × 3 horisonter
        self.assertTrue(conn.committed)

        # score_total/90d: n = 24 — alla observationer räknas, inkl. de 4
        # terminalpris-raden (hade de droppats hade n varit 20).
        n_90 = [p[2] for _, p in conn.inserts if p[0] == "score_total" and p[1] == 90]
        self.assertEqual(n_90, [24])

    def test_terminal_raknas_loggas(self):
        conn = _FakeFactorMetricsConn(self._rows())

        def fake_flagged(cur, ticker, from_date, days):
            if days == 90 and ticker.startswith("DELIST"):
                return (-0.5, True)
            return (0.1, False)

        with mock.patch(
            "backend_worker.signal_analytics.psycopg2.connect", return_value=conn
        ), mock.patch.object(sa, "_forward_return_at_flagged", side_effect=fake_flagged):
            with self.assertLogs("backend_worker.signal_analytics", level="INFO") as cm:
                sa.compute_factor_metrics("postgresql://fake")

        terminal_logs = [m for m in cm.output if "terminalpris" in m]
        self.assertTrue(terminal_logs, "terminalpris-fallback ska loggas per faktor/horisont")
        self.assertIn("score_total/90d: 4 observationer med terminalpris", terminal_logs[0])


if __name__ == "__main__":
    unittest.main()