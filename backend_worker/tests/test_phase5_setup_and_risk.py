"""
Phase 5 Verification Tests: SetupState & Risk v1 Shadow
- APP / Text post-drop DAMAGED setup vs fundamental thesis separation
- HALO post-run ATR EXTENDED setup with STRONG thesis
- Event window EVENT_RISK setup
- RiskState multi-dimensional combination (leverage, liquidity, volatility)
- DataGrade A-F computation
"""
import pytest
from backend_worker.setup.setup_engine import compute_setup_state, SetupState
from backend_worker.risk.risk_engine import compute_risk_state, compute_data_grade, RiskState, DataGrade
from backend_worker.ranking_v2.master_rank_v2 import compute_master_rank_v2, ThesisBand

def test_applovin_separation_strong_thesis_damaged_setup():
    # AppLovin post-earnings reset: strong fundamentals but -16% gap down
    app_fundamentals = {
        "roe": 0.38, "operating_margin": 0.32, "piotroski_f": 8, "debt_to_equity": 0.8,
        "revenue_growth": 0.30, "earnings_growth": 0.40,
        "pe_forward": 22.0, "score_momentum": 80.0
    }
    thesis_res = compute_master_rank_v2(app_fundamentals)
    setup_res = compute_setup_state(
        price=75.0, ma20=88.0, ma50=85.0, ma200=70.0, atr=3.5, rsi_14=32.0,
        recent_gap_pct=-0.16
    )

    # Core separation: Thesis is STRONG/POSITIVE, Setup is DAMAGED
    assert thesis_res.thesis_band in (ThesisBand.STRONG, ThesisBand.POSITIVE)
    assert setup_res.state == SetupState.DAMAGED
    assert "SEVERE_POST_EVENT_GAP_DOWN" in setup_res.reason_codes

def test_halozyme_separation_strong_thesis_extended_setup():
    # Halozyme: strong fundamentals, high momentum, but stretched >2.5 ATR above MA20
    halo_fundamentals = {
        "roe": 0.30, "operating_margin": 0.45, "piotroski_f": 9, "debt_to_equity": 0.2,
        "revenue_growth": 0.20, "pe_forward": 15.0, "score_momentum": 92.0
    }
    thesis_res = compute_master_rank_v2(halo_fundamentals)
    setup_res = compute_setup_state(
        price=62.0, ma20=50.0, ma50=46.0, ma200=40.0, atr=3.0, rsi_14=82.0
    )

    assert thesis_res.thesis_band in (ThesisBand.STRONG, ThesisBand.POSITIVE)
    assert setup_res.state == SetupState.EXTENDED
    assert "STATISTICALLY_EXTENDED_VS_ATR_MA" in setup_res.reason_codes

def test_event_risk_setup():
    setup_res = compute_setup_state(
        price=100.0, ma20=98.0, ma50=95.0, ma200=90.0, atr=2.0, rsi_14=60.0,
        days_to_earnings=3
    )
    assert setup_res.state == SetupState.EVENT_RISK
    assert "EARNINGS_INSIDE_7D_WINDOW" in setup_res.reason_codes

def test_risk_state_and_data_grade():
    # High debt + illiquid stock -> VERY_HIGH risk
    risk_res = compute_risk_state(
        liquidity_grade="F",
        debt_to_equity=3.2,
        volatility_20d=0.55,
        weighted_coverage=0.72
    )
    assert risk_res.risk_state == RiskState.VERY_HIGH
    assert risk_res.dominant_risk == "LEVERAGE_AND_ILLIQUIDITY"
    assert risk_res.data_grade == DataGrade.C

    # High coverage active stock -> DataGrade A
    grade_a = compute_data_grade(weighted_coverage=0.94, has_price=True, is_tradable=True)
    assert grade_a == DataGrade.A

    # Delisted stock -> DataGrade F
    grade_f = compute_data_grade(weighted_coverage=0.95, has_price=True, is_tradable=False)
    assert grade_f == DataGrade.F
