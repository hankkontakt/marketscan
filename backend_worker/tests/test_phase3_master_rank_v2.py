"""
Phase 3 Verification Tests: MasterRank v2 Challenger
- Reliability shrinkage to neutral 50
- Zero named-stock production branches in ranking_v2
- Thesis band classification & coverage gating
- Mathematical contribution attribution sum
- Benchmark cohort evaluation
"""
from pathlib import Path
import pytest
from backend_worker.ranking_v2.master_rank_v2 import compute_master_rank_v2, ThesisBand
from backend_worker.ranking_v2.factor_engine import compute_quality_block

def test_reliability_shrinkage_missing_factors():
    # Complete high quality profile
    full_data = {
        "roe": 0.35, "operating_margin": 0.28, "piotroski_f": 9, "debt_to_equity": 0.1,
        "revenue_growth": 0.25, "earnings_growth": 0.30,
        "pe_forward": 12.0,
        "score_momentum": 85.0,
        "target_revision_30d": 0.08, "analyst_count": 15,
        "dividend_yield": 0.02,
        "earnings_surprise_pct": 0.06
    }
    res_full = compute_master_rank_v2(full_data)
    assert res_full.weighted_coverage >= 0.85
    assert res_full.thesis_band in (ThesisBand.STRONG, ThesisBand.EXCEPTIONAL)
    assert res_full.master_rank > 75.0

    # Missing valuation and revisions (thin data)
    thin_data = {
        "roe": 0.35, "operating_margin": 0.28, "piotroski_f": 9, "debt_to_equity": 0.1,
        "revenue_growth": 0.25,
        "score_momentum": 85.0
    }
    res_thin = compute_master_rank_v2(thin_data)
    # The missing blocks shrink to 50 instead of upweighting the remaining blocks
    assert res_thin.factor_reliabilities["valuation"] == 0.0
    assert res_thin.factor_reliabilities["revisions"] == 0.0
    assert res_thin.master_rank < res_full.master_rank  # Lower than full due to neutral shrinkage

def test_zero_named_tickers_in_ranking_v2():
    ranking_v2_dir = Path("backend_worker/ranking_v2")
    for py_file in ranking_v2_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        # Invariant: No named ticker branches in factor engine
        for forbidden in ["7148.T", "TXT.WA", "HARVIA.HE", "NCAB.ST", "CPRX"]:
            assert forbidden not in content, f"Forbidden ticker {forbidden} found in {py_file.name}"

def test_coverage_gate_insufficient():
    # Only 1 factor present (e.g. momentum) -> coverage < 0.65 -> INSUFFICIENT
    data = {"score_momentum": 95.0}
    res = compute_master_rank_v2(data)
    assert res.weighted_coverage < 0.65
    assert res.thesis_band == ThesisBand.INSUFFICIENT
    assert any("Insufficient data coverage" in w for w in res.warnings)

def test_contribution_attribution_sum():
    data = {
        "roe": 0.25, "operating_margin": 0.20, "piotroski_f": 7, "debt_to_equity": 0.3,
        "revenue_growth": 0.15,
        "pe_forward": 20.0,
        "score_momentum": 70.0,
        "target_revision_30d": 0.02, "analyst_count": 5
    }
    res = compute_master_rank_v2(data)
    total_contrib = sum(d.contribution for d in res.positive_drivers) + sum(d.contribution for d in res.negative_drivers)
    # Total contribution + neutral 50 ≈ master_rank
    assert pytest.approx(res.master_rank, abs=0.5) == 50.0 + total_contrib

def test_cprx_inactive_tradability_gate():
    data = {"roe": 0.40, "score_momentum": 90.0}
    res = compute_master_rank_v2(data, is_tradable=False)
    assert res.thesis_band == ThesisBand.INSUFFICIENT
    assert res.master_rank == 0.0
