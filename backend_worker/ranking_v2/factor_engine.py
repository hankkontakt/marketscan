"""
Factor Engine v2 (Phase 3)
Calculates 7 distinct structural factor scores and reliabilities:
1. Quality (25%)
2. Growth (20%)
3. Valuation (20%)
4. Momentum (15%)
5. Estimate Revisions (10%)
6. Capital Allocation / Ownership (5%)
7. Directional Catalysts (5%)
"""
from typing import Dict, Any, Optional, Tuple
import numpy as np
from pydantic import BaseModel

class FactorBlockResult(BaseModel):
    score: Optional[float] = None       # 0.0 - 100.0 (None if data missing)
    reliability: float = 0.0           # 0.0 - 1.0 (0.0 if missing)
    components: Dict[str, Any] = {}

def _clip100(val: Optional[float]) -> Optional[float]:
    if val is None or np.isnan(val):
        return None
    return float(max(0.0, min(100.0, val)))

# 1. Quality Block (25%)
def compute_quality_block(data: Dict[str, Any]) -> FactorBlockResult:
    roe = data.get("roe") or data.get("roe_raw")
    roa = data.get("roa") or data.get("roa_raw")
    gm = data.get("gross_margin")
    om = data.get("operating_margin")
    f_score = data.get("piotroski_f")
    de = data.get("debt_to_equity")

    scores = []
    weights = []

    # Profitability (ROE / ROA)
    if roe is not None and not np.isnan(roe):
        # 15% ROE is neutral 50; 30%+ is 85+; negative ROE is penalized
        s_roe = 50.0 + (roe - 0.15) * 200.0
        scores.append(_clip100(s_roe))
        weights.append(0.35)

    if om is not None and not np.isnan(om):
        # 12% OM is neutral 50; >25% is high
        s_om = 50.0 + (om - 0.12) * 200.0
        scores.append(_clip100(s_om))
        weights.append(0.25)

    if f_score is not None and not np.isnan(f_score):
        # F-score 0-9: 5 is neutral 50, 8-9 is 85-100
        s_f = (float(f_score) / 9.0) * 100.0
        scores.append(_clip100(s_f))
        weights.append(0.20)

    if de is not None and not np.isnan(de):
        # Lower debt is safer (net cash / low D/E = high score)
        s_de = max(0.0, 100.0 - (de * 50.0))
        scores.append(_clip100(s_de))
        weights.append(0.20)

    if not scores:
        return FactorBlockResult(score=None, reliability=0.0)

    total_w = sum(weights)
    final_score = sum(s * w for s, w in zip(scores, weights)) / total_w
    rel = min(1.0, total_w / 0.8)  # High reliability if at least 80% weighted metrics present

    return FactorBlockResult(
        score=round(final_score, 2),
        reliability=round(rel, 3),
        components={"roe": roe, "om": om, "piotroski_f": f_score, "de": de}
    )

# 2. Growth Block (20%)
def compute_growth_block(data: Dict[str, Any]) -> FactorBlockResult:
    rev_g = data.get("revenue_growth") or data.get("revenue_growth_raw")
    earn_g = data.get("earnings_growth") or data.get("earnings_growth_raw")

    scores = []
    weights = []

    if rev_g is not None and not np.isnan(rev_g):
        # 10% rev growth is neutral 50; 25%+ is 80+
        s_rev = 50.0 + (rev_g - 0.10) * 150.0
        scores.append(_clip100(s_rev))
        weights.append(0.60)

    if earn_g is not None and not np.isnan(earn_g):
        s_earn = 50.0 + (earn_g - 0.10) * 120.0
        scores.append(_clip100(s_earn))
        weights.append(0.40)

    if not scores:
        return FactorBlockResult(score=None, reliability=0.0)

    total_w = sum(weights)
    final_score = sum(s * w for s, w in zip(scores, weights)) / total_w
    rel = min(1.0, total_w / 0.8)

    return FactorBlockResult(
        score=round(final_score, 2),
        reliability=round(rel, 3),
        components={"revenue_growth": rev_g, "earnings_growth": earn_g}
    )

# 3. Valuation Block (20%)
def compute_valuation_block(data: Dict[str, Any]) -> FactorBlockResult:
    pe_t = data.get("pe_trailing") or data.get("pe_trailing_raw")
    pe_f = data.get("pe_forward") or data.get("pe_forward_raw")

    scores = []
    weights = []

    # Forward PE preferred
    if pe_f is not None and not np.isnan(pe_f) and pe_f > 0:
        # P/E 15 is neutral 50; P/E 8 is 80; P/E 35 is 20
        s_pe_f = max(0.0, 100.0 - (pe_f * 2.5))
        scores.append(_clip100(s_pe_f))
        weights.append(0.60)
    elif pe_t is not None and not np.isnan(pe_t) and pe_t > 0:
        s_pe_t = max(0.0, 100.0 - (pe_t * 2.2))
        scores.append(_clip100(s_pe_t))
        weights.append(0.50)

    if not scores:
        return FactorBlockResult(score=None, reliability=0.0)

    total_w = sum(weights)
    final_score = sum(s * w for s, w in zip(scores, weights)) / total_w
    rel = min(1.0, total_w / 0.5)

    return FactorBlockResult(
        score=round(final_score, 2),
        reliability=round(rel, 3),
        components={"pe_forward": pe_f, "pe_trailing": pe_t}
    )

# 4. Momentum Block (15%) - Clean 6-12m cross-sectional momentum, no technical overlap
def compute_momentum_block(data: Dict[str, Any]) -> FactorBlockResult:
    mom = data.get("score_momentum") or data.get("momentum_z")
    if mom is not None and not np.isnan(mom):
        return FactorBlockResult(
            score=round(float(_clip100(mom)), 2),
            reliability=0.90,
            components={"raw_momentum": mom}
        )
    return FactorBlockResult(score=None, reliability=0.0)

# 5. Estimate Revisions Block (10%)
def compute_revisions_block(data: Dict[str, Any]) -> FactorBlockResult:
    rev_delta = data.get("target_revision_30d")
    analyst_count = data.get("analyst_count") or 0

    if rev_delta is not None and not np.isnan(rev_delta):
        # Upward revision is positive, downward is negative
        s = 50.0 + (rev_delta * 250.0)
        rel = min(1.0, 0.4 + (analyst_count * 0.05)) if analyst_count > 0 else 0.4
        return FactorBlockResult(score=round(_clip100(s), 2), reliability=round(rel, 3), components={"revision_30d": rev_delta})

    # Fallback to analyst consensus score with modest reliability
    an_z = data.get("analyst_z")
    if an_z is not None and not np.isnan(an_z):
        rel = min(0.70, 0.3 + (analyst_count * 0.04)) if analyst_count > 0 else 0.3
        return FactorBlockResult(score=round(_clip100(an_z), 2), reliability=round(rel, 3), components={"analyst_z": an_z})

    return FactorBlockResult(score=None, reliability=0.0)

# 6. Capital Allocation Block (5%)
def compute_capital_allocation_block(data: Dict[str, Any]) -> FactorBlockResult:
    div_y = data.get("dividend_yield")
    clean_accruals = data.get("mews_clean_accruals", True)

    scores = []
    weights = []

    if div_y is not None and not np.isnan(div_y):
        # Modest dividend 2-4% is positive, >8% or 0% is neutral
        s_div = 50.0 + min(30.0, div_y * 800.0) if div_y <= 0.06 else 55.0
        scores.append(_clip100(s_div))
        weights.append(0.50)

    s_acc = 75.0 if clean_accruals else 30.0
    scores.append(s_acc)
    weights.append(0.50)

    total_w = sum(weights)
    final_score = sum(s * w for s, w in zip(scores, weights)) / total_w
    return FactorBlockResult(
        score=round(final_score, 2),
        reliability=0.75,
        components={"dividend_yield": div_y, "clean_accruals": clean_accruals}
    )

# 7. Directional Catalysts Block (5%) - Post-event evidence only, no proximity boost
def compute_catalysts_block(data: Dict[str, Any]) -> FactorBlockResult:
    # Post-earnings surprise or guidance raise/cut
    surprise_pct = data.get("earnings_surprise_pct")
    if surprise_pct is not None and not np.isnan(surprise_pct):
        # +10% beat -> 75 score; -10% miss -> 25 score
        s = 50.0 + (surprise_pct * 250.0)
        return FactorBlockResult(
            score=round(_clip100(s), 2),
            reliability=0.85,
            components={"surprise_pct": surprise_pct}
        )
    return FactorBlockResult(score=None, reliability=0.0)
