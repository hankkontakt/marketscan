"""
macro_regime.py — Dynamisk Makro- & Faktorregimmotor.

Institutionell marknadsklassificering som analyserar makroindikatorer:
  1. Volatilitet / VIX (Risk-On vs Risk-Off)
  2. Räntekurva (2y-10y Yield Spread: Normal / Flack / Inverterad)
  3. Marknadsbredd (% av aktier i upptrend och med positivt momentum)
  4. Inflations- & Råvarutrend

Regimer:
  - EXPANSION_RISK_ON: Låg VIX, normal räntekurva, hög marknadsbredd.
    Tilt: Momentum (22%), Tillväxt (18%), Kvalitet (20%), Värde (10%).
  - STAGFLATION_HIGH_RATE: Höga räntor/inverterad kurva, stark inflation.
    Tilt: Värde (25%), Utdelning/Payout (15%), FCF-Kvalitet (25%), Tillväxt (5%).
  - CONTRACTION_CRISIS: Hög VIX (>25), negativ marknadsbredd, fallande tillväxt.
    Tilt: Kvalitet/Balansräkning (35%), Net Cash (20%), Låg Beta/Värde (20%), Momentum (5%).
  - NEUTRAL: Balanserad regim (standardvikter).

Innehåller fullständiga felsäkringar och fallbacks vid saknad realtidsdata.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import date
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Standard-grundvikter (MasterRank baseline)
BASE_WEIGHTS = {
    "quality": 0.25,
    "value": 0.15,
    "momentum": 0.15,
    "analyst": 0.15,
    "insider": 0.10,
    "catalyst": 0.10,
    "payout": 0.05,
    "growth": 0.05,
}

REGIME_WEIGHT_TILTS = {
    "EXPANSION_RISK_ON": {
        "quality": 0.20,
        "value": 0.10,
        "momentum": 0.20,
        "analyst": 0.18,
        "insider": 0.07,
        "catalyst": 0.10,
        "payout": 0.03,
        "growth": 0.12,
    },
    "STAGFLATION_HIGH_RATE": {
        "quality": 0.25,
        "value": 0.22,
        "momentum": 0.08,
        "analyst": 0.12,
        "insider": 0.10,
        "catalyst": 0.08,
        "payout": 0.10,
        "growth": 0.05,
    },
    "CONTRACTION_CRISIS": {
        "quality": 0.35,
        "value": 0.20,
        "momentum": 0.05,
        "analyst": 0.10,
        "insider": 0.10,
        "catalyst": 0.05,
        "payout": 0.10,
        "growth": 0.05,
    },
    "NEUTRAL": dict(BASE_WEIGHTS),
}

REGIME_DESCRIPTIONS = {
    "EXPANSION_RISK_ON": {
        "label": "Expansion & Risk-On",
        "description": "Gynnsamt makroklimat med låg volatilitet och stark marknadsbredd. Tillväxt, momentum och framåtblickande analytikerestimat premieras.",
        "color": "emerald",
    },
    "STAGFLATION_HIGH_RATE": {
        "label": "Stagflation & Högräntemiljö",
        "description": "Stigande räntor och ihållande inflation. Kassaflöden i dag, prissättningskraft, låg skuldsättning och värde premieras framför avlägsen tillväxt.",
        "color": "amber",
    },
    "CONTRACTION_CRISIS": {
        "label": "Kontraktion & Krisläge",
        "description": "Hög marknadsvolatilitet, fallande bredd och ökad riskpremie. Urstarka balansräkningar, nettokassa och defensiv kvalitet skyddar kapitalet.",
        "color": "rose",
    },
    "NEUTRAL": {
        "label": "Neutral / Balanserad",
        "description": "Balanserad marknadsregim utan extrema makroavvikelser. Balanserade standardvikter tillämpas.",
        "color": "slate",
    },
}


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def classify_macro_regime(
    vix: Optional[float] = None,
    yield_spread_2y10y: Optional[float] = None,
    uptrend_breadth_pct: Optional[float] = None,
    inflation_rate_pct: Optional[float] = None,
) -> tuple[str, dict]:
    """Klassificerar makroregim deterministiskt baserat på tillgängliga indikatorer.

    Felsäker: Om alla indikatorer är None faller motorn tillbaka på 'NEUTRAL'.
    """
    scores = {
        "EXPANSION_RISK_ON": 0.0,
        "STAGFLATION_HIGH_RATE": 0.0,
        "CONTRACTION_CRISIS": 0.0,
        "NEUTRAL": 1.0,
    }

    # 1. Volatilitetsanalys (VIX)
    if vix is not None:
        if vix >= 28.0:
            scores["CONTRACTION_CRISIS"] += 3.5
        elif vix >= 22.0:
            scores["CONTRACTION_CRISIS"] += 1.5
            scores["STAGFLATION_HIGH_RATE"] += 1.0
        elif vix <= 16.0:
            scores["EXPANSION_RISK_ON"] += 2.5
        else:
            scores["NEUTRAL"] += 1.0

    # 2. Räntekurva (2y-10y Yield Spread i procentenheter)
    if yield_spread_2y10y is not None:
        if yield_spread_2y10y < -0.20:
            # Tydligt inverterad kurva -> recessions-/stagflationsrisk
            scores["STAGFLATION_HIGH_RATE"] += 2.0
            scores["CONTRACTION_CRISIS"] += 1.5
        elif yield_spread_2y10y > 0.50:
            # Brant normal kurva -> expansion
            scores["EXPANSION_RISK_ON"] += 2.0
        else:
            scores["NEUTRAL"] += 1.0

    # 3. Marknadsbredd (% aktier i upptrend på 3–6 mån)
    if uptrend_breadth_pct is not None:
        if uptrend_breadth_pct >= 60.0:
            scores["EXPANSION_RISK_ON"] += 3.0
        elif uptrend_breadth_pct <= 30.0:
            scores["CONTRACTION_CRISIS"] += 2.5
        elif 30.0 < uptrend_breadth_pct < 45.0:
            scores["STAGFLATION_HIGH_RATE"] += 1.5
        else:
            scores["NEUTRAL"] += 1.0

    # 4. Inflation / Räntenivå
    if inflation_rate_pct is not None:
        if inflation_rate_pct >= 4.0:
            scores["STAGFLATION_HIGH_RATE"] += 2.5
        elif inflation_rate_pct <= 2.5:
            scores["EXPANSION_RISK_ON"] += 1.5

    # Välj regim med högst poäng
    best_regime = max(scores, key=lambda k: scores[k])
    
    # Om ingen tydlig dominans (skillnad < 1.0 mot neutral) -> NEUTRAL
    if best_regime != "NEUTRAL" and scores[best_regime] < 2.0:
        best_regime = "NEUTRAL"

    info = REGIME_DESCRIPTIONS.get(best_regime, REGIME_DESCRIPTIONS["NEUTRAL"])
    weights = REGIME_WEIGHT_TILTS.get(best_regime, BASE_WEIGHTS)

    result = {
        "regime": best_regime,
        "label": info["label"],
        "description": info["description"],
        "color": info["color"],
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "weights": weights,
        "inputs": {
            "vix": vix,
            "yield_spread_2y10y": yield_spread_2y10y,
            "uptrend_breadth_pct": uptrend_breadth_pct,
            "inflation_rate_pct": inflation_rate_pct,
        },
    }
    return best_regime, result


def derive_regime_from_scan(scan_rows: list[dict]) -> tuple[str, dict]:
    """Härleder marknadsregim direkt ur den interna scan-databasen (aggregat)."""
    if not scan_rows:
        return classify_macro_regime()

    total = len(scan_rows)
    uptrends = sum(1 for r in scan_rows if r.get("trend_signal") == "Upptrend" or r.get("trend_tech") == "Upptrend")
    downtrends = sum(1 for r in scan_rows if r.get("trend_signal") == "Nedtrend" or r.get("trend_tech") == "Nedtrend")
    stark_count = sum(1 for r in scan_rows if r.get("entry_signal") == "STARK")

    breadth_pct = (uptrends / total) * 100.0 if total > 0 else 50.0

    # Approximerad volatilitetsindikator från beta/change
    avg_change_abs = float(np.mean([abs(r.get("change_pct") or 0.0) for r in scan_rows]))
    synthetic_vix = 15.0 + avg_change_abs * 500.0  # 1% rörelse -> ~20 VIX

    return classify_macro_regime(
        vix=synthetic_vix,
        uptrend_breadth_pct=breadth_pct,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vix", type=float, default=14.5)
    parser.add_argument("--spread", type=float, default=0.6)
    parser.add_argument("--breadth", type=float, default=65.0)
    args = parser.parse_args()

    regime, res = classify_macro_regime(
        vix=args.vix,
        yield_spread_2y10y=args.spread,
        uptrend_breadth_pct=args.breadth,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
