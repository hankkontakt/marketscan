from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.dependencies import get_supabase
from apps.api.main import app


class FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *columns):
        return self

    def eq(self, key, value):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, n):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class FakeDB:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


def _enable_flag(monkeypatch):
    monkeypatch.setenv("MARKETSCAN_FF_DECISION_V3_API", "true")


def _override_db(monkeypatch, tables):
    _enable_flag(monkeypatch)
    app.dependency_overrides[get_supabase] = lambda: FakeDB(tables)


def _row(**overrides):
    values = {
        "decision_id": "d1",
        "decision_snapshot_id": "s1",
        "listing_id": "l1",
        "ticker": "MSFT",
        "mic": "XNAS",
        "currency": "USD",
        "tradability_state": "ACTIVE",
        "decision_time": "2026-09-01T12:00:00Z",
        "master_rank_score": 82.0,
        "thesis_band": "BULLISH",
        "setup_state": "READY",
        "risk_state": "NORMAL",
        "is_actionable": True,
        "data_grade": "A",
        "coverage": 0.9,
        "stale_critical_count": 0,
        "published_at": "2026-09-01T12:00:00Z",
        "name": "Microsoft Corporation",
        "segment": "large_cap",
        "price": 420.5,
        "change_pct": 0.012,
    }
    values.update(overrides)
    return values


def test_disabled_v3_routes_are_not_reachable(monkeypatch):
    monkeypatch.delenv("MARKETSCAN_FF_DECISION_V3_API", raising=False)
    response = TestClient(app).get("/api/v3/decisions/screener")
    assert response.status_code == 404
    assert response.json()["detail"] == "Decision API v3 is disabled"


def test_disabled_system_snapshot_route_is_not_reachable(monkeypatch):
    monkeypatch.delenv("MARKETSCAN_FF_DECISION_V3_API", raising=False)
    response = TestClient(app).get("/api/v3/decisions/system/current-snapshot")
    assert response.status_code == 404


def test_enabled_screener_without_published_snapshot_returns_404(monkeypatch):
    _override_db(monkeypatch, {"current_decisions_v3": []})
    try:
        response = TestClient(app).get("/api/v3/decisions/screener")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_enabled_screener_returns_published_projection(monkeypatch):
    _override_db(monkeypatch, {"current_decisions_v3": [_row()]})
    try:
        response = TestClient(app).get("/api/v3/decisions/screener")
        assert response.status_code == 200
        body = response.json()
        assert body["snapshot_id"] == "s1"
        assert body["total_count"] == 1
        assert body["rows"][0]["ticker"] == "MSFT"
        assert body["rows"][0]["thesis_band"] == "BULLISH"
        assert body["rows"][0]["price"] == 420.5
    finally:
        app.dependency_overrides.clear()


def test_enabled_screener_filters_by_segment_and_thesis(monkeypatch):
    rows = [_row(ticker="MSFT", segment="large_cap", thesis_band="BULLISH"), _row(ticker="CPRX", segment="small_cap", thesis_band="NEUTRAL")]
    _override_db(monkeypatch, {"current_decisions_v3": rows})
    try:
        response = TestClient(app).get("/api/v3/decisions/screener?segment=small_cap&thesis_band=NEUTRAL")
        assert response.status_code == 200
        body = response.json()
        assert [row["ticker"] for row in body["rows"]] == ["CPRX"]
    finally:
        app.dependency_overrides.clear()


def test_stock_resolves_by_ticker_alias(monkeypatch):
    _override_db(monkeypatch, {"current_decisions_v3": [_row(ticker="CPRX")]})
    try:
        response = TestClient(app).get("/api/v3/decisions/stock/cprx")
        assert response.status_code == 200
        assert response.json()["ticker"] == "CPRX"
    finally:
        app.dependency_overrides.clear()


def test_current_snapshot_without_pointer_returns_zero_counts(monkeypatch):
    _override_db(monkeypatch, {"publication_state": [{"current_decision_snapshot_id": None}]})
    try:
        response = TestClient(app).get("/api/v3/decisions/system/current-snapshot")
        assert response.status_code == 200
        body = response.json()
        assert body["current_snapshot_id"] is None
        assert body["manifest_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_current_snapshot_reports_manifest_and_exclusion_counts(monkeypatch):
    _override_db(monkeypatch, {
        "publication_state": [{"current_decision_snapshot_id": "s1"}],
        "decision_snapshots": [{
            "decision_snapshot_id": "s1",
            "published_at": "2026-09-01T12:00:00Z",
            "master_model_version": "legacy-bridge-v3",
            "code_sha": "abc123",
            "quality_report": {"excluded_count": 2, "exclusions": [{"ticker": "CPRX", "reason": "listing_not_active:MERGED"}]},
        }],
        "decision_manifests": [{"is_actionable": True}, {"is_actionable": False}, {"is_actionable": True}],
    })
    try:
        response = TestClient(app).get("/api/v3/decisions/system/current-snapshot")
        assert response.status_code == 200
        body = response.json()
        assert body["current_snapshot_id"] == "s1"
        assert body["manifest_count"] == 3
        assert body["actionable_count"] == 2
        assert body["excluded_count"] == 2
        assert body["master_model_version"] == "legacy-bridge-v3"
    finally:
        app.dependency_overrides.clear()