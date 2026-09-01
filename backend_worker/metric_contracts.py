"""Canonical metric contracts (Ultimate Rebuild v3, section 8) — worker-side only.

Every vendor value must pass a canonical unit contract before any factor
computation. A column name is not a data contract: ``debt_to_equity`` may
arrive as percentage points (Yahoo-style, e.g. 89.94) or as a ratio (0.8),
and the scoring engine must never guess which one it received.

Contract rules (plan table 13):
- unit unknown            -> value is refused (quality flag UNIT_UNKNOWN)
- implausible value       -> flagged, never silently winsorized
- negative equity         -> representable, flagged, never zeroed
- missing value           -> explicit MISSING, never a positive default
"""
from __future__ import annotations

from dataclasses import dataclass

TRANSFORM_DEBT_TO_EQUITY_V1 = "metric_debt_to_equity_v1"

# Contract bounds after canonicalization (ratio, 1.0 = 100%). These flag
# implausible values; they are not a winsorization range.
DEBT_TO_EQUITY_PLAUSIBLE_MIN = -20.0
DEBT_TO_EQUITY_PLAUSIBLE_MAX = 20.0

_PERCENT_UNITS = {"percent", "percentage_points", "%", "pct"}
_RATIO_UNITS = {"ratio", "decimal"}


@dataclass(frozen=True)
class NormalizedMetric:
    metric_code: str
    value: float | None
    canonical_unit: str
    transform_version: str
    quality_flags: tuple[str, ...] = ()
    source_value: str | None = None
    source_unit: str | None = None


def normalize_debt_to_equity(value: object, *, source_unit: str | None) -> NormalizedMetric:
    """Canonicalize a vendor debt/equity value to a ratio (1.0 = 100%).

    ``source_unit`` must be stated by the provider adapter: ``percent`` (or
    ``percentage_points``) is divided by 100; ``ratio`` is kept as-is. Any
    other value quarantines the observation.
    """
    metric_code = "debt_to_equity_ratio"
    if value is None:
        return NormalizedMetric(
            metric_code, None, "ratio", TRANSFORM_DEBT_TO_EQUITY_V1,
            quality_flags=("MISSING",), source_value=None, source_unit=source_unit,
        )
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return NormalizedMetric(
            metric_code, None, "ratio", TRANSFORM_DEBT_TO_EQUITY_V1,
            quality_flags=("NON_NUMERIC",), source_value=str(value), source_unit=source_unit,
        )
    if source_unit in _PERCENT_UNITS:
        canonical = numeric / 100.0
    elif source_unit in _RATIO_UNITS:
        canonical = numeric
    else:
        return NormalizedMetric(
            metric_code, None, "ratio", TRANSFORM_DEBT_TO_EQUITY_V1,
            quality_flags=("UNIT_UNKNOWN",), source_value=str(value), source_unit=source_unit,
        )
    flags: list[str] = []
    if not DEBT_TO_EQUITY_PLAUSIBLE_MIN <= canonical <= DEBT_TO_EQUITY_PLAUSIBLE_MAX:
        flags.append("OUT_OF_PLAUSIBLE_BOUNDS")
    if canonical < 0:
        flags.append("NEGATIVE_EQUITY")
    return NormalizedMetric(
        metric_code, canonical, "ratio", TRANSFORM_DEBT_TO_EQUITY_V1,
        quality_flags=tuple(flags), source_value=str(value), source_unit=source_unit,
    )