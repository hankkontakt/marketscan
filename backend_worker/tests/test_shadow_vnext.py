"""Shadow vNext engine tests (Phase 6)."""
from datetime import date

import pytest

from backend_worker.shadow_vnext import compute_risk_vnext, compute_setup_vnext


def base_row(**overrides):
    values = {
        "ticker": "MSFT", "entry_signal": "STARK", "trend_tech": "Upptrend",
        "pit_status": "READY", "low_liquidity": False,
        "warning_flags": [], "data_missing": [],
        "master_rank": 82.0, "master_rank_pctl": 95.0, "quality_z": 80.0,
        "value_z": 55.0, "momentum_z": 70.0, "analyst_z": 60.0, "tech_z": 70.0,
        "insider_z": 50.0, "catalyst_z": 50.0, "growth_z": 65.0,
    }
    values.update(overrides)
    return values


def test_strong_signal_with_uptrend_is_ready():
    state, reasons = compute_setup_vnext(base_row(), date(2026, 9, 1))
    assert state == "READY"
    assert "strong_signal_and_uptrend" in reasons


def test_catalyst_within_14_days_is_wait():
    row = base_row(catalyst_next="2026-09-10:earnings")
    state, reasons = compute_setup_vnext(row, date(2026, 9, 1))
    assert state == "WAIT"
    assert "event_within_14d" in reasons


def test_event_beyond_horizon_keeps_normal_setup():
    row = base_row(catalyst_next="2026-12-10:earnings", entry_signal="STARK", trend_tech="Upptrend")
    state, _ = compute_setup_vnext(row, date(2026, 9, 1))
    assert state == "READY"


def test_low_coverage_is_insufficient():
    row = base_row(master_rank=None, master_rank_pctl=None, quality_z=None, value_z=None,
                   momentum_z=None, analyst_z=None, tech_z=None, insider_z=None,
                   catalyst_z=None, growth_z=None)
    state, reasons = compute_setup_vnext(row, date(2026, 9, 1))
    assert state == "INSUFFICIENT"
    assert "coverage_below_0_5" in reasons


def test_sideways_trend_is_wait():
    row = base_row(trend_tech="Sidled")
    state, _ = compute_setup_vnext(row, date(2026, 9, 1))
    assert state == "WAIT"


def test_stale_pit_is_critical_risk():
    state, reasons = compute_risk_vnext(base_row(pit_status="STALE"))
    assert state == "CRITICAL"
    assert "stale_pit" in reasons


def test_low_liquidity_is_elevated_risk():
    state, reasons = compute_risk_vnext(base_row(low_liquidity=True))
    assert state == "ELEVATED"
    assert "low_liquidity" in reasons


def test_clean_row_is_normal_risk():
    state, reasons = compute_risk_vnext(base_row())
    assert state == "NORMAL"
    assert reasons == []


def test_warnings_elevate_risk():
    state, reasons = compute_risk_vnext(base_row(warning_flags=["OVERBOUGHT"]))
    assert state == "ELEVATED"
    assert any(reason.startswith("warnings:") for reason in reasons)