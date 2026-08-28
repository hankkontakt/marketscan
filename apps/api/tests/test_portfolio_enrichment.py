"""Enhetstester för portfolio-berikning + aktiesidans registry-fallback.

Testar (diagnos 2026-08-28: TAGM-B.ST/NCAB.ST saknade all data):
  - enrich_with_scan_data fallback: tickers utan scan_results-rad får name/market
    från universe_registry + alpha_rank/quality_z/momentum_z/value_z/stratum
    från qmj_scores. score_total/entry_signal förblir None (ärligt).
  - GET /api/stocks/{ticker}: registry+qmj-fallback ger 200 med riktig basdata
    i stället för 404; 404 endast när tickern inte alls är känd.
  - Befintlig fast path (scan_results-rad) är oförändrad.

Supabase-klienten mockas (FakeSupabase/FakeQuery) — inga nätverks- eller
DB-beroenden. Följer unittest-stilen i test_market_intel.py.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from apps.api.core.enrichment import enrich_with_scan_data


class FakeQuery:
    """Kedjebar PostgREST-liknande query-builder som returnerar fasta rader.

    Alla filter/order/limit är no-ops — raderna returneras i den ordning de
    gavs (testet lägger senaste raden först, som ORDER BY ... DESC gör).
    maybe_single returnerar första raden (eller None) som PostgREST gör.
    """

    def __init__(self, rows):
        self._rows = rows
        self._single = False

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows)


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


def _base_tables(**overrides):
    tables = {
        "scan_results": [
            {"ticker": "INVE-B.ST", "name": "Investor AB", "segment": "large_cap",
             "price": 300.0, "change_pct": 1.2, "score_total": 72.0,
             "entry_signal": "OK", "trend_signal": "Upptrend"},
        ],
        "universe_registry": [
            {"ticker": "NCAB.ST", "name": "NCAB Group AB", "market": "Mid Cap",
             "sector": "Industri"},
            {"ticker": "TAGM-B.ST", "name": "TagMaster AB", "market": "First North",
             "sector": "Teknik"},
        ],
        # Senaste scan_date-raden först (ORDER BY scan_date DESC).
        "qmj_scores": [
            {"ticker": "NCAB.ST", "scan_date": "2026-08-28", "stratum": "mid",
             "alpha_rank": 88.0, "quality_z": 77.0, "momentum_z": 66.0,
             "value_z": 55.0},
            {"ticker": "NCAB.ST", "scan_date": "2026-07-28", "stratum": "mid",
             "alpha_rank": 80.0, "quality_z": 70.0, "momentum_z": 60.0,
             "value_z": 50.0},
        ],
    }
    tables.update(overrides)
    return tables


class TestEnrichFallback(unittest.TestCase):
    def test_scan_row_still_wins(self):
        # Befintlig fast path: scan_results-raden anrikar som förut.
        sb = FakeSupabase(_base_tables())
        items = [{"ticker": "INVE-B.ST", "shares": 10}]
        enrich_with_scan_data(items, sb)
        self.assertEqual(items[0]["name"], "Investor AB")
        self.assertEqual(items[0]["score_total"], 72.0)
        self.assertEqual(items[0]["entry_signal"], "OK")

    def test_registry_and_qmj_fallback(self):
        # Tickers utan scan_results-rad → name/market från registry + qmj-fält.
        sb = FakeSupabase(_base_tables())
        items = [
            {"ticker": "INVE-B.ST", "shares": 10},
            {"ticker": "NCAB.ST", "shares": 5},
            {"ticker": "TAGM-B.ST", "shares": 20},
        ]
        enrich_with_scan_data(items, sb)
        by_ticker = {i["ticker"]: i for i in items}

        ncab = by_ticker["NCAB.ST"]
        self.assertEqual(ncab["name"], "NCAB Group AB")
        self.assertEqual(ncab["market"], "Mid Cap")
        self.assertEqual(ncab["alpha_rank"], 88.0)   # senaste scan_date-raden
        self.assertEqual(ncab["quality_z"], 77.0)
        self.assertEqual(ncab["momentum_z"], 66.0)
        self.assertEqual(ncab["value_z"], 55.0)
        self.assertEqual(ncab["stratum"], "mid")
        # Ärligt: inga påhittade scores när scan saknas.
        self.assertIsNone(ncab.get("score_total"))
        self.assertIsNone(ncab.get("entry_signal"))

        tagm = by_ticker["TAGM-B.ST"]
        self.assertEqual(tagm["name"], "TagMaster AB")
        self.assertEqual(tagm["market"], "First North")
        # Ingen qmj-rad → inga qmj-fält.
        self.assertIsNone(tagm.get("alpha_rank"))
        self.assertIsNone(tagm.get("quality_z"))
        self.assertIsNone(tagm.get("stratum"))

    def test_empty_fallback_tables_graceful(self):
        # Tomma registry/qmj-tabeller → inga nya fält, inget krasch.
        sb = FakeSupabase(_base_tables(universe_registry=[], qmj_scores=[]))
        items = [{"ticker": "NCAB.ST", "shares": 5}]
        enrich_with_scan_data(items, sb)
        self.assertIsNone(items[0].get("name"))
        self.assertIsNone(items[0].get("alpha_rank"))

    def test_existing_name_not_overwritten(self):
        # Befintligt name-fält (t.ex. från Avanza-import) skrivs inte över.
        sb = FakeSupabase(_base_tables())
        items = [{"ticker": "NCAB.ST", "shares": 5, "name": "Mitt NCAB"}]
        enrich_with_scan_data(items, sb)
        self.assertEqual(items[0]["name"], "Mitt NCAB")


class TestGetStockFallback(unittest.TestCase):
    """Route-wiring: GET /api/stocks/{ticker} registry+qmj-fallback (200/404)."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        cls._app = app
        cls._client = TestClient(app)

    def setUp(self):
        # Importera direkt här: dependency-override-nyckeln måste vara EXAKT
        # samma funktionsobjekt som Depends(get_supabase) använder.
        from apps.api.dependencies import get_supabase
        self._app.dependency_overrides[get_supabase] = (
            lambda: FakeSupabase(_base_tables())
        )
        # Tvinga registry-fallbacken: ingen Finnhub-nyckel i testet.
        from apps.api.routers import stocks as stocks_router
        self._fh_patch = mock.patch.object(stocks_router.settings, "FINNHUB_API_KEY", "")
        self._fh_patch.start()

    def tearDown(self):
        self._app.dependency_overrides.clear()
        self._fh_patch.stop()

    def test_registry_fallback_returns_200_with_base_data(self):
        # Varken scan_results eller Finnhub har data → registry+qmj ger 200.
        sb = FakeSupabase(_base_tables(scan_results=[]))
        from apps.api.dependencies import get_supabase
        self._app.dependency_overrides[get_supabase] = lambda: sb
        resp = self._client.get("/api/stocks/NCAB.ST")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["ticker"], "NCAB.ST")
        self.assertEqual(body["name"], "NCAB Group AB")
        self.assertEqual(body["market"], "Mid Cap")
        self.assertEqual(body["sector"], "Industri")
        self.assertEqual(body["segment"], "mid_cap")
        self.assertEqual(body["alpha_rank"], 88.0)
        self.assertEqual(body["quality_z"], 77.0)
        self.assertEqual(body["momentum_z"], 66.0)
        self.assertEqual(body["value_z"], 55.0)
        self.assertEqual(body["stratum"], "mid")
        self.assertIsNone(body["score_total"])  # ärligt — ej scorad

    def test_unknown_ticker_still_404(self):
        # Tickern inte alls känd → 404 behålls.
        sb = FakeSupabase(_base_tables(scan_results=[], universe_registry=[],
                                       qmj_scores=[]))
        from apps.api.dependencies import get_supabase
        self._app.dependency_overrides[get_supabase] = lambda: sb
        resp = self._client.get("/api/stocks/HELT-OKAND.ST")
        self.assertEqual(resp.status_code, 404)

    def test_scan_row_fast_path_unchanged(self):
        # Befintlig fast path: scan_results-raden returneras som förut.
        resp = self._client.get("/api/stocks/INVE-B.ST")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["name"], "Investor AB")
        self.assertEqual(body["score_total"], 72.0)


if __name__ == "__main__":
    unittest.main()