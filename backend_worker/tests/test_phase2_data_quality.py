"""
Phase 2 Verification Tests: Provenance & Data Quality Platform
- ObservedValue schema & point-in-time invariant
- Reliability scoring by SourceTier & QualityFlags
- LiquidityEngine real ADV & LiquidityGrade (A-F) deterministic calculations
- DataQualityReport coverage and SLA verification
"""
from datetime import datetime, date, timedelta, timezone
import pytest
import numpy as np
import pandas as pd
from backend_worker.data_contracts.observed_value import ObservedValue, SourceTier, QualityFlag
from backend_worker.data_contracts.liquidity_engine import compute_liquidity_grade
from backend_worker.data_contracts.quality_checker import evaluate_data_quality

def test_observed_value_point_in_time():
    now = datetime.now(timezone.utc)
    # Valid observation: available today or in the past
    obs_valid = ObservedValue[float](
        security_id="sec-1",
        field_name="pe_trailing",
        value=25.4,
        source_id="BORSDATA_API",
        source_tier=SourceTier.B,
        available_at=now - timedelta(days=1),
        fetched_at=now
    )
    assert obs_valid.is_point_in_time_valid is True

    # Look-ahead violation: available_at is in the future relative to fetched_at
    obs_future = ObservedValue[float](
        security_id="sec-2",
        field_name="pe_trailing",
        value=20.0,
        source_id="BORSDATA_API",
        source_tier=SourceTier.B,
        available_at=now + timedelta(days=5),
        fetched_at=now
    )
    assert obs_future.is_point_in_time_valid is False

def test_source_tier_reliability_scoring():
    now = datetime.now(timezone.utc)
    obs_tier_a = ObservedValue[float](
        security_id="sec-1", field_name="net_income", value=1e6,
        source_id="EXCHANGE_OFFICIAL", source_tier=SourceTier.A
    )
    obs_tier_b = ObservedValue[float](
        security_id="sec-1", field_name="net_income", value=1e6,
        source_id="BORSDATA_API", source_tier=SourceTier.B
    )
    obs_tier_c = ObservedValue[float](
        security_id="sec-1", field_name="net_income", value=1e6,
        source_id="FINNHUB_API", source_tier=SourceTier.C
    )
    obs_tier_d = ObservedValue[float](
        security_id="sec-1", field_name="net_income", value=1e6,
        source_id="AI_DOCUMENT_RAG", source_tier=SourceTier.D
    )

    assert obs_tier_a.reliability_score == 1.0
    assert obs_tier_b.reliability_score == 0.95
    assert obs_tier_c.reliability_score == 0.80
    assert obs_tier_d.reliability_score == 0.50

    # Test quality flag degradation
    obs_stale = ObservedValue[float](
        security_id="sec-1", field_name="net_income", value=1e6,
        source_id="BORSDATA_API", source_tier=SourceTier.B,
        quality_flags=[QualityFlag.STALE]
    )
    assert obs_stale.reliability_score < 0.95

def test_liquidity_grade_large_cap_vs_micro_cap():
    # TSMC / Apple profile: 5M shares/day at $150 = $750M ADV
    prices_large = [150.0] * 20
    vols_large = [5_000_000.0] * 20
    liq_large = compute_liquidity_grade(vols_large, prices_large, fx_to_usd=1.0)
    assert liq_large.liquidity_grade == "A"
    assert liq_large.median_adv_usd_20d >= 10_000_000
    assert liq_large.is_tradable_for_institutions is True

    # Microcap illiquid profile: 200 shares/day at $10 with 5 zero-volume days
    prices_micro = [10.0] * 20
    vols_micro = [200.0] * 15 + [0.0] * 5
    liq_micro = compute_liquidity_grade(vols_micro, prices_micro, fx_to_usd=1.0)
    assert liq_micro.liquidity_grade == "F"
    assert liq_micro.zero_volume_days_20d == 5
    assert liq_micro.is_tradable_for_institutions is False

def test_data_quality_report_evaluation():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C", "D"],
        "segment": ["large_cap", "large_cap", "small_cap", "small_cap"],
        "price": [100.0, 105.0, 25.0, np.nan],
        "pe_trailing": [15.0, 20.0, 12.0, np.nan],
        "roe": [0.20, 0.25, 0.10, np.nan]
    })
    report = evaluate_data_quality(df)
    assert report.total_rows == 4
    assert report.segment_breakdowns["large_cap"]["price_coverage"] == 1.0
    assert report.segment_breakdowns["small_cap"]["price_coverage"] == 0.5
    assert len(report.anomalies) > 0
