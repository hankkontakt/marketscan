"""
earnings_revision.py — Earnings Revision Velocity & Smart Consensus Engine.

Kvantitativ modell för att mäta hastigheten och riktningen på analytikernas
vinst- och omsättningsestimat (Earnings Revision Momentum / Velocity).

Forskning (AQR, MSCI, Fama-French):
  Riktningen och accelerationen på analytikers revideringar de senaste 30–90 dagarna
  är en av marknadens mest persistenta alpha-faktorer. Bolag där analytiker tvingas
  skruva upp prognoserna tenderar att överprestera kraftigt (SUE-effekten).

Mått:
  1. eps_trend_30d_pct: % förändring i konsensus-EPS senaste 30 dagarna
  2. eps_trend_7d_pct: % förändring i konsensus-EPS senaste 7 dagarna (omedelbar fart)
  3. revision_breadth: andel analytiker som höjer vs sänker (Up / (Up + Down))
  4. revision_velocity_z: sammansatt z-score (0–100)
"""
from __future__ import annotations

import argparse
import json
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def compute_revision_metrics(
    eps_current: Optional[float],
    eps_30d_ago: Optional[float],
    eps_7d_ago: Optional[float],
    eps_90d_ago: Optional[float] = None,
    up_revisions_30d: int = 0,
    down_revisions_30d: int = 0,
    revenue_current: Optional[float] = None,
    revenue_30d_ago: Optional[float] = None,
) -> dict:
    """Beräknar vinstrevideringsmått deterministiskt ur historiska konsensuspunkter."""
    res = {
        "eps_trend_7d_pct": None,
        "eps_trend_30d_pct": None,
        "eps_trend_90d_pct": None,
        "revenue_trend_30d_pct": None,
        "revision_breadth": None,
        "revision_velocity_z": None,
        "revision_flags": [],
    }

    # 1. EPS Trend 7d
    if eps_current is not None and eps_7d_ago is not None and abs(eps_7d_ago) > 0.001:
        res["eps_trend_7d_pct"] = round(((eps_current - eps_7d_ago) / abs(eps_7d_ago)) * 100.0, 2)

    # 2. EPS Trend 30d
    if eps_current is not None and eps_30d_ago is not None and abs(eps_30d_ago) > 0.001:
        res["eps_trend_30d_pct"] = round(((eps_current - eps_30d_ago) / abs(eps_30d_ago)) * 100.0, 2)

    # 3. EPS Trend 90d
    if eps_current is not None and eps_90d_ago is not None and abs(eps_90d_ago) > 0.001:
        res["eps_trend_90d_pct"] = round(((eps_current - eps_90d_ago) / abs(eps_90d_ago)) * 100.0, 2)

    # 4. Revenue Trend 30d
    if revenue_current is not None and revenue_30d_ago is not None and revenue_30d_ago > 0:
        res["revenue_trend_30d_pct"] = round(((revenue_current - revenue_30d_ago) / revenue_30d_ago) * 100.0, 2)

    # 5. Revideringsbredd (Upward / Total)
    tot_rev = up_revisions_30d + down_revisions_30d
    if tot_rev > 0:
        res["revision_breadth"] = round(up_revisions_30d / tot_rev, 3)

    # 6. Sammansatt Revision Velocity Z (0–100)
    comps: list[float] = []
    weights: list[float] = []

    # A) 30d EPS Trend (tanh-skalad: +15% -> ~0.76)
    if res["eps_trend_30d_pct"] is not None:
        t = float(np.tanh(res["eps_trend_30d_pct"] / 15.0))
        comps.append(np.sign(t) * (abs(t) ** 1.1))
        weights.append(0.50)

    # B) 7d EPS Trend (kortsiktig fart: +5% -> ~0.76)
    if res["eps_trend_7d_pct"] is not None:
        t7 = float(np.tanh(res["eps_trend_7d_pct"] / 5.0))
        comps.append(t7)
        weights.append(0.20)

    # C) Revision Breadth (0.0 -> -1.0, 0.5 -> 0.0, 1.0 -> +1.0)
    if res["revision_breadth"] is not None:
        breadth_comp = (res["revision_breadth"] - 0.5) * 2.0
        comps.append(breadth_comp)
        weights.append(0.30)

    if weights and sum(weights) > 0:
        norm_score = sum(c * w for c, w in zip(comps, weights)) / sum(weights)
        res["revision_velocity_z"] = float(np.clip(50.0 + norm_score * 50.0, 0.0, 100.0))
    else:
        res["revision_velocity_z"] = 50.0  # Neutral fallback

    # 7. Varningsflaggor & Signaler
    flags = []
    if res["eps_trend_30d_pct"] is not None and res["eps_trend_30d_pct"] >= 10.0:
        flags.append("STRONG_UPWARD_REVISION")
    elif res["eps_trend_30d_pct"] is not None and res["eps_trend_30d_pct"] <= -10.0:
        flags.append("ESTIMATE_DOWNGRADE_WARNING")

    if res["revision_breadth"] is not None and res["revision_breadth"] >= 0.80 and tot_rev >= 4:
        flags.append("UNANIMOUS_ESTIMATE_UPGRADE")
    elif res["revision_breadth"] is not None and res["revision_breadth"] <= 0.20 and tot_rev >= 4:
        flags.append("UNANIMOUS_ESTIMATE_DOWNGRADE")

    res["revision_flags"] = flags
    return res


# ═════════════════════════ HÄMTNING UR YFINANCE / CACHE ════════════════════════

def extract_yfinance_revisions(info: dict) -> dict:
    """Extraherar revisionsdata från yfinance eps_trend/earnings_estimate dict."""
    # yfinance epsTrend dict struktur: {'current': ..., '7daysAgo': ..., '30daysAgo': ..., '90daysAgo': ...}
    eps_trend = info.get("epsTrend", {})
    curr_q = eps_trend.get("0q", {}) if isinstance(eps_trend, dict) else {}
    
    eps_curr = curr_q.get("current")
    eps_7d = curr_q.get("7daysAgo")
    eps_30d = curr_q.get("30daysAgo")
    eps_90d = curr_q.get("90daysAgo")

    # Revisionsantal
    eps_rev = info.get("epsRevisions", {})
    curr_rev = eps_rev.get("0q", {}) if isinstance(eps_rev, dict) else {}
    up_30d = int(curr_rev.get("upLast30days", 0) or 0)
    down_30d = int(curr_rev.get("downLast30days", 0) or 0)

    return compute_revision_metrics(
        eps_current=float(eps_curr) if eps_curr is not None else None,
        eps_30d_ago=float(eps_30d) if eps_30d is not None else None,
        eps_7d_ago=float(eps_7d) if eps_7d is not None else None,
        eps_90d_ago=float(eps_90d) if eps_90d is not None else None,
        up_revisions_30d=up_30d,
        down_revisions_30d=down_30d,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--curr", type=float, default=2.50)
    parser.add_argument("--prev30", type=float, default=2.10)
    parser.add_argument("--prev7", type=float, default=2.40)
    parser.add_argument("--up", type=int, default=8)
    parser.add_argument("--down", type=int, default=1)
    args = parser.parse_args()

    res = compute_revision_metrics(
        eps_current=args.curr,
        eps_30d_ago=args.prev30,
        eps_7d_ago=args.prev7,
        up_revisions_30d=args.up,
        down_revisions_30d=args.down,
    )
    print(json.dumps(res, indent=2))
