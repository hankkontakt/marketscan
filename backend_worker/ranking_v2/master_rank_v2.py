"""
MasterRank v2 Core Model (Phase 3)
Calculates long-horizon thesis attractiveness (3-12m) using:
- 7 Structural factor blocks
- Reliability-weighted shrinkage to neutral (50)
- Thesis bands & coverage gates
- Transparent contribution attribution
"""
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from backend_worker.ranking_v2.factor_engine import (
    compute_quality_block,
    compute_growth_block,
    compute_valuation_block,
    compute_momentum_block,
    compute_revisions_block,
    compute_capital_allocation_block,
    compute_catalysts_block,
    FactorBlockResult
)

class ThesisBand(str, Enum):
    EXCEPTIONAL = "EXCEPTIONAL"
    STRONG = "STRONG"
    POSITIVE = "POSITIVE"
    MIXED = "MIXED"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"

FACTOR_WEIGHTS = {
    "quality": 0.25,
    "growth": 0.20,
    "valuation": 0.20,
    "momentum": 0.15,
    "revisions": 0.10,
    "capital_alloc": 0.05,
    "catalysts": 0.05,
}

class FactorDriver(BaseModel):
    factor_name: str
    label_sv: str
    raw_score: Optional[float]
    reliability: float
    contribution: float  # Score impact relative to 50

class MasterRankV2Result(BaseModel):
    master_rank: float
    thesis_band: ThesisBand
    weighted_coverage: float
    factor_scores: Dict[str, Optional[float]]
    factor_reliabilities: Dict[str, float]
    positive_drivers: List[FactorDriver]
    negative_drivers: List[FactorDriver]
    warnings: List[str] = Field(default_factory=list)
    model_version: str = "master_v2.0"

SV_LABELS = {
    "quality": "Kvalitet & Lönsamhet",
    "growth": "Tillväxtkvalitet",
    "valuation": "Värdering & Multiplar",
    "momentum": "Momentum & Relativ Styrka",
    "revisions": "Estimatrevideringar",
    "capital_alloc": "Kapitalallokering & Utdelning",
    "catalysts": "Händelseutfall & Rapporter",
}

def compute_master_rank_v2(
    data: Dict[str, Any],
    segment: str = "large_cap",
    is_tradable: bool = True
) -> MasterRankV2Result:
    """
    Compute MasterRank v2 for a security given raw data and segment.
    """
    warnings = []

    if not is_tradable:
        return MasterRankV2Result(
            master_rank=0.0,
            thesis_band=ThesisBand.INSUFFICIENT,
            weighted_coverage=0.0,
            factor_scores={},
            factor_reliabilities={},
            positive_drivers=[],
            negative_drivers=[],
            warnings=["Instrument is inactive or quarantined from active decisions"]
        )

    # Compute all 7 blocks
    blocks: Dict[str, FactorBlockResult] = {
        "quality": compute_quality_block(data),
        "growth": compute_growth_block(data),
        "valuation": compute_valuation_block(data),
        "momentum": compute_momentum_block(data),
        "revisions": compute_revisions_block(data),
        "capital_alloc": compute_capital_allocation_block(data),
        "catalysts": compute_catalysts_block(data),
    }

    base_score = 0.0
    weighted_coverage = 0.0
    drivers = []
    factor_scores = {}
    factor_reliabilities = {}

    for factor, weight in FACTOR_WEIGHTS.items():
        block = blocks[factor]
        s_i = block.score if block.score is not None else 50.0
        r_i = block.reliability if block.score is not None else 0.0

        factor_scores[factor] = block.score
        factor_reliabilities[factor] = r_i

        # Reliability shrinkage formula:
        # effective_factor = r_i * s_i + (1 - r_i) * 50
        effective_factor = (r_i * s_i) + ((1.0 - r_i) * 50.0)
        base_score += weight * effective_factor
        weighted_coverage += weight * r_i

        # Contribution relative to baseline 50
        contrib = weight * (effective_factor - 50.0)
        drivers.append(FactorDriver(
            factor_name=factor,
            label_sv=SV_LABELS.get(factor, factor),
            raw_score=block.score,
            reliability=round(r_i, 3),
            contribution=round(contrib, 2)
        ))

    base_score = round(max(0.0, min(100.0, base_score)), 2)
    weighted_coverage = round(weighted_coverage, 3)

    # Coverage thresholds
    min_strong_cov = 0.70 if segment in ("small_cap", "micro_cap") else 0.80

    if weighted_coverage < 0.65:
        thesis_band = ThesisBand.INSUFFICIENT
        warnings.append(f"Insufficient data coverage ({weighted_coverage:.1%}) for thesis verdict")
    elif base_score >= 85.0 and weighted_coverage >= 0.85:
        thesis_band = ThesisBand.EXCEPTIONAL
    elif base_score >= 75.0 and weighted_coverage >= min_strong_cov:
        thesis_band = ThesisBand.STRONG
    elif base_score >= 65.0:
        thesis_band = ThesisBand.POSITIVE
    elif base_score >= 50.0:
        thesis_band = ThesisBand.MIXED
    else:
        thesis_band = ThesisBand.WEAK

    # Separate positive and negative drivers sorted by absolute impact
    pos_drivers = sorted([d for d in drivers if d.contribution > 0.1], key=lambda d: d.contribution, reverse=True)
    neg_drivers = sorted([d for d in drivers if d.contribution < -0.1], key=lambda d: d.contribution)

    return MasterRankV2Result(
        master_rank=base_score,
        thesis_band=thesis_band,
        weighted_coverage=weighted_coverage,
        factor_scores=factor_scores,
        factor_reliabilities=factor_reliabilities,
        positive_drivers=pos_drivers,
        negative_drivers=neg_drivers,
        warnings=warnings
    )
