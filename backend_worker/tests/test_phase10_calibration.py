"""
Phase 10 Verification Tests: Research Engine + Calibration
- Information Coefficient (IC) & Rank IC
- Quintile spread & monotonic sorting
- Autocorrelation / rank stability (>0.85)
- Degenerate input handling
"""
import pytest
import numpy as np
from backend_worker.research.calibration_engine import compute_model_calibration

def test_calibration_metrics_positive_alpha():
    np.random.seed(42)
    n = 100
    # True signal with noise
    signal = np.random.uniform(20, 90, size=n)
    noise = np.random.normal(0, 5, size=n)
    # Forward 6m returns correlate positively with signal
    forward_ret = (signal / 100.0) * 0.25 + noise * 0.01

    metrics = compute_model_calibration(
        predicted_scores=list(signal),
        forward_returns=list(forward_ret),
        model_name="master_v2.0"
    )

    assert metrics.sample_size == 100
    assert metrics.rank_ic > 0.60
    assert metrics.rank_ic_t_stat > 3.0
    assert metrics.quintile_spread > 0.10
    assert metrics.q1_mean_return > metrics.q5_mean_return

def test_rank_autocorrelation_stability():
    np.random.seed(42)
    scores_m1 = np.random.uniform(30, 85, size=50)
    # Month 2 scores have minor monthly updates
    scores_m2 = scores_m1 + np.random.normal(0, 2, size=50)

    metrics = compute_model_calibration(
        predicted_scores=list(scores_m2),
        forward_returns=[0.05] * 50,
        prior_scores=list(scores_m1),
        model_name="master_v2.0"
    )
    assert metrics.rank_autocorrelation_30d > 0.85

def test_degenerate_empty_handling():
    metrics = compute_model_calibration([], [])
    assert metrics.sample_size == 0
    assert metrics.rank_ic == 0.0
