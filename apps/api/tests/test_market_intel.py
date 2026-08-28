"""Enhetstester för market_intel-radarn (lokala mockar, ingen DB).

Testar kontraktet från PLAN.md ROND 4 (API-kontrakt-sektionen):
  - RadarItemOut nya fält: sector, sector_value_z, value_mode, earnings_sue,
    earnings_announced.
  - RadarResponse nya fält: signal_ics (senaste per faktor, kanonisk ordning),
    qmj_regime.
  - F7: earnings anrikar EXISTERANDE items — earnings-only-tickers är INTE i
    unionen.
  - Ny endpoint GET /api/market-intel/qmj-regime → QmjRegimeOut (null om tom).
  - Runtime-säkerhet: tomma/nya tabeller → radarn 500:ar inte.

Supabase-klienten mockas (FakeSupabase/FakeQuery) — inga nätverks- eller
DB-beroenden. Följer unittest-stilen i backend_worker/tests/.
"""
import unittest
from types import SimpleNamespace

from apps.api.routers.market_intel import (QmjRegimeOut,
                                           RADAR_THEMES,
                                           RadarItemOut, RadarResponse,
                                           get_qmj_regime, get_radar)


class FakeQuery:
    """Kedjebar PostgREST-liknande query-builder som returnerar fasta rader.

    Alla filter/order/limit är no-ops — raderna returneras i den ordning de
    gavs (testet lägger senaste raden först, som ORDER BY ... DESC gör).
    """

    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def lt(self, *a, **k):
        return self

    def is_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    @property
    def not_(self):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


def _base_tables(**overrides):
    tables = {
        "qmj_scores": [
            {"ticker": "AAA.ST", "scan_date": "2026-08-28", "stratum": "mid",
             "alpha_rank": 90.0, "quality_z": 80.0, "momentum_z": 70.0,
             "value_z": 60.0, "payout_z": 50.0, "insider_z": 40.0,
             "exclusion_reason": None, "sector_value_z": 75.0,
             "value_mode": "sector", "data_quality": "ok",
             "as_of_date": "2026-03-31"},
            {"ticker": "BBB.ST", "scan_date": "2026-08-28", "stratum": "small",
             "alpha_rank": 85.0, "quality_z": 70.0, "momentum_z": 60.0,
             "value_z": 50.0, "payout_z": 40.0, "insider_z": 30.0,
             "exclusion_reason": None, "sector_value_z": None,
             "value_mode": "global", "data_quality": "partial",
             "as_of_date": None},
        ],
        "news_events": [
            {"ticker": "AAA.ST", "headline": "Order", "bearing": "positive",
             "confidence": 0.9, "published_at": "2026-08-28T08:00:00",
             "message_url": "https://x", "source_category": "order",
             "mention_surge": 2.5},
        ],
        "short_positions": [],
        "insider_cluster_signals": [],
        "universe_registry": [
            {"ticker": "AAA.ST", "name": "AAA AB", "sector": "Industri"},
            {"ticker": "BBB.ST", "name": "BBB AB", "sector": None},
        ],
        # Senaste announced_on först (ORDER BY announced_on DESC).
        "earnings_surprises": [
            {"ticker": "AAA.ST", "announced_on": "2026-08-20", "sue": 1.8},
            {"ticker": "AAA.ST", "announced_on": "2026-05-10", "sue": 0.5},
            # earnings-only-ticker → får INTE dyka upp i radarn (F7).
            {"ticker": "CCC.ST", "announced_on": "2026-08-21", "sue": 2.2},
        ],
        "factor_metrics": [
            {"factor": "score_momentum", "horizon_days": 90,
             "computed_date": "2026-08-28", "n": 40, "rank_ic": 0.05,
             "decile_spread": 0.02, "decile_spread_net": 0.0, "win_rate": 0.55},
            {"factor": "score_momentum", "horizon_days": 90,
             "computed_date": "2026-07-28", "n": 30, "rank_ic": 0.03,
             "decile_spread": 0.01, "decile_spread_net": -0.01, "win_rate": 0.5},
            {"factor": "score_total", "horizon_days": 90,
             "computed_date": "2026-08-28", "n": 5, "rank_ic": None,
             "decile_spread": None, "decile_spread_net": None, "win_rate": None},
            {"factor": "score_quality", "horizon_days": 90,
             "computed_date": "2026-08-28", "n": 42, "rank_ic": 0.07,
             "decile_spread": 0.03, "decile_spread_net": 0.01, "win_rate": 0.6},
            {"factor": "score_growth", "horizon_days": 90,
             "computed_date": "2026-08-28", "n": 38, "rank_ic": 0.02,
             "decile_spread": 0.01, "decile_spread_net": -0.01, "win_rate": 0.52},
            {"factor": "score_value", "horizon_days": 90,
             "computed_date": "2026-08-28", "n": 41, "rank_ic": 0.04,
             "decile_spread": 0.02, "decile_spread_net": 0.0, "win_rate": 0.54},
        ],
        "factor_regime": [
            {"computed_date": "2026-08-01", "data_through": "2026-07-31",
             "premium_12m": 0.042, "percentile": 0.87, "n_obs": 372,
             "regime": "stark", "reason": "87% OOS-percentil",
             "countries": ["SWE", "DNK", "FIN", "NOR"],
             "europe_12m": 0.01, "global_12m": 0.005},
        ],
    }
    tables.update(overrides)
    return tables


class TestSchemas(unittest.TestCase):
    def test_radar_item_new_fields_default_none(self):
        item = RadarItemOut(ticker="X")
        self.assertIsNone(item.sector)
        self.assertIsNone(item.sector_value_z)
        self.assertIsNone(item.value_mode)
        self.assertIsNone(item.earnings_sue)
        self.assertIsNone(item.earnings_announced)

    def test_radar_response_new_fields_defaults(self):
        resp = RadarResponse(total=0, items=[])
        self.assertEqual(resp.signal_ics, [])
        self.assertIsNone(resp.qmj_regime)

    def test_radar_themes_contains_dilution(self):
        # RADAR_THEMES matchar news_discovery.py-temalistan exakt (8 teman).
        self.assertIn("dilution", RADAR_THEMES)
        self.assertEqual(
            RADAR_THEMES,
            {"ipo", "order", "vinstvarning", "ledning", "regulatorik",
             "sector-ai", "sector-forsvar", "dilution"},
        )

    def test_qmj_regime_out(self):
        r = QmjRegimeOut(computed_date="2026-08-01", data_through="2026-07-31",
                         premium_12m=0.042, percentile=0.87, n_obs=372,
                         regime="stark", reason="x", countries=["SWE"],
                         europe_12m=0.01, global_12m=0.005)
        self.assertEqual(r.regime, "stark")
        self.assertEqual(r.countries, ["SWE"])
        self.assertEqual(r.computed_date, "2026-08-01")


class TestRadar(unittest.TestCase):
    def test_new_fields_and_enrichment(self):
        sb = FakeSupabase(_base_tables())
        resp = get_radar(sb=sb)
        by_ticker = {i.ticker: i for i in resp.items}
        self.assertIn("AAA.ST", by_ticker)
        aaa = by_ticker["AAA.ST"]
        self.assertEqual(aaa.sector, "Industri")
        self.assertEqual(aaa.sector_value_z, 75.0)
        self.assertEqual(aaa.value_mode, "sector")
        self.assertEqual(aaa.earnings_sue, 1.8)          # senaste announced_on
        self.assertEqual(aaa.earnings_announced, "2026-08-20")
        bbb = by_ticker["BBB.ST"]
        self.assertIsNone(bbb.sector)
        self.assertIsNone(bbb.sector_value_z)
        self.assertEqual(bbb.value_mode, "global")
        self.assertIsNone(bbb.earnings_sue)

    def test_earnings_only_ticker_not_in_union(self):
        # F7: earnings anrikar, lägger ALDRIG till nya tickers.
        sb = FakeSupabase(_base_tables())
        resp = get_radar(sb=sb)
        tickers = {i.ticker for i in resp.items}
        self.assertNotIn("CCC.ST", tickers)

    def test_union_includes_cluster_only_ticker(self):
        # Kluster-tickers är hög-signal: en ticker som BARA finns i
        # insider_cluster_signals ska ändå dyka upp i radarn (anrikad).
        sb = FakeSupabase(_base_tables(
            insider_cluster_signals=[
                {"ticker": "DDD.ST", "cluster_score": 0.9,
                 "unique_sellers_30d": 4},
            ],
        ))
        resp = get_radar(sb=sb)
        by_ticker = {i.ticker: i for i in resp.items}
        self.assertIn("DDD.ST", by_ticker)
        self.assertEqual(by_ticker["DDD.ST"].cluster_score, 0.9)
        self.assertEqual(by_ticker["DDD.ST"].sellers_30d, 4)
        self.assertIn("säljkluster", by_ticker["DDD.ST"].warnings)

    def test_data_quality_and_as_of_fields(self):
        sb = FakeSupabase(_base_tables())
        resp = get_radar(sb=sb)
        by_ticker = {i.ticker: i for i in resp.items}
        aaa = by_ticker["AAA.ST"]
        self.assertEqual(aaa.data_quality, "ok")
        self.assertEqual(aaa.as_of_date.isoformat(), "2026-03-31")
        bbb = by_ticker["BBB.ST"]
        self.assertEqual(bbb.data_quality, "partial")
        self.assertIsNone(bbb.as_of_date)

    def test_total_is_uncapped_count(self):
        # > limit (40) tickers → total = pre-cap count, len(items) = cap.
        qmj_rows = [
            {"ticker": f"T{i:03d}.ST", "scan_date": "2026-08-28",
             "stratum": "mid", "alpha_rank": float(100 - i),
             "quality_z": 50.0, "momentum_z": 50.0, "value_z": 50.0,
             "payout_z": 50.0, "insider_z": 50.0, "exclusion_reason": None,
             "sector_value_z": None, "value_mode": "global"}
            for i in range(45)
        ]
        sb = FakeSupabase(_base_tables(
            qmj_scores=qmj_rows, news_events=[], short_positions=[],
            insider_cluster_signals=[],
        ))
        resp = get_radar(sb=sb)
        self.assertEqual(resp.total, 45)
        self.assertEqual(len(resp.items), 40)
        self.assertNotEqual(resp.total, len(resp.items))

    def test_signal_ics_canonical_order_and_latest_per_factor(self):
        sb = FakeSupabase(_base_tables())
        resp = get_radar(sb=sb)
        factors = [m.factor for m in resp.signal_ics]
        self.assertEqual(factors, ["score_total", "score_quality",
                                   "score_momentum", "score_growth",
                                   "score_value"])
        by_factor = {m.factor: m for m in resp.signal_ics}
        # Senaste per faktor (inte den gamla 07-28-raden).
        self.assertEqual(by_factor["score_momentum"].computed_date, "2026-08-28")
        # Låg n behålls (UI visar 'ej mätt') — rank_ic None.
        self.assertIsNone(by_factor["score_total"].rank_ic)
        self.assertEqual(by_factor["score_total"].n, 5)

    def test_qmj_regime_in_response(self):
        sb = FakeSupabase(_base_tables())
        resp = get_radar(sb=sb)
        self.assertIsNotNone(resp.qmj_regime)
        self.assertEqual(resp.qmj_regime.regime, "stark")
        self.assertEqual(resp.qmj_regime.countries, ["SWE", "DNK", "FIN", "NOR"])
        self.assertEqual(resp.qmj_regime.percentile, 0.87)

    def test_empty_new_tables_graceful(self):
        # Runtime-säkerhet: tomma/nya tabeller → radarn 500:ar inte.
        sb = FakeSupabase(_base_tables(earnings_surprises=[],
                                       factor_metrics=[],
                                       factor_regime=[]))
        resp = get_radar(sb=sb)
        self.assertEqual(resp.signal_ics, [])
        self.assertIsNone(resp.qmj_regime)
        self.assertIn("AAA.ST", {i.ticker for i in resp.items})


class TestQmjRegimeEndpoint(unittest.TestCase):
    def test_returns_regime(self):
        sb = FakeSupabase(_base_tables())
        out = get_qmj_regime(sb=sb)
        self.assertIsInstance(out, QmjRegimeOut)
        self.assertEqual(out.computed_date, "2026-08-01")
        self.assertEqual(out.data_through, "2026-07-31")
        self.assertEqual(out.premium_12m, 0.042)

    def test_empty_returns_none(self):
        sb = FakeSupabase(_base_tables(factor_regime=[]))
        self.assertIsNone(get_qmj_regime(sb=sb))


class TestRouteContract(unittest.TestCase):
    """Route-wiring + JSON-serialisering via TestClient (dependency override).

    Verifierar det exakta JSON-kontraktet UI:n är byggd mot (ROND 4).
    """

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        cls._app = app
        cls._client = TestClient(app)

    def setUp(self):
        # Importera direkt här: en funktion lagrad som klassattribut blir en
        # bound method vid self-åtkomst — och dependency-override-nyckeln måste
        # vara EXAKT samma funktionsobjekt som Depends(get_supabase) använder.
        from apps.api.dependencies import get_supabase
        self._app.dependency_overrides[get_supabase] = (
            lambda: FakeSupabase(_base_tables())
        )

    def tearDown(self):
        self._app.dependency_overrides.clear()

    def test_radar_json_contract(self):
        resp = self._client.get("/api/market-intel/radar")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("signal_ics", body)
        self.assertIn("qmj_regime", body)
        aaa = next(i for i in body["items"] if i["ticker"] == "AAA.ST")
        self.assertEqual(aaa["sector"], "Industri")
        self.assertEqual(aaa["sector_value_z"], 75.0)
        self.assertEqual(aaa["value_mode"], "sector")
        self.assertEqual(aaa["earnings_sue"], 1.8)
        self.assertEqual(aaa["earnings_announced"], "2026-08-20")
        self.assertEqual(aaa["data_quality"], "ok")
        self.assertEqual(aaa["as_of_date"], "2026-03-31")
        self.assertEqual(body["qmj_regime"]["regime"], "stark")
        self.assertEqual(
            [m["factor"] for m in body["signal_ics"]],
            ["score_total", "score_quality", "score_momentum",
             "score_growth", "score_value"],
        )

    def test_qmj_regime_route(self):
        resp = self._client.get("/api/market-intel/qmj-regime")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["regime"], "stark")
        self.assertEqual(body["computed_date"], "2026-08-01")
        self.assertEqual(body["countries"], ["SWE", "DNK", "FIN", "NOR"])

    def test_qmj_regime_route_empty_is_null(self):
        from apps.api.dependencies import get_supabase
        self._app.dependency_overrides[get_supabase] = (
            lambda: FakeSupabase(_base_tables(factor_regime=[]))
        )
        resp = self._client.get("/api/market-intel/qmj-regime")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json())


if __name__ == "__main__":
    unittest.main()