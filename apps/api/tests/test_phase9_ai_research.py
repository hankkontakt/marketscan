"""
Phase 9 Verification Tests: AI Research v2
- Grounded narrative generator endpoint /api/v2/ai/thesis-report/{ticker}
- Canonical grounding invariant (strict fact anchoring)
- Thesis report structured sections validation
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_ai_thesis_report_endpoint():
    response = client.get("/api/v2/ai/thesis-report/HALO")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "HALO"
    assert "master_rank" in data
    assert "thesis_band" in data
    assert "setup_state" in data
    assert "risk_state" in data
    assert "data_grade" in data
    assert "executive_summary" in data
    assert "sections" in data
    assert len(data["sections"]) >= 4

    # Check sections titles
    titles = [s["title"] for s in data["sections"]]
    assert any("Huvudtes" in t for t in titles)
    assert any("Timing" in t for t in titles)
    assert any("Risk" in t for t in titles)
    assert any("Slutsats" in t for t in titles)

def test_canonical_grounding_invariant():
    response = client.get("/api/v2/ai/thesis-report/HALO")
    data = response.json()
    facts = data["grounded_canonical_facts"]

    # Verify executive summary references the exact score
    assert f"{facts['master_rank']:.0f}/100" in data["executive_summary"]
    assert facts["thesis_band"] in data["executive_summary"]
    assert facts["data_grade"] in data["executive_summary"]
