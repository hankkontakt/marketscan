"""
Phase 0.1 Verification Tests:
- Feature flag defaults and environment override resolution
- Benchmark cohort fixture validity and completeness
- Rollback documentation existence
"""
import os
import json
from pathlib import Path
from apps.api.core.feature_flags import get_feature_flags, is_feature_enabled, DEFAULT_FLAGS

def test_feature_flags_defaults():
    flags = get_feature_flags()
    assert isinstance(flags, dict)
    assert flags["decision_v2_api"] is False
    assert flags["screener_v2"] is False
    assert flags["setup_state_shadow"] is True
    assert is_feature_enabled("decision_v2_api") is False

def test_feature_flags_env_override(monkeypatch):
    monkeypatch.setenv("MARKETSCAN_FF_DECISION_V2_API", "true")
    monkeypatch.setenv("MARKETSCAN_FF_SCREENER_V2", "1")
    assert is_feature_enabled("decision_v2_api") is True
    assert is_feature_enabled("screener_v2") is True

def test_benchmark_cohort_fixture():
    fixture_path = Path("data/fixtures/benchmark_cohort_v1.json")
    assert fixture_path.exists()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["version"] == "1.0"
    tickers = [item["ticker"] for item in data["cohort"]]
    assert "2330.TW" in tickers
    assert "HALO" in tickers
    assert "APP" in tickers
    assert "TXT.WA" in tickers
    assert "CPRX" in tickers
    assert len(tickers) == 21

def test_migration_docs_exist():
    doc_path = Path("docs/MIGRATION_V2.md")
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "Rollback Procedures" in content
