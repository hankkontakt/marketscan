"""
apps/api/core/segments.py — Central segment thresholds and derivation for apps/api.

NOTE (Vercel rule): apps/api NEVER imports backend_worker.
Thresholds here MUST match backend_worker/db_loader.py (lines 34-38).
"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Segment thresholds in absolute USD.
# Cross-reference: backend_worker/db_loader.py:34-38
SEGMENT_THRESHOLDS = {
    "large_cap": 10_000_000_000,  # USD (>= 10B)
    "mid_cap": 2_000_000_000,     # USD (>= 2B)
    "small_cap": 300_000_000,     # USD (>= 300M)
}

SegmentType = Literal["large_cap", "mid_cap", "small_cap", "micro_cap", "unknown"]


def segment_from_market_cap(market_cap_usd: float | None) -> SegmentType:
    """Determine segment string from market cap in USD.

    Returns 'unknown' for None/zero/negative values (never dumps to micro_cap).
    Applies guard for probable million-unit values (0 < mc < 1e6).
    """
    if market_cap_usd is None or market_cap_usd <= 0:
        return "unknown"
    mc = float(market_cap_usd)
    if 0 < mc < 1_000_000:
        logger.warning(
            "market_cap %s scaled by 1e6 as probable million-unit -> %s",
            mc,
            mc * 1_000_000,
        )
        mc *= 1_000_000
    if mc > 1e13:
        logger.warning("market_cap %s unusually large (>1e13 USD)", mc)
    if mc >= SEGMENT_THRESHOLDS["large_cap"]:
        return "large_cap"
    if mc >= SEGMENT_THRESHOLDS["mid_cap"]:
        return "mid_cap"
    if mc >= SEGMENT_THRESHOLDS["small_cap"]:
        return "small_cap"
    return "micro_cap"


def segment_from_finnhub_mcap(market_cap_millions: float | None) -> SegmentType:
    """Determine segment from Finnhub marketCapitalization (in USD millions)."""
    if market_cap_millions is None or market_cap_millions <= 0:
        return "unknown"
    return segment_from_market_cap(float(market_cap_millions) * 1_000_000)
