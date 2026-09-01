"""
Phase 11 Verification Tests: Portfolio Construction v2
- Max position weight constraint (<= 10%)
- Exclusion of DataGrade E/F and VERY_HIGH risk
- Liquidity capacity limit (<= 2% 20d ADV)
- Deferral of new entries with DAMAGED setup
- Order action generation
"""
import pytest
from backend_worker.portfolio_v2.optimizer import optimize_portfolio_v2, PortfolioCandidate

def test_portfolio_weight_constraints_and_filtering():
    candidates = [
        PortfolioCandidate(ticker="TSMC", master_rank=88.0, setup_state="CONFIRMED", data_grade="A", median_adv_usd_20d=50_000_000.0),
        PortfolioCandidate(ticker="HALO", master_rank=82.0, setup_state="PULLBACK", data_grade="A", median_adv_usd_20d=10_000_000.0),
        PortfolioCandidate(ticker="BAD_DATA", master_rank=95.0, setup_state="CONFIRMED", data_grade="F"),
        PortfolioCandidate(ticker="VERY_RISKY", master_rank=90.0, risk_state="VERY_HIGH", data_grade="B"),
        PortfolioCandidate(ticker="DAMAGED_ENTRY", master_rank=85.0, setup_state="DAMAGED", data_grade="A", current_weight=0.0),
    ]

    res = optimize_portfolio_v2(
        candidates=candidates,
        max_position_weight=0.10,
        portfolio_aum_usd=100_000.0
    )

    tickers_selected = [tw.ticker for tw in res.target_weights]
    assert "TSMC" in tickers_selected
    assert "HALO" in tickers_selected
    assert "BAD_DATA" not in tickers_selected
    assert "VERY_RISKY" not in tickers_selected
    assert "DAMAGED_ENTRY" not in tickers_selected

    for tw in res.target_weights:
        assert tw.target_weight <= 0.101

def test_liquidity_capacity_cap():
    # Microcap with only $10,000 ADV
    # 2% of $10,000 = $200 max position. On $100,000 AUM, max weight = 0.002 (0.2%)
    candidates = [
        PortfolioCandidate(ticker="MICRO", master_rank=90.0, setup_state="CONFIRMED", data_grade="B", median_adv_usd_20d=10_000.0),
        PortfolioCandidate(ticker="LIQUID", master_rank=80.0, setup_state="CONFIRMED", data_grade="A", median_adv_usd_20d=20_000_000.0),
    ]

    res = optimize_portfolio_v2(
        candidates=candidates,
        max_position_weight=0.10,
        portfolio_aum_usd=100_000.0
    )

    micro_tw = next(tw for tw in res.target_weights if tw.ticker == "MICRO")
    assert micro_tw.target_weight <= 0.0021  # Enforces liquidity limit
