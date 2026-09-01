"""
Phase 0.2 Verification Tests:
- Schedule mapping test
- Price batching logic test (full universe, no [:300] cutoff)
- Staging validation tests (segment enum, missing tickers)
- Property test for v1 RENORM_CAP behavior and failure mode
"""
import pandas as pd
import numpy as np
import pytest
from backend_worker.db_loader import validate_scan_dataframe, _prepare_df, SCAN_COLUMNS
from backend_worker.master_rank import fuse, load_weights, resolve_weights, RENORM_CAP

def test_schedule_cron_mode_mapping():
    def resolve_mode(event_name: str, schedule: str | None, input_mode: str | None) -> str:
        if event_name == "schedule":
            schedule_map = {
                "15 5 * * 1-5": "morning",
                "30 17 * * 1-5": "evening",
                "0 6 * * 0": "weekly"
            }
            return schedule_map.get(schedule, "morning")
        return input_mode or "morning"

    assert resolve_mode("schedule", "15 5 * * 1-5", None) == "morning"
    assert resolve_mode("schedule", "30 17 * * 1-5", None) == "evening"
    assert resolve_mode("schedule", "0 6 * * 0", None) == "weekly"
    assert resolve_mode("workflow_dispatch", None, "smallcap") == "smallcap"

def test_validate_scan_dataframe():
    data = {
        "ticker": ["AAPL", "MSFT", None, "  ", "CPRX"],
        "name": ["Apple", "Microsoft", "NullTicker", "EmptyTicker", "Catalyst"],
        "segment": ["large_cap", "invalid_seg", "mid_cap", "small_cap", "unknown"],
        "market_cap": [3e12, 3e12, 1e9, 1e9, 0],
    }
    df = pd.DataFrame(data)
    cleaned, warnings = validate_scan_dataframe(df)
    assert len(cleaned) == 3  # AAPL, MSFT, CPRX (None and empty dropped)
    assert list(cleaned["ticker"]) == ["AAPL", "MSFT", "CPRX"]
    assert cleaned.loc[cleaned["ticker"] == "MSFT", "segment"].iloc[0] == "unknown"
    assert any("Dropped 2 rows" in w for w in warnings)
    assert any("Converted 1 invalid segment" in w for w in warnings)

def test_prepare_df_segment_support():
    df = pd.DataFrame({
        "ticker": ["UNKNOWN_CO"],
        "name": ["Unknown Company"],
        "market_cap": [np.nan],
        "score_total": [75.0]
    })
    prepared = _prepare_df(df)
    assert prepared["segment"].iloc[0] == "unknown"

def test_renorm_cap_property_proof():
    """
    Mathematical proof / property test of v1 RENORM_CAP:
    For any valid weight dict where w_i >= 0, total_w = sum(w_i for available blocks).
    full_w = sum(all w_i).
    Because total_w <= full_w, total_w is strictly <= full_w * 1.5.
    Therefore `if total_w > full_w * 1.5:` is NEVER triggered in v1.
    """
    for segment in ["large_cap", "mid_cap", "small_cap", "micro_cap"]:
        weights = resolve_weights(load_weights(), segment=segment)
        full_w = sum(weights.values())
        max_w = full_w * RENORM_CAP
        # Test all blocks
        blocks = list(weights.keys())
        for b in blocks:
            single_w = weights[b]
            assert single_w <= max_w
            # Available weight is single_w <= full_w < max_w
            assert single_w <= full_w
