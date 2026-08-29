"""Tester för earnings_surprise.py — SUE-beräkning, PIT-guard, snapshot-väljare,
chunkad körning (pick_chunk + worker_state-cursor) och main-chunk-loggen.

Inga DB-beroenden: testar bara pure funktioner (compute_sue,
select_estimate_source, pick_chunk), process_earnings_frame (DataFrame → rader)
och cursor load/save via fake-conn (mönster från fi_short_positions-testen).
"""
import json
import unittest
from datetime import datetime, timezone
from unittest import mock

import pandas as pd

from backend_worker import earnings_surprise as es
from backend_worker.earnings_surprise import (
    compute_sue, pick_chunk, process_earnings_frame, select_estimate_source,
)


def _utc(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


class TestComputeSue(unittest.TestCase):
    """compute_sue(prior_surprises): element 0 = aktuella kvartalets surprise,
    element 1..8 = tidigare kvartal (senaste först)."""

    def test_min_four_priors(self):
        # 4 giltiga tidigare kvartal räcker
        self.assertIsNotNone(compute_sue([10.0, 5.0, -5.0, 3.0, -2.0]))
        # bara 3 tidigare kvartal → None
        self.assertIsNone(compute_sue([10.0, 5.0, -5.0, 3.0]))

    def test_std_zero_none(self):
        # alla tidigare surprises identiska → std=0 → None
        self.assertIsNone(compute_sue([10.0, 5.0, 5.0, 5.0, 5.0]))

    def test_clip(self):
        # enorm surprise → z clip till ±3
        self.assertEqual(compute_sue([1000.0, 1.0, 2.0, 3.0, 4.0]), 3.0)
        self.assertEqual(compute_sue([-1000.0, 1.0, 2.0, 3.0, 4.0]), -3.0)

    def test_z_value(self):
        # z = surprise_t / pstdev(priors)
        # pstdev([5.0, -5.0, 3.0, -2.0]) = sqrt(15.6875) ≈ 3.960744
        self.assertAlmostEqual(compute_sue([10.0, 5.0, -5.0, 3.0, -2.0]),
                               2.5248, places=3)

    def test_ordering_most_recent_first(self):
        # bara de 8 senaste tidigare kvartalen räknas (element 1..8)
        s = [10.0] + [1.0] * 8 + [5.0] * 4
        # de 8 senaste priors är alla 1.0 → std=0 → None
        # (hade funktionen använt alla 12 hade std>0 och z beräknats)
        self.assertIsNone(compute_sue(s))

    def test_surprise_t_is_first_element(self):
        # element 0 = aktuella kvartalets surprise (större surprise → större z)
        # små surprises så att z inte klipps till ±3
        priors = [1.0, 2.0, 3.0, 4.0]
        z1 = compute_sue([1.0] + priors)
        z2 = compute_sue([2.0] + priors)
        self.assertIsNotNone(z1)
        self.assertIsNotNone(z2)
        self.assertGreater(z2, z1)

    def test_none_handling(self):
        # None bland priors filtreras bort; 4 giltiga räcker
        self.assertIsNotNone(compute_sue([10.0, 5.0, None, 4.0, 3.0, 2.0]))
        # None som surprise_t → ingen SUE
        self.assertIsNone(compute_sue([None, 5.0, 4.0, 3.0, 2.0]))
        # tom lista → None
        self.assertIsNone(compute_sue([]))


class TestPitGuard(unittest.TestCase):
    """process_earnings_frame: framtida rader skippas från SUE men blir
    snapshot-kandidater; announced_on = UTC-datum."""

    @staticmethod
    def _frame(rows):
        # rows: (naiv NY-väggklocka, estimate, actual, surprise)
        idx = pd.DatetimeIndex([r[0] for r in rows], tz="America/New_York")
        return pd.DataFrame(
            [[r[1], r[2], r[3]] for r in rows],
            index=idx,
            columns=["EPS Estimate", "Reported EPS", "Surprise(%)"],
        )

    def test_future_rows_skipped_from_sue(self):
        now = _utc(2026, 8, 28, 12)
        df = self._frame([
            (datetime(2026, 11, 26, 10, 0), -0.10, None, None),    # framtida → snapshot
            (datetime(2026, 5, 29, 1, 0), -0.10, -0.12, -22.0),    # publicerad
            (datetime(2026, 2, 26, 1, 0), -0.11, -0.04, 63.48),    # publicerad
            (datetime(2025, 10, 24, 1, 0), -0.12, -0.15, -25.08),  # publicerad
            (datetime(2025, 7, 17, 2, 0), -0.12, -0.15, -18.0),    # publicerad
            (datetime(2025, 5, 8, 2, 0), -0.17, -0.20, -15.29),    # publicerad
        ])
        res = process_earnings_frame(df, "SIVE.ST", now)
        published, snapshots = res["published"], res["snapshots"]

        # framtida kvartal → snapshot-kandidat, inte publicerad
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["announced_on"].isoformat(), "2026-11-26")
        self.assertEqual(len(published), 5)

        # ingen publicerad rad har announce > now (PIT-guard)
        for p in published:
            self.assertLessEqual(p["announce_at"], now)

        # senaste publicerade kvartalet har 4 giltiga priors → SUE beräknad
        self.assertIsNotNone(published[0]["sue"])
        # äldsta publicerade kvartalet har inga priors → ingen SUE
        self.assertIsNone(published[-1]["sue"])

    def test_announced_on_is_utc_date(self):
        now = _utc(2026, 8, 28, 12)
        # NY 2026-05-29 22:00 (EDT, UTC-4) = UTC 2026-05-30 02:00 → datum 05-30
        df = self._frame([
            (datetime(2026, 5, 29, 22, 0), -0.10, -0.12, -22.0),
            (datetime(2026, 2, 26, 1, 0), -0.11, -0.04, 63.48),
            (datetime(2025, 10, 24, 1, 0), -0.12, -0.15, -25.08),
            (datetime(2025, 7, 17, 2, 0), -0.12, -0.15, -18.0),
            (datetime(2025, 5, 8, 2, 0), -0.17, -0.20, -15.29),
        ])
        res = process_earnings_frame(df, "SIVE.ST", now)
        self.assertEqual(res["published"][0]["announced_on"].isoformat(), "2026-05-30")

    def test_empty_frame(self):
        df = pd.DataFrame(columns=["EPS Estimate", "Reported EPS", "Surprise(%)"])
        res = process_earnings_frame(df, "SIVE.ST", _utc(2026, 8, 28, 12))
        self.assertEqual(res["published"], [])
        self.assertEqual(res["snapshots"], [])


class TestSnapshotSelector(unittest.TestCase):
    """select_estimate_source: snapshot före announce → snapshot; efter → retro."""

    def test_snapshot_before_announce_used(self):
        eps, source = select_estimate_source(
            snapshot_eps=0.5,
            snapshot_captured_at=_utc(2026, 5, 20, 10),
            yahoo_eps=0.6,
            announce_at=_utc(2026, 5, 29, 5),
        )
        self.assertEqual(eps, 0.5)
        self.assertEqual(source, "snapshot")

    def test_snapshot_after_announce_retro(self):
        # snapshot fångad EFTER annonsering (inte PIT-giltig) → retro
        eps, source = select_estimate_source(
            snapshot_eps=0.5,
            snapshot_captured_at=_utc(2026, 6, 1, 10),
            yahoo_eps=0.6,
            announce_at=_utc(2026, 5, 29, 5),
        )
        self.assertEqual(eps, 0.6)
        self.assertEqual(source, "retro")

    def test_no_snapshot_retro(self):
        eps, source = select_estimate_source(
            snapshot_eps=None, snapshot_captured_at=None,
            yahoo_eps=0.6, announce_at=_utc(2026, 5, 29, 5),
        )
        self.assertEqual(eps, 0.6)
        self.assertEqual(source, "retro")


class TestPickChunk(unittest.TestCase):
    """pick_chunk(tickers, cursor, chunk): chunk ur universum + nästa cursor."""

    def test_mellanhack(self):
        # cursor mitt i universumet → chunk + nästa cursor = cursor+chunk
        tickers = [f"T{i}" for i in range(10)]
        chunk, nxt = pick_chunk(tickers, 0, 4)
        self.assertEqual(chunk, ["T0", "T1", "T2", "T3"])
        self.assertEqual(nxt, 4)

    def test_wraparound_vid_slut(self):
        # sista chunken kortare än chunk-size → wrap: nästa cursor = 0
        tickers = [f"T{i}" for i in range(10)]
        chunk, nxt = pick_chunk(tickers, 8, 4)
        self.assertEqual(chunk, ["T8", "T9"])
        self.assertEqual(nxt, 0)

    def test_exakt_slut_nollas(self):
        # chunk slutar exakt på sista tickern → wrap: nästa cursor = 0
        tickers = [f"T{i}" for i in range(10)]
        chunk, nxt = pick_chunk(tickers, 6, 4)
        self.assertEqual(chunk, ["T6", "T7", "T8", "T9"])
        self.assertEqual(nxt, 0)

    def test_tomt_universum(self):
        self.assertEqual(pick_chunk([], 0, 60), ([], 0))

    def test_cursor_bortom_slut(self):
        # universumet krympt sedan förra körningen → tom chunk + wrap
        tickers = [f"T{i}" for i in range(10)]
        self.assertEqual(pick_chunk(tickers, 15, 4), ([], 0))

    def test_negativ_cursor_klampas(self):
        # korrupt worker_state-värde ska aldrig processa fel tickers
        tickers = [f"T{i}" for i in range(10)]
        chunk, nxt = pick_chunk(tickers, -3, 4)
        self.assertEqual(chunk, ["T0", "T1", "T2", "T3"])
        self.assertEqual(nxt, 4)


class _FakeCursor:
    """Cursor med execute/fetchone — lagrar skrivet värde, returnerar på läs."""

    def __init__(self, stored_value=None):
        self.stored_value = stored_value
        self.last_query = ""
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_query = sql
        self.last_params = params
        return self

    def fetchone(self):
        if self.stored_value is None:
            return None
        return (self.stored_value,)


class _FakeConn:
    def __init__(self, stored_value=None):
        self._cursor = _FakeCursor(stored_value)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


class TestCursorWorkerState(unittest.TestCase):
    """earnings_surprise_cursor i worker_state: load/save via fake-conn."""

    def test_load_fran_worker_state(self):
        # psycopg2 returnerar JSONB som dict → next_index returneras direkt.
        conn = _FakeConn(stored_value={"next_index": 42,
                                       "updated_at": "2026-08-29T04:10:00+00:00"})
        self.assertEqual(es._load_cursor(conn), 42)

    def test_load_tom_worker_state(self):
        # Ingen rad → 0 (börja från början).
        self.assertEqual(es._load_cursor(_FakeConn(stored_value=None)), 0)

    def test_load_str_value(self):
        # JSONB som str (t.ex. från annan klient) → parsas.
        conn = _FakeConn(stored_value=json.dumps({"next_index": 7}))
        self.assertEqual(es._load_cursor(conn), 7)

    def test_load_ogiltigt_varde(self):
        # Värde utan next_index → 0.
        self.assertEqual(es._load_cursor(_FakeConn(stored_value={"foo": "bar"})), 0)

    def test_save_upsert_till_worker_state(self):
        conn = _FakeConn()
        es._save_cursor(conn, 60)
        self.assertEqual(conn._cursor.last_params[0], es.CURSOR_STATE_KEY)
        saved = json.loads(conn._cursor.last_params[1])
        self.assertEqual(saved["next_index"], 60)
        self.assertIn("updated_at", saved)
        # Commit sköts av anroparen (samma transaktion som upsert) — cursorn
        # avancerar bara om datan också skrivs.
        self.assertFalse(conn.committed)


class TestMainChunkLog(unittest.TestCase):
    """main() loggar chunk-info (cursor → nästa) vid varje körning."""

    @staticmethod
    def _empty_frame():
        return pd.DataFrame(columns=["EPS Estimate", "Reported EPS", "Surprise(%)"])

    def test_main_loggar_chunk_info(self):
        tickers = [f"T{i}.ST" for i in range(10)]
        with mock.patch.object(es, "load_universe", return_value=tickers), \
             mock.patch.object(es, "_last_run_age_hours", return_value=None), \
             mock.patch.object(es, "_load_cursor", return_value=4), \
             mock.patch.object(es, "fetch_earnings_dates", return_value=self._empty_frame()), \
             mock.patch.object(es, "_archive_raw"), \
             mock.patch.object(es, "_connect", return_value=mock.MagicMock()), \
             mock.patch.object(es.time, "sleep"), \
             mock.patch("sys.argv", ["earnings_surprise.py", "--dry-run"]), \
             mock.patch.dict("os.environ", {"DATABASE_URL": "postgres://fake"}):
            with self.assertLogs("backend_worker.earnings_surprise", level="INFO") as cm:
                es.main()
        joined = "\n".join(cm.output)
        # cursor 4 + chunk 60 över 10 tickers → 6 tickers, wrap → nästa 0
        self.assertIn("Chunk: 6/10 tickers (cursor 4 → nästa 0)", joined)

    def test_full_ignorerar_cursor(self):
        # --full: cursorn läses inte, hela universumet processas från 0.
        tickers = [f"T{i}.ST" for i in range(10)]
        with mock.patch.object(es, "load_universe", return_value=tickers), \
             mock.patch.object(es, "_last_run_age_hours", return_value=None), \
             mock.patch.object(es, "_load_cursor") as load_cursor, \
             mock.patch.object(es, "fetch_earnings_dates", return_value=self._empty_frame()), \
             mock.patch.object(es, "_archive_raw"), \
             mock.patch.object(es, "_connect", return_value=mock.MagicMock()), \
             mock.patch.object(es.time, "sleep"), \
             mock.patch("sys.argv", ["earnings_surprise.py", "--dry-run", "--full"]), \
             mock.patch.dict("os.environ", {"DATABASE_URL": "postgres://fake"}):
            with self.assertLogs("backend_worker.earnings_surprise", level="INFO") as cm:
                es.main()
        load_cursor.assert_not_called()
        joined = "\n".join(cm.output)
        self.assertIn("Chunk: 10/10 tickers (cursor 0 → nästa 0, fullkörning)", joined)


if __name__ == "__main__":
    unittest.main()