"""
Smart Money & Super-Investor Fund Tracker (Fund Shadowing).

Monitors top Nordic small/mid-cap institutional investors and funds:
  - TIN Fonder (Ny Teknik, Småbolag)
  - Svolder AB
  - Cliens Småbolag
  - Lannebo Småbolag
  - Spiltan Småbolag / Småbolagsfond
  - Handelsbanken Småbolag
  - Didner & Gerge Småbolag
  - ODIN Småbedrifter

Tracks:
  - FI Flaggningsmeddelanden (Major shareholding threshold crossings: >5%, >10%)
  - Multi-fund accumulation clusters
  - Initiations vs Disposals

Outputs:
  - smart_money_score (0 - 100)
  - smart_money_flag (bool)
  - cluster_institutions (list of funds)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# Institutional small-cap funds with verified high historical alpha in the Nordics
FLAGSHIP_FUNDS = {
    "TIN Fonder": {"alpha_weight": 1.2, "focus": "Tech & Life Science"},
    "Svolder": {"alpha_weight": 1.3, "focus": "Nordic Quality Small Caps"},
    "Cliens Småbolag": {"alpha_weight": 1.25, "focus": "Nordic Compounders"},
    "Lannebo Småbolag": {"alpha_weight": 1.15, "focus": "Small & Micro Caps"},
    "Spiltan Fonder": {"alpha_weight": 1.2, "focus": "Long-term Value/Growth"},
    "Didner & Gerge Småbolag": {"alpha_weight": 1.1, "focus": "Nordic Small Caps"},
    "Handelsbanken Småbolag": {"alpha_weight": 1.05, "focus": "Broad Nordic Small Cap"},
    "ODIN Småbedrifter": {"alpha_weight": 1.2, "focus": "Nordic Micro & Small Caps"},
}


@dataclass
class HoldingChange:
    institution_name: str
    ticker: str
    change_type: str        # 'NEW_POSITION', 'INCREASE', 'DECREASE', 'EXIT', 'FLAGGING_5PCT', 'FLAGGING_10PCT'
    shares_change: Optional[int]
    total_percent: Optional[float]
    reported_date: date


def score_smart_money_cluster(
    changes: list[HoldingChange],
    market_cap_msek: Optional[float] = None
) -> dict:
    """
    Computes a smart money score based on recent institutional moves.
    
    If 2 or more distinct Tier-1 funds initiate new positions or flag >5%,
    this represents a powerful cluster signal.
    """
    if not changes:
        return {
            "smart_money_score": 50.0,
            "smart_money_cluster": False,
            "cluster_funds": [],
            "badge": None,
            "reason": "Ingen känd institutionsförändring senaste perioden"
        }
        
    buyers = []
    sellers = []
    total_buyer_weight = 0.0
    has_flagging = False
    
    for c in changes:
        fund_meta = FLAGSHIP_FUNDS.get(c.institution_name, {"alpha_weight": 1.0})
        w = fund_meta["alpha_weight"]
        
        if c.change_type in ["NEW_POSITION", "INCREASE", "FLAGGING_5PCT", "FLAGGING_10PCT"]:
            buyers.append(c.institution_name)
            total_buyer_weight += w
            if "FLAGGING" in c.change_type:
                has_flagging = True
                total_buyer_weight += 0.5
        elif c.change_type in ["DECREASE", "EXIT"]:
            sellers.append(c.institution_name)
            
    unique_buyers = list(set(buyers))
    unique_sellers = list(set(sellers))
    
    # Calculate score
    base_score = 50.0
    if unique_buyers:
        base_score += len(unique_buyers) * 15.0 * (total_buyer_weight / len(unique_buyers))
    if unique_sellers:
        base_score -= len(unique_sellers) * 12.0
        
    score = float(max(10.0, min(99.0, base_score)))
    
    is_cluster = len(unique_buyers) >= 2 or has_flagging
    
    badge = None
    if is_cluster and len(unique_buyers) >= 2:
        badge = f"💼 SMART MONEY KLUSTER: {', '.join(unique_buyers[:2])} Köper"
    elif has_flagging:
        badge = f"🚩 FLAGGNINSMEDDELANDE: {unique_buyers[0] if unique_buyers else 'Institution'} >5%"
    elif len(unique_buyers) == 1:
        badge = f"🏛️ INSTITUTIONELL KÖPARE: {unique_buyers[0]}"
        
    return {
        "smart_money_score": round(score, 1),
        "smart_money_cluster": is_cluster,
        "cluster_funds": unique_buyers,
        "badge": badge,
        "reason": f"{len(unique_buyers)} institutionella köpare, {len(unique_sellers)} säljare"
    }
