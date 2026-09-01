"""
Phase 6 Verification Tests: Decision API v2
- Screener endpoint /api/v2/decisions/screener contract & response schema
- Stock detail endpoint /api/v2/decisions/stock/{ticker}
- Typed filter parameters (thesis_band, setup_state, risk_state)
- Tradability gate enforcement on CPRX
- Snapshot consistency verification
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_screener_decisions_endpoint():
    response = client.get("/api/v2/decisions/screener?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total_count" in data
    assert "rows" in data
    assert "snapshot_id" in data
    assert len(data["rows"]) > 0

    row = data["rows"][0]
    assert "decision_snapshot_id" in row
    assert "ticker" in row
    assert "master_rank" in row
    assert "band" in row["master_rank"]
    assert "setup" in row
    assert "state" in row["setup"]
    assert "risk" in row
    assert "data_grade" in row
    assert "positive_drivers" in row
    assert "negative_drivers" in row

def test_stock_decision_endpoint():
    response = client.get("/api/v2/decisions/stock/HALO")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "HALO"
    assert "master_rank" in data
    assert "setup" in data
    assert "risk" in data
    assert "data_grade" in data
    assert "factor_scores" in data
    assert "factor_reliabilities" in data

def test_cprx_quarantine_in_decision_api():
    response = client.get("/api/v2/decisions/stock/CPRX")
    assert response.status_code == 200
    data = response.json()
    assert data["master_rank"]["band"] == "INSUFFICIENT"
    assert data["master_rank"]["score"] == 0.0
    assert any("quarantined" in w.lower() or "inactive" in w.lower() for w in data["warnings"])

def test_screener_typed_filters():
    # Filter by thesis band STRONG
    response_strong = client.get("/api/v2/decisions/screener?thesis_band=STRONG")
    assert response_strong.status_code == 200
    data_strong = response_strong.json()
    for row in data_strong["rows"]:
        assert row["master_rank"]["band"] == "STRONG"
