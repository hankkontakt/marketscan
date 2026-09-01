from fastapi.testclient import TestClient

from apps.api.main import app


def test_disabled_v3_routes_are_not_reachable(monkeypatch):
    monkeypatch.delenv("MARKETSCAN_FF_DECISION_V3_API", raising=False)
    response = TestClient(app).get("/api/v3/decisions/screener")
    assert response.status_code == 404
    assert response.json()["detail"] == "Decision API v3 is disabled"
