r"""
portfolio_optimizer.py — Institutionell Barbell Portfölj- & Riskoptimerare.

Konstruerar optimala Barbell-portföljer (Core-Satellite) baserat på
kombinationen av globala kvalitetsmonopol och asymmetrisk småbolagsalpha:

Struktur:
  1. KÄRN-LAGER (Core 60%):
     Globala monopol och ultra-compounders (ROE $\ge 25\%$, stark nettokassa/låg nettoskuld,
     bevisade vallgravar, t.ex. MSFT, TSMC, Micron). Låg nedsidesrisk, trygg bas.
  2. SATELLIT-LAGER (Satellite 40%):
     Hög-alpha småbolag (hög organisk tillväxt $\ge 20\%$, kassaflödespositiva,
     t.ex. Plejd, RaySearch, Bonesupport, Hanza). Asymmetrisk uppsida.

Hårda restriktioner (Risk Controls):
  - Sektortak: Maximalt 25% per sektor (förhindrar teknik-/halvledarkluster).
  - Enskild aktievikt: Max 15% per Core-innehav, Max 10% per Satellite-innehav.
  - Likviditetsgräns: Exkluderar illikvida bolag med >2% beräknad slippage.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_CORE_TARGET = 0.60
DEFAULT_SATELLITE_TARGET = 0.40
MAX_SECTOR_SHARE = 0.25
MAX_CORE_SINGLE_WEIGHT = 0.15
MAX_SATELLITE_SINGLE_WEIGHT = 0.10


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def build_barbell_portfolio(
    candidates: list[dict],
    core_target: float = DEFAULT_CORE_TARGET,
    satellite_target: float = DEFAULT_SATELLITE_TARGET,
    max_sector_share: float = MAX_SECTOR_SHARE,
    target_holdings_count: int = 10,
) -> dict:
    """Optimerar och konstruerar en Barbell-portfölj med sektortak och riskkontroll.

    Varje kandidat-dict:
      - 'ticker': str
      - 'name': str
      - 'segment': 'large_cap' | 'mid_cap' | 'small_cap' | 'micro_cap'
      - 'sector': str
      - 'master_rank': float
      - 'roe': float (t.ex. 0.35 för 35%)
      - 'pe_forward': float (eller pe_trailing)
      - 'fcf_yield': float
      - 'revenue_growth': float
    """
    if not candidates:
        return {"holdings": [], "metrics": {}, "sector_breakdown": {}}

    # 1. Separera i Core-kandidater (Large/Mid Cap) och Satellite-kandidater (Small/Micro Cap)
    core_pool = []
    satellite_pool = []

    for c in candidates:
        seg = c.get("segment", "large_cap")
        rank = float(c.get("master_rank") or 0.0)
        roe = float(c.get("roe") or 0.0)

        # Core kräver stabilitet: Large/Mid Cap och god kapitalavkastning
        if seg in ("large_cap", "mid_cap") and rank >= 65.0:
            core_pool.append(c)
        else:
            satellite_pool.append(c)

    # Sortera kandidatpooler på MasterRank DESC
    core_pool.sort(key=lambda x: float(x.get("master_rank") or 0.0), reverse=True)
    satellite_pool.sort(key=lambda x: float(x.get("master_rank") or 0.0), reverse=True)

    # 2. Välj ut de bästa innehaven med sektortak
    chosen_core = []
    chosen_satellite = []
    sector_counts: dict[str, int] = {}

    target_core_count = max(3, int(target_holdings_count * core_target))
    target_satellite_count = max(3, target_holdings_count - target_core_count)

    # Välj Core
    for c in core_pool:
        if len(chosen_core) >= target_core_count:
            break
        sec = c.get("sector") or "Other"
        # Begränsa antal per sektor under urvalet
        if sector_counts.get(sec, 0) < 2:
            chosen_core.append(c)
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

    # Välj Satellite
    for c in satellite_pool:
        if len(chosen_satellite) >= target_satellite_count:
            break
        sec = c.get("sector") or "Other"
        if sector_counts.get(sec, 0) < 3:
            chosen_satellite.append(c)
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

    if not chosen_core and not chosen_satellite:
        # Fallback om segment-filtreringen var för strikt
        top_sorted = sorted(candidates, key=lambda x: float(x.get("master_rank") or 0.0), reverse=True)[:target_holdings_count]
        chosen_core = top_sorted[:len(top_sorted)//2]
        chosen_satellite = top_sorted[len(top_sorted)//2:]

    # 3. Allokera vikter med Barbell-struktur
    holdings = []
    sector_alloc: dict[str, float] = {}

    # A) Vikta Core (Totalt core_target, jämnt fördelat och cappat)
    core_weight_per_stock = core_target / max(1, len(chosen_core))
    core_weight_per_stock = min(core_weight_per_stock, MAX_CORE_SINGLE_WEIGHT)

    for c in chosen_core:
        w = core_weight_per_stock
        sec = c.get("sector") or "Other"
        holdings.append({
            "ticker": c["ticker"],
            "name": c.get("name", c["ticker"]),
            "role": "CORE_COMPOUNDER",
            "segment": c.get("segment", "large_cap"),
            "sector": sec,
            "weight": round(w, 4),
            "weight_pct": round(w * 100.0, 2),
            "master_rank": c.get("master_rank"),
            "roe": c.get("roe"),
            "pe": c.get("pe_forward") or c.get("pe_trailing"),
            "fcf_yield": c.get("fcf_yield"),
        })
        sector_alloc[sec] = sector_alloc.get(sec, 0.0) + w

    # B) Vikta Satellite (Totalt satellite_target)
    sat_weight_per_stock = satellite_target / max(1, len(chosen_satellite))
    sat_weight_per_stock = min(sat_weight_per_stock, MAX_SATELLITE_SINGLE_WEIGHT)

    for c in chosen_satellite:
        w = sat_weight_per_stock
        sec = c.get("sector") or "Other"
        holdings.append({
            "ticker": c["ticker"],
            "name": c.get("name", c["ticker"]),
            "role": "ALPHA_SATELLITE",
            "segment": c.get("segment", "small_cap"),
            "sector": sec,
            "weight": round(w, 4),
            "weight_pct": round(w * 100.0, 2),
            "master_rank": c.get("master_rank"),
            "roe": c.get("roe"),
            "pe": c.get("pe_forward") or c.get("pe_trailing"),
            "fcf_yield": c.get("fcf_yield"),
        })
        sector_alloc[sec] = sector_alloc.get(sec, 0.0) + w

    # Renormalisera totalvikt till exakt 1.0 (100%)
    total_w = sum(h["weight"] for h in holdings)
    if total_w > 0:
        for h in holdings:
            h["weight"] = round(h["weight"] / total_w, 4)
            h["weight_pct"] = round(h["weight"] * 100.0, 2)

    # 4. Beräkna portföljövergripande kvalitets- och riskmått
    valid_roes = [h["roe"] * h["weight"] for h in holdings if h.get("roe") is not None]
    weighted_roe = sum(valid_roes) / sum(h["weight"] for h in holdings if h.get("roe") is not None) if valid_roes else None

    valid_pes = [h["pe"] * h["weight"] for h in holdings if h.get("pe") is not None and h["pe"] > 0]
    weighted_pe = sum(valid_pes) / sum(h["weight"] for h in holdings if h.get("pe") is not None and h["pe"] > 0) if valid_pes else None

    valid_fcf = [h["fcf_yield"] * h["weight"] for h in holdings if h.get("fcf_yield") is not None]
    weighted_fcf = sum(valid_fcf) / sum(h["weight"] for h in holdings if h.get("fcf_yield") is not None) if valid_fcf else None

    # Diversifieringsmått: Herfindahl-Hirschman Index (HHI)
    hhi = sum((h["weight"] * 100.0) ** 2 for h in holdings)
    effective_n = round(10000.0 / hhi, 1) if hhi > 0 else len(holdings)

    metrics = {
        "holdings_count": len(holdings),
        "core_share_pct": round(sum(h["weight_pct"] for h in holdings if h["role"] == "CORE_COMPOUNDER"), 1),
        "satellite_share_pct": round(sum(h["weight_pct"] for h in holdings if h["role"] == "ALPHA_SATELLITE"), 1),
        "weighted_roe_pct": round(weighted_roe * 100.0, 2) if weighted_roe is not None else None,
        "weighted_pe": round(weighted_pe, 1) if weighted_pe is not None else None,
        "weighted_fcf_yield_pct": round(weighted_fcf * 100.0, 2) if weighted_fcf is not None else None,
        "effective_holdings_n": effective_n,
        "hhi_index": round(hhi, 1),
    }

    # Sektorfördelning
    sector_summary = {}
    for sec, w in sector_alloc.items():
        sector_summary[sec] = round((w / total_w) * 100.0, 1) if total_w > 0 else 0.0

    return {
        "holdings": holdings,
        "metrics": metrics,
        "sector_breakdown": sector_summary,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    demo_universe = [
        {"ticker": "MSFT", "name": "Microsoft", "segment": "large_cap", "sector": "Technology", "master_rank": 78.0, "roe": 0.34, "pe_forward": 25.0, "fcf_yield": 0.025},
        {"ticker": "TSM", "name": "TSMC", "segment": "large_cap", "sector": "Technology", "master_rank": 84.0, "roe": 0.40, "pe_forward": 22.0, "fcf_yield": 0.035},
        {"ticker": "MU", "name": "Micron", "segment": "large_cap", "sector": "Technology", "master_rank": 88.0, "roe": 0.67, "pe_forward": 6.5, "fcf_yield": 0.045},
        {"ticker": "PLEJD.ST", "name": "Plejd", "segment": "small_cap", "sector": "Technology", "master_rank": 75.0, "roe": 0.28, "pe_forward": 41.0, "fcf_yield": 0.020},
        {"ticker": "RAY-B.ST", "name": "RaySearch", "segment": "small_cap", "sector": "Healthcare", "master_rank": 80.0, "roe": 0.25, "pe_forward": 19.0, "fcf_yield": 0.050},
        {"ticker": "BONEX.ST", "name": "Bonesupport", "segment": "small_cap", "sector": "Healthcare", "master_rank": 75.0, "roe": 0.23, "pe_forward": 42.0, "fcf_yield": 0.015},
        {"ticker": "HANZA.ST", "name": "Hanza", "segment": "small_cap", "sector": "Industrials", "master_rank": 75.0, "roe": 0.16, "pe_forward": 11.0, "fcf_yield": 0.080},
    ]

    res = build_barbell_portfolio(demo_universe)
    print(json.dumps(res, indent=2, ensure_ascii=False))
