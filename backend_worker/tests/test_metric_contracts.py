"""Canonical metric contracts — unit normalization tests (plan section 8)."""
import pytest

from backend_worker.metric_contracts import (
    TRANSFORM_DEBT_TO_EQUITY_V1,
    normalize_debt_to_equity,
)


def test_percentage_points_are_divided_by_100():
    # The live debt_to_equity mismatch: Yahoo-style percentage points like
    # 89.94, 99.89 and 139.66 were previously treated as ratios.
    metric = normalize_debt_to_equity(89.94, source_unit="percent")
    assert metric.value == pytest.approx(0.8994)
    assert metric.canonical_unit == "ratio"
    assert metric.transform_version == TRANSFORM_DEBT_TO_EQUITY_V1
    assert metric.quality_flags == ()


def test_ratio_is_kept_as_is():
    metric = normalize_debt_to_equity(0.8, source_unit="ratio")
    assert metric.value == pytest.approx(0.8)
    assert metric.quality_flags == ()


def test_unit_unknown_quarantines_the_value():
    metric = normalize_debt_to_equity(0.8, source_unit=None)
    assert metric.value is None
    assert "UNIT_UNKNOWN" in metric.quality_flags


def test_missing_value_is_explicit_not_positive_default():
    metric = normalize_debt_to_equity(None, source_unit="ratio")
    assert metric.value is None
    assert "MISSING" in metric.quality_flags


def test_negative_equity_is_flagged_not_zeroed():
    metric = normalize_debt_to_equity(-1.5, source_unit="ratio")
    assert metric.value == pytest.approx(-1.5)
    assert "NEGATIVE_EQUITY" in metric.quality_flags


def test_implausible_value_is_flagged_not_winsorized():
    metric = normalize_debt_to_equity(9999, source_unit="percent")
    assert metric.value == pytest.approx(99.99)
    assert "OUT_OF_PLAUSIBLE_BOUNDS" in metric.quality_flags


def test_non_numeric_value_is_quarantined():
    metric = normalize_debt_to_equity("n/a", source_unit="ratio")
    assert metric.value is None
    assert "NON_NUMERIC" in metric.quality_flags