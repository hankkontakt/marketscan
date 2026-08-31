"""Tester för ticker-normalisering + /scan default-segment (ren unittest, ingen DB).

Diagnos 2026-08-29:
  - Manuell add_holding sparade "TAGM B" med mellanslag medan import-kedjan
    ger "TAGM-B.ST" (avanza_import.kortnamn_to_ticker). Fix: norm_ticker_input
    kör samma maskin på manuella inmatningar.
  - /scan default-segment var ["large_cap", "mid_cap"] — small/micro exkluderades
    trots att appens focus är hela marknaden. Fix: default = inget segmentfilter
    (alla segment); filter bara vid explicit ?segments=...

Följer unittest-stilen i test_portfolio_enrichment.py / test_alert_routes.py.
Supabase-klienten mockas (FakeSupabase/FakeQuery) — inga nätverks- eller
DB-beroenden.
"""
import unittest
from types import SimpleNamespace

from apps.api.core.avanza_import import norm_ticker_input


# ─── Pure function: norm_ticker_input ─────────────────────────────────────────


class TestNormTickerInput(unittest.TestCase):
    """Manuell ticker-inmatning normaliseras till kanonisk Yahoo-form."""

    def test_lowercase_with_space_gets_dash_and_st_suffix(self):
        # "tagm b" → "TAGM-B.ST" (samma maskin som import-kedjan)
        self.assertEqual(norm_ticker_input("tagm b"), "TAGM-B.ST")

    def test_plain_name_gets_st_suffix(self):
        self.assertEqual(norm_ticker_input("NCAB"), "NCAB.ST")

    def test_already_suffixed_ticker_left_alone(self):
        # Befintligt suffix rörs inte — aldrig dubbel-suffix.
        self.assertEqual(norm_ticker_input("TAGM-B.ST"), "TAGM-B.ST")

    def test_lowercase_suffixed_uppercased_but_suffix_kept(self):
        self.assertEqual(norm_ticker_input("tagm-b.st"), "TAGM-B.ST")

    def test_non_st_suffix_kept(self):
        self.assertEqual(norm_ticker_input("ASML.AS"), "ASML.AS")

    def test_us_ticker_gets_st_suffix_documented_sweden_default(self):
        # Dokumenterad Sverige-app-default: icke-suffixade får .ST.
        self.assertEqual(norm_ticker_input("AAPL"), "AAPL.ST")

    def test_whitespace_stripped(self):
        # Mellanslag runt om stripas; inre mellanslag → bindestreck.
        self.assertEqual(norm_ticker_input("  tagm b  "), "TAGM-B.ST")

    def test_empty_and_none(self):
        self.assertEqual(norm_ticker_input(""), "")
        self.assertEqual(norm_ticker_input(None), "")


# ─── /scan default-segment (route-level) ──────────────────────────────────────


class RecordingQuery:
    """Kedjebar query-builder som loggar .in_-anrop (segment-filtrering)."""

    def __init__(self, rows):
        self._rows = rows
        self.in_calls: list[tuple] = []

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        self.in_calls.append(a)
        return self

    def gte(self, *a, **k):
        return self

    def lte(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *a, **k):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeSupabase:
    def __init__(self, rows):
        self._rows = rows
        self.queries_by_table: dict[str, RecordingQuery] = {}
        self.last_query: RecordingQuery | None = None

    def table(self, name):
        q = RecordingQuery(self._rows if name == "scan_results" else [])
        self.queries_by_table[name] = q
        if name == "scan_results" or self.last_query is None:
            self.last_query = q
        return q


_SCAN_ROWS = [
    {"ticker": "INVE-B.ST", "name": "Investor AB", "segment": "large_cap", "score_total": 72.0},
    {"ticker": "NCAB.ST", "name": "NCAB Group AB", "segment": "mid_cap", "score_total": 60.0},
    {"ticker": "TAGM-B.ST", "name": "TagMaster AB", "segment": "small_cap", "score_total": 55.0},
    {"ticker": "MIPS.ST", "name": "MIPS AB", "segment": "micro_cap", "score_total": 40.0},
]


class TestScanDefaultSegments(unittest.TestCase):
    """/scan: default = ALLA segment; filter bara vid explicit ?segments=..."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        cls._app = app
        cls._client = TestClient(app)

    def setUp(self):
        from apps.api.dependencies import get_supabase
        self._sb = FakeSupabase(_SCAN_ROWS)
        self._app.dependency_overrides[get_supabase] = lambda: self._sb

    def tearDown(self):
        self._app.dependency_overrides.clear()

    def _segment_filters(self):
        q = self._sb.queries_by_table.get("scan_results") or self._sb.last_query
        return [a for a in q.in_calls if a[0] == "segment"]

    def test_no_segments_param_returns_all_segments(self):
        resp = self._client.get("/api/scan")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 4)  # alla fyra segmenten
        self.assertEqual(self._segment_filters(), [])  # inget segmentfilter

    def test_explicit_single_segment_filters(self):
        resp = self._client.get("/api/scan", params={"segments": "small_cap"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._segment_filters(), [("segment", ["small_cap"])])

    def test_explicit_multi_segment_filters(self):
        resp = self._client.get(
            "/api/scan",
            params=[("segments", "large_cap"), ("segments", "mid_cap")],
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._segment_filters(), [("segment", ["large_cap", "mid_cap"])])


# ─── add_holding normaliserar manuell inmatning (buggfix) ─────────────────────


class AddHoldingFakeQuery:
    """Fake för add_holding-flödet: portfolios / scan_results / holdings / requests."""

    def __init__(self, rows, table, parent):
        self._rows = rows
        self._table = table
        self._parent = parent

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, payload, **k):
        self._parent.upserts.append((self._table, payload))
        return self

    def insert(self, payload):
        self._parent.inserts.append((self._table, payload))
        # Returnera det som faktiskt sattes in (med id/added_at för HoldingOut).
        self._rows = [dict(payload, id="h1", added_at="2026-08-29T00:00:00")]
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class AddHoldingFakeSupabase:
    def __init__(self, tables):
        self._tables = tables
        self.inserts: list[tuple] = []
        self.upserts: list[tuple] = []

    def table(self, name):
        return AddHoldingFakeQuery(self._tables.get(name, []), name, self)


class TestAddHoldingNormalizesTicker(unittest.TestCase):
    """add_holding kör norm_ticker_input på manuell inmatning (buggfix)."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        cls._app = app
        cls._client = TestClient(app)

    def setUp(self):
        from apps.api.dependencies import get_user_supabase, get_supabase_admin
        from apps.api.core.security import get_current_user, User
        self._sb = AddHoldingFakeSupabase({
            "portfolios": [{"id": "p1"}],
            "scan_results": [],  # out-of-universe → köar ticker-request
        })
        self._app.dependency_overrides[get_user_supabase] = lambda: self._sb
        self._app.dependency_overrides[get_supabase_admin] = lambda: self._sb
        self._app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@t.se")

    def tearDown(self):
        self._app.dependency_overrides.clear()

    def test_manual_lowercase_with_space_normalized(self):
        resp = self._client.post("/api/portfolio/holdings", json={
            "ticker": "tagm b", "shares": 10, "cost_basis": 100,
        })
        self.assertEqual(resp.status_code, 201)
        # Inlagd holding har kanonisk ticker — inte "TAGM B" med mellanslag.
        payload = self._sb.inserts[0][1]
        self.assertEqual(payload["ticker"], "TAGM-B.ST")
        self.assertEqual(resp.json()["ticker"], "TAGM-B.ST")
        # Out-of-universe-request köas med samma kanoniska ticker.
        self.assertEqual(self._sb.upserts[0][1]["ticker"], "TAGM-B.ST")

    def test_plain_name_gets_st_suffix(self):
        resp = self._client.post("/api/portfolio/holdings", json={
            "ticker": "NCAB", "shares": 5, "cost_basis": 50,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._sb.inserts[0][1]["ticker"], "NCAB.ST")
        self.assertEqual(resp.json()["ticker"], "NCAB.ST")

    def test_already_suffixed_ticker_not_double_suffixed(self):
        resp = self._client.post("/api/portfolio/holdings", json={
            "ticker": "TAGM-B.ST", "shares": 10, "cost_basis": 100,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._sb.inserts[0][1]["ticker"], "TAGM-B.ST")
        self.assertEqual(resp.json()["ticker"], "TAGM-B.ST")


if __name__ == "__main__":
    unittest.main()