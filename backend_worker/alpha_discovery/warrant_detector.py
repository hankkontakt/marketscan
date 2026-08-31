"""
Warrant & Dilution Overhang Detector (TO-Radar).

Audits active Swedish/Nordic subscription warrants (Teckningsoptioner TO1-TO9).
Evaluates:
  - Active warrant series attached to the ticker/company
  - Strike price vs Current share price (Moneyness: (Price - Strike) / Strike)
  - Days to subscription window / expiration
  - Potential dilution percentage: (Warrants Count / Total Shares) * 100
  - Dilution Overhang Risk Rating: 'CRITICAL', 'HIGH', 'MODERATE', 'CLEAN'
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WarrantSeries:
    series_name: str         # e.g. "TO1", "TO2", "TO3"
    strike_price: float      # SEK per share
    subscription_start: Optional[date]
    subscription_end: Optional[date]
    warrants_outstanding: Optional[int]
    shares_per_warrant: float = 1.0


def extract_warrant_mentions_from_text(text: str) -> list[dict]:
    """
    Parses press releases or regulatory text for warrant (TO) issuance and strike details.
    
    Looks for patterns like:
      - 'teckningsoptioner av serie TO 2'
      - 'teckningskurs om 4,50 SEK'
      - 'teckningsperiod från och med 15 oktober till och med 29 oktober 2026'
    """
    if not text:
        return []
        
    results = []
    
    # Pattern for series name
    series_pattern = re.compile(r'\b(?:serie\s+)?(TO\s*\d+|TO\d+[A-Z]?)\b', re.IGNORECASE)
    series_matches = series_pattern.findall(text)
    
    # Pattern for strike price
    strike_pattern = re.compile(
        r'(?:teckningskurs|lösenpris|kurs(?:en)?)\s+(?:om|på|fastställd till)?\s*([0-9]+(?:[,.][0-9]+)?)\s*(?:kr|sek)',
        re.IGNORECASE
    )
    strike_match = strike_pattern.search(text)
    strike_val = None
    if strike_match:
        strike_val = float(strike_match.group(1).replace(",", "."))
        
    for s in set(series_matches):
        s_norm = s.upper().replace(" ", "")
        results.append({
            "series_name": s_norm,
            "strike_price": strike_val,
            "raw_text": text[:300]
        })
        
    return results


def audit_warrant_overhang(
    current_price: Optional[float],
    total_shares: Optional[int],
    warrants: list[WarrantSeries],
    as_of: Optional[date] = None
) -> dict:
    """
    Evaluates whether active warrants pose a near-term dilution risk or price ceiling.
    
    Logic:
      - If current_price > strike_price * 0.9 (in-the-money or near money)
      - And expiration is within 90 days:
        Arbitrageurs hedge/short the underlying stock, and exercising warrants will flood market.
    """
    if as_of is None:
        as_of = date.today()
        
    if not warrants or current_price is None or current_price <= 0:
        return {
            "warrant_risk": "CLEAN",
            "overhang_flag": False,
            "dilution_penalty": 0.0,
            "active_warrants": [],
            "reason": "Inga aktiva teckningsoptioner identifierade"
        }
        
    high_risk_series = []
    max_dilution_pct = 0.0
    total_penalty = 0.0
    
    for w in warrants:
        if w.strike_price <= 0:
            continue
            
        moneyness = (current_price - w.strike_price) / w.strike_price
        
        days_to_end = None
        if w.subscription_end:
            days_to_end = (w.subscription_end - as_of).days
            
        is_near_expiry = (days_to_end is not None and 0 <= days_to_end <= 90)
        is_in_the_money = moneyness >= -0.10  # inom 10% från lösen eller över
        
        dilution_pct = 0.0
        if w.warrants_outstanding and total_shares and total_shares > 0:
            dilution_pct = round((w.warrants_outstanding * w.shares_per_warrant / total_shares) * 100.0, 1)
            max_dilution_pct += dilution_pct
            
        if is_near_expiry and is_in_the_money:
            penalty = 15.0 if moneyness > 0.15 else 8.0
            total_penalty += penalty
            high_risk_series.append({
                "series": w.series_name,
                "strike_price": w.strike_price,
                "moneyness_pct": round(moneyness * 100.0, 1),
                "days_to_expiry": days_to_end,
                "potential_dilution_pct": dilution_pct,
                "risk_level": "CRITICAL" if moneyness > 0.20 else "HIGH"
            })
            
    if high_risk_series:
        return {
            "warrant_risk": "CRITICAL" if total_penalty >= 15.0 else "HIGH",
            "overhang_flag": True,
            "dilution_penalty": min(total_penalty, 25.0),
            "potential_total_dilution_pct": round(max_dilution_pct, 1),
            "active_warrants": high_risk_series,
            "reason": f"Aktiv teckningsoption ({high_risk_series[0]['series']}) in-the-money med lösen inom kort — kurspressrisk"
        }
        
    return {
        "warrant_risk": "CLEAN",
        "overhang_flag": False,
        "dilution_penalty": 0.0,
        "active_warrants": [],
        "reason": "Teckningsoptioner är ur pengarna (OTM) eller har lång löptid"
    }
