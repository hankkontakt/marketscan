"""
Wyckoff Sentiment & Ownership Divergence Radar (Smart Money vs Retail).

Compares:
  - Retail owner count trend (Avanza / Nordnet ownership change over 30d/90d)
  - Insider transaction trend (CEO, Chairman, Board net buying in MSEK)
  - Institutional volume accumulation (On-balance volume / Block trades)

Key Signals:
  1. STEALTH_ACCUMULATION: Retail owners capitulate (falling owner count) while
     Insiders/Institutions aggressively accumulate shares. (Classic Wyckoff Phase C Spring).
  2. RETAIL_EUPHORIA / DISTRIBUTION: Retail owners spike (+50% to +200%) on social media hype
     while insiders sell into the exit liquidity.
  3. COMPRESSION_READY: Volume dry-up with tight volatility contraction.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_wyckoff_divergence(
    retail_owners_curr: Optional[int],
    retail_owners_30d_ago: Optional[int],
    insider_net_buy_msek_90d: Optional[float],
    price_change_30d_pct: Optional[float] = None,
    volatility_compression: Optional[bool] = None
) -> dict:
    """
    Evaluates whether retail sentiment is diverging from smart money behavior.
    """
    if retail_owners_curr is None or retail_owners_30d_ago is None or retail_owners_30d_ago <= 0:
        return {
            "wyckoff_signal": "NEUTRAL",
            "divergence_score": 50.0,
            "badge": None,
            "reason": "Otillräcklig ägarhistorik"
        }
        
    owner_delta_pct = ((retail_owners_curr - retail_owners_30d_ago) / retail_owners_30d_ago) * 100.0
    insider_buy = insider_net_buy_msek_90d if insider_net_buy_msek_90d is not None else 0.0
    
    # 1. STEALTH ACCUMULATION: Retail leaving (-2% to -20%) while insiders buy (> 0.5 MSEK)
    if owner_delta_pct <= 0.0 and insider_buy >= 0.5:
        score = 88.0 + min(insider_buy * 2.0, 10.0)
        return {
            "wyckoff_signal": "STEALTH_ACCUMULATION",
            "divergence_score": round(score, 1),
            "badge": "💎 STEALTH-ACKUMULATION (Wyckoff Spring)",
            "reason": f"Småsparare lämnar ({owner_delta_pct:+.1f}%) medan insynspersoner köper för {insider_buy:.1f} MSEK"
        }
        
    # 2. RETAIL EUPHORIA: Retail surging (>+35%) while insiders sell or stay away
    if owner_delta_pct >= 35.0 and insider_buy <= 0.0:
        score = 25.0
        return {
            "wyckoff_signal": "RETAIL_EUPHORIA",
            "divergence_score": 25.0,
            "badge": "⚠️ SMÅSPARAR-ÖVERHETTNING",
            "reason": f"Avanza-ägare rusar ({owner_delta_pct:+.1f}%) utan stöd från insynsköp (distributionsrisk)"
        }
        
    # 3. QUIET ACCUMULATION: Tight base, slight insider buying
    if abs(owner_delta_pct) < 5.0 and insider_buy > 0.2:
        return {
            "wyckoff_signal": "QUIET_ACCUMULATION",
            "divergence_score": 72.0,
            "badge": "🤫 TYST ACKUMULATION",
            "reason": f"Stabil ägarbas och insynsköp ({insider_buy:.1f} MSEK)"
        }
        
    return {
        "wyckoff_signal": "NEUTRAL",
        "divergence_score": 50.0,
        "badge": None,
        "reason": f"Normal ägartrend ({owner_delta_pct:+.1f}%)"
    }
