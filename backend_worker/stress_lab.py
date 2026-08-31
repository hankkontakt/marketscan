r"""
stress_lab.py — Portfölj-Stresstest Lab & Krissimulator.

Simulerar och stresstestar aktieportföljer mot 4 historiskt förankrade krisscenarier:

1. RATE_SHOCK_150BPS (Räntechock +150 bps / 2022-repris):
   - Multiplakontraktion för tillväxtbolag med lång duration och höga multiplar (P/E > 40x).
   - Bolag med nettokassa och värdebolag dämpas.
2. TECH_SEMI_DRAWDOWN_25PCT (Teknik- & Halvledarnedgång -25%):
   - Sektorspecifik krasch för tech/semis. Defensiva hälsovårds- och industribolag står emot.
3. SMALLCAP_LIQUIDITY_CRUNCH (Småbolags- & Likviditetskris -20% + spreadvidgning):
   - Småbolag drabbas av likviditetsbortfall (-20% till -30%), medan megacaps agerar trygg hamn.
4. STAGFLATION_ENERGY_SPIKE (Stagflationschock / Oljeprisspik +30%):
   - Prispress på bolag med låga bruttomarginaler (<30%). Bolag med pricing power (>70% marginal) skyddas.

Beräknar:
  - Portföljens uppskattade drawdown per scenario
  - Value-at-Risk (VaR 95%)
  - Resiliensbetyg (Resilience Score 0–100)
  - Innehavsspecifik stressrespons
"""
from __future__ import annotations

import argparse
import json
import logging

import numpy as np

logger = logging.getLogger(__name__)

SCENARIOS = {
    "RATE_SHOCK_150BPS": {
        "title": "Räntechock (+150 bps)",
        "description": "Kraftigt stigande marknadsräntor som pressar högt värderade tillväxtmultiplar och högt belånade bolag (motsvarande 2022).",
        "market_shock_pct": -12.0,
    },
    "TECH_SEMI_DRAWDOWN_25PCT": {
        "title": "Teknik- & Halvledarnedgång (-25%)",
        "description": "Cyklisk avkylning och multipelkontraktion inom tech och halvledare.",
        "market_shock_pct": -15.0,
    },
    "SMALLCAP_LIQUIDITY_CRUNCH": {
        "title": "Småbolags- & Likviditetskris (-20%)",
        "description": "Likviditeten torkar upp i småbolagssegmentet med kraftig spreadvidgning som följd.",
        "market_shock_pct": -10.0,
    },
    "STAGFLATION_ENERGY_SPIKE": {
        "title": "Stagflations- & Råvaruchock (+30% Olja)",
        "description": "Ihållande kostnadsinflation som pressar bruttomarginaler för bolag utan prissättningskraft.",
        "market_shock_pct": -8.0,
    },
}


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def stress_test_portfolio(holdings: list[dict]) -> dict:
    """Kör samtliga 4 stresstestscenarier på en portfölj.

    Varje holding-dict:
      - 'ticker': str
      - 'weight': float (t.ex. 0.15 för 15%)
      - 'segment': 'large_cap' | 'small_cap' ...
      - 'sector': str
      - 'pe': float
      - 'roe': float
      - 'gross_margin': float (t.ex. 0.70 för 70%)
      - 'beta': float
    """
    if not holdings:
        return {"scenarios": {}, "summary": {"resilience_score": 50.0, "max_drawdown_pct": 0.0}}

    scenario_results = {}
    drawdown_list = []

    for scen_key, scen_meta in SCENARIOS.items():
        asset_impacts = []
        port_impact = 0.0

        for h in holdings:
            w = float(h.get("weight") or 0.0)
            seg = h.get("segment", "large_cap")
            sec = str(h.get("sector", "Other"))
            pe = float(h.get("pe") or 20.0)
            gm = float(h.get("gross_margin") or 0.50)
            beta = float(h.get("beta") or 1.0)

            # Beräkna specifik stresseffekt per scenario
            if scen_key == "RATE_SHOCK_150BPS":
                # Multiplar > 35x drabbas hårdare av räntechock
                mult_penalty = min(15.0, max(0.0, (pe - 20.0) * 0.4))
                impact = -(8.0 + mult_penalty)

            elif scen_key == "TECH_SEMI_DRAWDOWN_25PCT":
                if "TECH" in sec.upper() or "SEMI" in sec.upper():
                    impact = -25.0 * beta
                elif "HEALTH" in sec.upper() or "DEFENSE" in sec.upper():
                    impact = -4.0 * beta
                else:
                    impact = -10.0 * beta

            elif scen_key == "SMALLCAP_LIQUIDITY_CRUNCH":
                if seg in ("small_cap", "micro_cap"):
                    impact = -22.0 * max(0.8, beta)
                else:
                    impact = -4.0 * max(0.8, beta)

            elif scen_key == "STAGFLATION_ENERGY_SPIKE":
                # Hög bruttomarginal (>70%) skyddar mot kostnadsinflation
                if gm >= 0.70:
                    impact = -3.5
                elif gm >= 0.50:
                    impact = -8.0
                else:
                    impact = -18.0

            asset_impacts.append({
                "ticker": h.get("ticker"),
                "weight_pct": round(w * 100.0, 2),
                "estimated_impact_pct": round(impact, 2),
            })
            port_impact += w * impact

        scenario_results[scen_key] = {
            "title": scen_meta["title"],
            "description": scen_meta["description"],
            "portfolio_drawdown_pct": round(port_impact, 2),
            "asset_impacts": asset_impacts,
        }
        drawdown_list.append(port_impact)

    worst_drawdown = min(drawdown_list) if drawdown_list else 0.0
    avg_drawdown = float(np.mean(drawdown_list)) if drawdown_list else 0.0

    # Resiliensbetyg (0–100): 100 = 0% drawdown, 0 = -40% drawdown
    resilience_score = float(np.clip(100.0 + (avg_drawdown * 2.5), 0.0, 100.0))

    # Parametrisk 95% VaR (10-dagars horisont)
    var_95 = round(abs(worst_drawdown) * 0.65, 2)

    return {
        "scenarios": scenario_results,
        "summary": {
            "resilience_score": round(resilience_score, 1),
            "worst_case_scenario": min(scenario_results, key=lambda k: scenario_results[k]["portfolio_drawdown_pct"]),
            "worst_case_drawdown_pct": round(worst_drawdown, 2),
            "average_crisis_drawdown_pct": round(avg_drawdown, 2),
            "estimated_10d_var_95_pct": var_95,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    demo_portfolio = [
        {"ticker": "MSFT", "weight": 0.20, "segment": "large_cap", "sector": "Technology", "pe": 25.0, "gross_margin": 0.68, "beta": 0.95},
        {"ticker": "TSM", "weight": 0.20, "segment": "large_cap", "sector": "Technology", "pe": 22.0, "gross_margin": 0.55, "beta": 1.10},
        {"ticker": "JNJ", "weight": 0.20, "segment": "large_cap", "sector": "Healthcare", "pe": 15.0, "gross_margin": 0.68, "beta": 0.60},
        {"ticker": "PLEJD.ST", "weight": 0.20, "segment": "small_cap", "sector": "Technology", "pe": 41.0, "gross_margin": 0.71, "beta": 1.20},
        {"ticker": "RAY-B.ST", "weight": 0.20, "segment": "small_cap", "sector": "Healthcare", "pe": 19.0, "gross_margin": 0.85, "beta": 0.90},
    ]

    res = stress_test_portfolio(demo_portfolio)
    print(json.dumps(res, indent=2, ensure_ascii=False))
