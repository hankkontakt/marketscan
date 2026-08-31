"""
macro.py — Pure Python Makro- & Marknadsregim-beräkning.
Inga externa beroenden utöver standardbiblioteket och numpy.
"""
from __future__ import annotations
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

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


def classify_macro_regime(
    vix: Optional[float] = None,
    yield_spread_2y10y: Optional[float] = None,
    uptrend_breadth_pct: Optional[float] = None,
    inflation_rate_pct: Optional[float] = None,
) -> tuple[str, dict]:
    """Klassificerar makroregim deterministiskt baserat på tillgängliga indikatorer."""
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

    # 2. Räntekurva (2y-10y Yield Spread)
    if yield_spread_2y10y is not None:
        if yield_spread_2y10y < -0.20:
            scores["STAGFLATION_HIGH_RATE"] += 2.0
            scores["CONTRACTION_CRISIS"] += 1.5
        elif yield_spread_2y10y > 0.50:
            scores["EXPANSION_RISK_ON"] += 2.0
        else:
            scores["NEUTRAL"] += 1.0

    # 3. Marknadsbredd (% upptrend)
    if uptrend_breadth_pct is not None:
        if uptrend_breadth_pct >= 60.0:
            scores["EXPANSION_RISK_ON"] += 3.0
        elif uptrend_breadth_pct <= 30.0:
            scores["CONTRACTION_CRISIS"] += 2.5
        elif 30.0 < uptrend_breadth_pct < 45.0:
            scores["STAGFLATION_HIGH_RATE"] += 1.5
        else:
            scores["NEUTRAL"] += 1.0

    # 4. Inflation
    if inflation_rate_pct is not None:
        if inflation_rate_pct >= 4.0:
            scores["STAGFLATION_HIGH_RATE"] += 2.5
        elif inflation_rate_pct <= 2.5:
            scores["EXPANSION_RISK_ON"] += 1.5

    best_regime = max(scores, key=lambda k: scores[k])
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

    breadth_pct = (uptrends / total) * 100.0 if total > 0 else 50.0

    avg_change_abs = float(np.mean([abs(r.get("change_pct") or 0.0) for r in scan_rows]))
    synthetic_vix = 15.0 + avg_change_abs * 500.0

    return classify_macro_regime(
        vix=synthetic_vix,
        uptrend_breadth_pct=breadth_pct,
    )
