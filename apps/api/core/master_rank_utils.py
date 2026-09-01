"""
master_rank_utils.py — Pure Python utility functions for MasterRank tiers and signals.
No numpy or database dependencies.
"""
from __future__ import annotations

from typing import Optional

# ── Tiers ─────────────────────────────────────────────────────────────────────
TIER_T1 = 75.0
TIER_T2 = 65.0
TIER_T3 = 50.0

# ── Segment-relativa tiers (small/micro har tunnare data = lägre absolut rank) ──
TIER_T1_SMALL = 62.0    # STARK-tröskel för small/micro (vs 75 för large)
TIER_T2_SMALL = 50.0    # OK-tröskel (vs 65)
TIER_T3_SMALL = 38.0    # VÄNTA-tröskel (vs 50)


def tier_of(
    rank: Optional[float],
    excluded: bool = False,
    pit: str = "READY",
    segment: str | None = None,
) -> str:
    """Returnerar MasterRank-tier baserat på rank, segment och PIT-status."""
    if rank is None or excluded:
        return "EXCLUDED"
    is_small = segment in ("small_cap", "micro_cap")
    t1 = TIER_T1_SMALL if is_small else TIER_T1
    t2 = TIER_T2_SMALL if is_small else TIER_T2
    t3 = TIER_T3_SMALL if is_small else TIER_T3
    if pit == "PENDING" and rank >= t1:
        return "T2"          # PENDING kan aldrig nå T1 (kvalitetsdata saknas)
    if rank >= t1:
        return "T1"
    if rank >= t2:
        return "T2"
    if rank >= t3:
        return "T3"
    return "T4"


def signal_from_tier(tier: str | None) -> str:
    """MasterRank-tier → entry_signal (motsv. köplägesetikett).

    T1 (≥75) → STARK · T2 (65-74) → OK · T3 (50-64) → VÄNTA ·
    T4 (<50) / EXCLUDED → EJ_AKTUELL.
    """
    if tier == "T1":
        return "STARK"
    if tier == "T2":
        return "OK"
    if tier == "T3":
        return "VÄNTA"
    return "EJ_AKTUELL"
