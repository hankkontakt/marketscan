"""Tester för V3-beslutsberikning (champion-data) i portfolio-API:t.

Testar:
  - enrich_with_v3_decisions: items med ticker-träff i current_decisions_v3
    får sina V3-fält satta (första träffen vinner, befintliga fält skrivs
    inte över, is_actionable=False sätts fortfarande).
  - Items utan träff lämnas orörda (V1-beteende) — aldrig syntetiska värden.
  - GET /api/portfolio: v3-fälten syns i holdings-svaret (additivt).
  - _get_holdings_with_prices (risk.py): v3-fälten sätts även på den vägen.

Supabase-klienten mockas (FakeSupabase/FakeQuery) — inga nätverks- eller
DB-beroenden. Följer unittest-stilen i test_portfolio_enrichment.py och
auth-override-mönstret i test_ticker_normalization.py.
"""
import unittest
from types import SimpleNamespace

from apps.api.core.enrichment import enrich_with_v3_decisions


class FakeQuery:
    """Kedjebar PostgREST-liknande query-builder som returnerar fasta rader.

    Alla filter/order/limit är no-ops — raderna returneras i den ordning de
    gavs. maybe_single returnerar första raden (eller None) som PostgREST gör.
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


def _v3_row(**overrides):
    values = {
        "decision_id": "d1",
        "decision_snapshot_id": "s1",
        "listing_id": "l1",
        "ticker": "INVE-B.ST",
        "tradability_state": "ACTIVE",
        "master_rank_score": 82.0,
        "thesis_band": "BULLISH",
        "setup_state": "READY",
        "risk_state": "NORMAL",
        "is_actionable": True,
        "data_grade": "A",
        "segment_percentile": 0.93,
    }
    values.update(overrides)
    return values


def _base_tables(**overrides):
    tables = {
        "scan_results": [
            {"ticker": "INVE-B.ST", "name": "Investor AB", "price": 300.0,
             "change_pct": 1.2, "score_total": 72.0, "entry_signal": "OK",
             "trend_signal": "Upptrend"},
        ],
        "current_decisions_v3": [_v3_row()],
    }
    tables.update(overrides)
    return tables


class TestEnrichWithV3Decisions(unittest.TestCase):
    def test_match_sets_all_v3_fields(self):
        sb = FakeSupabase(_base_tables())
        items = [{"ticker": "INVE-B.ST", "shares": 10}]
        enrich_with_v3_decisions(items, sb)
        it = items[0]
        self.assertEqual(it["thesis_band"], "BULLISH")
        self.assertEqual(it["setup_state"], "READY")
        self.assertEqual(it["risk_state"], "NORMAL")
        self.assertEqual(it["data_grade"], "A")
        self.assertEqual(it["decision_id"], "d1")
        self.assertEqual(it["master_rank_score"], 82.0)
        self.assertEqual(it["segment_percentile"], 0.93)
        self.assertEqual(it["tradability_state"], "ACTIVE")
        self.assertIs(it["is_actionable"], True)
        self.assertEqual(it["v3_snapshot_id"], "s1")

    def test_no_hit_leaves_item_untouched(self):
        sb = FakeSupabase(_base_tables())
        items = [{"ticker": "HELT-OKAND.ST", "shares": 5}]
        enrich_with_v3_decisions(items, sb)
        self.assertEqual(items[0], {"ticker": "HELT-OKAND.ST", "shares": 5})

    def test_first_hit_wins(self):
        rows = [
            _v3_row(ticker="INVE-B.ST", thesis_band="BULLISH", decision_snapshot_id="s1"),
            _v3_row(ticker="INVE-B.ST", thesis_band="CONSTRUCTIVE", decision_snapshot_id="s2"),
        ]
        sb = FakeSupabase(_base_tables(current_decisions_v3=rows))
        items = [{"ticker": "INVE-B.ST", "shares": 10}]
        enrich_with_v3_decisions(items, sb)
        self.assertEqual(items[0]["thesis_band"], "BULLISH")
        self.assertEqual(items[0]["v3_snapshot_id"], "s1")

    def test_existing_field_not_overwritten(self):
        sb = FakeSupabase(_base_tables())
        items = [{"ticker": "INVE-B.ST", "shares": 10, "thesis_band": "MITT"}]
        enrich_with_v3_decisions(items, sb)
        self.assertEqual(items[0]["thesis_band"], "MITT")
        # Övriga fält sätts ändå.
        self.assertEqual(items[0]["setup_state"], "READY")

    def test_is_actionable_false_still_set(self):
        sb = FakeSupabase(_base_tables(current_decisions_v3=[_v3_row(is_actionable=False)]))
        items = [{"ticker": "INVE-B.ST", "shares": 10}]
        enrich_with_v3_decisions(items, sb)
        self.assertIs(items[0]["is_actionable"], False)

    def test_empty_view_is_graceful(self):
        sb = FakeSupabase(_base_tables(current_decisions_v3=[]))
        items = [{"ticker": "INVE-B.ST", "shares": 10}]
        enrich_with_v3_decisions(items, sb)
        self.assertEqual(items[0], {"ticker": "INVE-B.ST", "shares": 10})

    def test_no_tickers_returns_early(self):
        sb = FakeSupabase(_base_tables())
        items = [{"shares": 10}]
        enrich_with_v3_decisions(items, sb)
        self.assertEqual(items[0], {"shares": 10})


class TestGetPortfolioV3Enrichment(unittest.TestCase):
    """Route-wiring: GET /api/portfolio inkluderar v3-fälten additivt."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        cls._app = app
        cls._client = TestClient(app)

    def setUp(self):
        from apps.api.dependencies import get_user_supabase
        from apps.api.core.security import get_current_user, User
        self._sb = FakeSupabase({
            "portfolios": [{"id": "p1", "user_id": "u1", "name": "Test",
                            "created_at": "2026-01-01T00:00:00"}],
            "holdings": [
                {"id": "h1", "portfolio_id": "p1", "ticker": "INVE-B.ST",
                 "shares": 10, "cost_basis": 100.0,
                 "added_at": "2026-01-02T00:00:00"},
                {"id": "h2", "portfolio_id": "p1", "ticker": "HELT-OKAND.ST",
                 "shares": 5, "cost_basis": 50.0,
                 "added_at": "2026-01-03T00:00:00"},
            ],
            "scan_results": [
                {"ticker": "INVE-B.ST", "name": "Investor AB", "price": 300.0,
                 "change_pct": 1.2, "score_total": 72.0, "entry_signal": "OK",
                 "trend_signal": "Upptrend"},
                # Pris satt → _fill_live_prices gör inga nätverksanrop.
                {"ticker": "HELT-OKAND.ST", "name": "Okänd AB", "price": 10.0,
                 "change_pct": 0.0, "score_total": None, "entry_signal": None,
                 "trend_signal": None},
            ],
            "current_decisions_v3": [_v3_row()],
        })
        self._app.dependency_overrides[get_user_supabase] = lambda: self._sb
        self._app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@t.se")

    def tearDown(self):
        self._app.dependency_overrides.clear()

    def test_holdings_carry_v3_fields(self):
        resp = self._client.get("/api/portfolio")
        self.assertEqual(resp.status_code, 200)
        holdings = {h["ticker"]: h for h in resp.json()["holdings"]}

        inve = holdings["INVE-B.ST"]
        self.assertEqual(inve["thesis_band"], "BULLISH")
        self.assertEqual(inve["setup_state"], "READY")
        self.assertEqual(inve["risk_state"], "NORMAL")
        self.assertEqual(inve["data_grade"], "A")
        self.assertEqual(inve["decision_id"], "d1")
        self.assertEqual(inve["master_rank_score"], 82.0)
        self.assertEqual(inve["segment_percentile"], 0.93)
        self.assertEqual(inve["tradability_state"], "ACTIVE")
        self.assertIs(inve["is_actionable"], True)
        self.assertEqual(inve["v3_snapshot_id"], "s1")
        # Befintlig berikning är oförändrad.
        self.assertEqual(inve["name"], "Investor AB")
        self.assertEqual(inve["score_total"], 72.0)

    def test_holding_without_v3_hit_has_no_v3_fields(self):
        resp = self._client.get("/api/portfolio")
        self.assertEqual(resp.status_code, 200)
        holdings = {h["ticker"]: h for h in resp.json()["holdings"]}
        okand = holdings["HELT-OKAND.ST"]
        self.assertIsNone(okand.get("thesis_band"))
        self.assertIsNone(okand.get("decision_id"))
        self.assertIsNone(okand.get("v3_snapshot_id"))
        self.assertIsNone(okand.get("is_actionable"))


class TestRiskHoldingsPath(unittest.TestCase):
    """_get_holdings_with_prices (risk.py) sätter v3-fälten på holdings."""

    def test_holdings_with_prices_carry_v3_fields(self):
        from apps.api.routers.risk import _get_holdings_with_prices
        sb = FakeSupabase({
            "holdings": [
                {"id": "h1", "portfolio_id": "p1", "ticker": "INVE-B.ST",
                 "shares": 10, "cost_basis": 100.0,
                 "added_at": "2026-01-02T00:00:00"},
            ],
            "scan_results": [
                {"ticker": "INVE-B.ST", "name": "Investor AB", "price": 300.0,
                 "sector": "Finans", "score_total": 72.0},
            ],
            "current_decisions_v3": [_v3_row()],
        })
        result = _get_holdings_with_prices("p1", sb)
        self.assertEqual(len(result), 1)
        it = result[0]
        self.assertEqual(it["thesis_band"], "BULLISH")
        self.assertEqual(it["setup_state"], "READY")
        self.assertEqual(it["decision_id"], "d1")
        self.assertEqual(it["master_rank_score"], 82.0)
        self.assertEqual(it["v3_snapshot_id"], "s1")
        # Scan-berikningen är oförändrad.
        self.assertEqual(it["price"], 300.0)
        self.assertEqual(it["name"], "Investor AB")
        self.assertEqual(it["sector"], "Finans")

    def test_holdings_without_v3_hit_untouched(self):
        from apps.api.routers.risk import _get_holdings_with_prices
        sb = FakeSupabase({
            "holdings": [
                {"id": "h1", "portfolio_id": "p1", "ticker": "HELT-OKAND.ST",
                 "shares": 5, "cost_basis": 50.0,
                 "added_at": "2026-01-03T00:00:00"},
            ],
            "scan_results": [],
            "current_decisions_v3": [_v3_row()],
        })
        result = _get_holdings_with_prices("p1", sb)
        self.assertEqual(len(result), 1)
        self.assertNotIn("thesis_band", result[0])
        self.assertNotIn("v3_snapshot_id", result[0])


if __name__ == "__main__":
    unittest.main()