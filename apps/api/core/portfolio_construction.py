"""
portfolio_construction.py — Portföljkonstruktion (ERC + Black-Litterman).

Riskparitet (ERC): robust baslinje som bara kräver kovariansmatris.
Black-Litterman: kombinerar marknadsprior med AI-views för posterior-vikter.

All ren NumPy/SciPy — inga externa beroenden.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def equal_risk_contribution(cov: np.ndarray) -> np.ndarray:
    """Equal Risk Contribution (ERC / Risk Parity).

    Varje tillgång bidrar lika mycket till portföljrisken.
    Long-only, summa=1.

    Args:
        cov: Kovariansmatris (n_assets x n_assets).

    Returns:
        Vikt-array (n_assets,) som summerar till 1.
    """
    n = cov.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    def _risk_contribution(weights: np.ndarray) -> np.ndarray:
        """Beräkna marginal risk contribution per tillgång."""
        port_var = weights @ cov @ weights
        if port_var <= 0:
            return np.zeros(n)
        # Marginal risk = (cov @ weights) / sqrt(port_var)
        marginal = cov @ weights
        rc = weights * marginal / np.sqrt(port_var)
        return rc

    def _objective(weights: np.ndarray) -> float:
        rc = _risk_contribution(weights)
        target = rc.sum() / n
        return np.sum((rc - target) ** 2)

    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    result = minimize(
        _objective, x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if not result.success:
        logger.warning("ERC-optimering konvergerade inte: %s", result.message)
        # Fallback: equal weight
        return np.ones(n) / n

    # Normalisera
    w = result.x
    w = np.maximum(w, 0)
    w = w / w.sum()
    return w


def black_litterman(
    market_caps: np.ndarray,
    cov: np.ndarray,
    views: list[dict],
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    max_position_pct: float = 0.25,
    target_volatility: Optional[float] = None,
) -> np.ndarray:
    """Black-Litterman portföljkonstruktion med AI-views.

    Standard BL-matematik (Idzorek):
      1. Implied equilibrium returns Π = δ Σ w_mkt
      2. Kombinera med views (P, Q, Ω) → posterior E[R]
      3. Mean-variance optimization med constraints

    Args:
        market_caps: Marknadsvärden för equilibrium-vikter.
        cov: Kovariansmatris (n_assets x n_assets).
        views: Lista med dicts {ticker_idx, expected_excess_return, confidence}.
               ticker_idx = index i market_caps/cov.
               confidence = 0..1 (hur säker är view:n?).
        risk_aversion: Riskaversion (δ). Lägre = tryggare profil.
        tau: Skalning av prior-kovarians (standard 0.05).
        max_position_pct: Maximal vikt per position (0..1).
        target_volatility: Målvolatilitet (om satt, skala).

    Returns:
        Posterior-vikter (n_assets,) som summerar till 1.
    """
    n = len(market_caps)
    if n == 0:
        return np.array([])

    # 1. Market cap weights
    w_mkt = np.array(market_caps, dtype=float)
    w_mkt = np.maximum(w_mkt, 0)
    if w_mkt.sum() == 0:
        w_mkt = np.ones(n) / n
    else:
        w_mkt = w_mkt / w_mkt.sum()

    # 2. Implied equilibrium returns Π = δ Σ w_mkt
    pi = risk_aversion * cov @ w_mkt

    # 3. Bygg view-matriser
    if not views:
        # Inga views → returnera equilibrium-vikter
        return w_mkt

    k = len(views)
    P = np.zeros((k, n))
    Q = np.zeros(k)
    omega = np.zeros((k, k))

    for i, view in enumerate(views):
        idx = view.get("ticker_idx", i)
        if idx >= n:
            continue
        P[i, idx] = 1.0
        Q[i] = view.get("expected_excess_return", 0.0)
        confidence = max(min(view.get("confidence", 0.5), 1.0), 0.01)
        # Ω: uncertainty scaled by prior variance
        omega[i, i] = (1.0 / confidence - 1.0) * cov[idx, idx] * tau if cov[idx, idx] > 0 else 0.01

    # 4. Posterior expected returns (BL master formula)
    # E[R] = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ [(τΣ)⁻¹Π + PᵀΩ⁻¹Q]
    tau_cov = tau * cov

    try:
        inv_tau_cov = np.linalg.inv(tau_cov)
        inv_omega = np.linalg.inv(omega)

        # Posterior covariance
        M = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
        # Posterior mean
        mu_bl = M @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)
    except np.linalg.LinAlgError:
        logger.warning("BL matrix inversion failed — using equilibrium returns")
        mu_bl = pi

    # 5. Mean-variance optimization with constraints
    def _neg_utility(weights: np.ndarray) -> float:
        port_return = weights @ mu_bl
        port_risk = weights @ cov @ weights
        return -(port_return - 0.5 * risk_aversion * port_risk)

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
    ]
    bounds = [(0.0, max_position_pct)] * n
    x0 = w_mkt.copy()

    result = minimize(
        _neg_utility, x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    weights = result.x if result.success else w_mkt
    weights = np.maximum(weights, 0)
    weights = weights / weights.sum()

    # 6. Volatilitets-begränsning
    if target_volatility is not None:
        port_vol = np.sqrt(weights @ cov @ weights)
        if port_vol > target_volatility and port_vol > 0:
            # Skala ner risk
            scale = target_volatility / port_vol
            # Blanda med kontanter (risk-free)
            cash = 1.0 - scale
            weights = weights * scale
            weights = weights / weights.sum() * (1 - cash)
            logger.info("BL: vol constraint applied (%.1f%% → %.1f%%)", port_vol * 100, target_volatility * 100)

    return weights


def portfolio_stats(
    weights: np.ndarray,
    cov: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
) -> dict:
    """Beräkna portföljstatistik.

    Returns:
        Dict med expected_return, volatility, sharpe, var_95.
    """
    if len(weights) == 0:
        return {"expected_return": 0, "volatility": 0, "sharpe": 0, "var_95": 0}

    vol = float(np.sqrt(weights @ cov @ weights))
    ret = float(weights @ expected_returns) if expected_returns is not None else 0.0

    # VaR (95%, normal approximation)
    var_95 = float(-1.645 * vol)

    sharpe = ret / vol if vol > 0 else 0.0

    return {
        "expected_return": round(ret, 4),
        "volatility": round(vol, 4),
        "sharpe": round(sharpe, 4),
        "var_95": round(var_95, 4),
    }


# ─── Barbell Optimizer & Stress Simulator ────────────────────────────────────

DEFAULT_CORE_TARGET = 0.60
DEFAULT_SATELLITE_TARGET = 0.40
MAX_SECTOR_SHARE = 0.25
MAX_CORE_SINGLE_WEIGHT = 0.15
MAX_SATELLITE_SINGLE_WEIGHT = 0.10


def build_barbell_portfolio(
    candidates: list[dict],
    core_target: float = DEFAULT_CORE_TARGET,
    satellite_target: float = DEFAULT_SATELLITE_TARGET,
    max_sector_share: float = MAX_SECTOR_SHARE,
    target_holdings_count: int = 10,
) -> dict:
    """Optimerar och konstruerar en Barbell-portfölj med sektortak och riskkontroll."""
    if not candidates:
        return {"holdings": [], "metrics": {}, "sector_breakdown": {}}

    core_pool = []
    satellite_pool = []

    for c in candidates:
        seg = c.get("segment", "large_cap")
        rank = float(c.get("master_rank") or 0.0)
        if seg in ("large_cap", "mid_cap") and rank >= 65.0:
            core_pool.append(c)
        else:
            satellite_pool.append(c)

    core_pool.sort(key=lambda x: float(x.get("master_rank") or 0.0), reverse=True)
    satellite_pool.sort(key=lambda x: float(x.get("master_rank") or 0.0), reverse=True)

    chosen_core = []
    chosen_satellite = []
    sector_counts: dict[str, int] = {}

    target_core_count = max(3, int(target_holdings_count * core_target))
    target_satellite_count = max(3, target_holdings_count - target_core_count)

    for c in core_pool:
        if len(chosen_core) >= target_core_count:
            break
        sec = c.get("sector") or "Other"
        if sector_counts.get(sec, 0) < 2:
            chosen_core.append(c)
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

    for c in satellite_pool:
        if len(chosen_satellite) >= target_satellite_count:
            break
        sec = c.get("sector") or "Other"
        if sector_counts.get(sec, 0) < 3:
            chosen_satellite.append(c)
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

    holdings = []
    if chosen_core:
        core_w = core_target / len(chosen_core)
        for c in chosen_core:
            holdings.append({
                "ticker": c["ticker"],
                "company_name": c.get("company_name") or c.get("name") or c["ticker"],
                "segment_type": "CORE",
                "weight": round(min(core_w, MAX_CORE_SINGLE_WEIGHT), 4),
                "sector": c.get("sector") or "Other",
                "master_rank": c.get("master_rank"),
                "thesis": f"Core-kvalitet: ROE {round(float(c.get('roe') or 0.0)*100, 1)}%, P/E {c.get('pe_forward') or c.get('pe') or '-'}"
            })

    if chosen_satellite:
        sat_w = satellite_target / len(chosen_satellite)
        for c in chosen_satellite:
            holdings.append({
                "ticker": c["ticker"],
                "company_name": c.get("company_name") or c.get("name") or c["ticker"],
                "segment_type": "SATELLITE",
                "weight": round(min(sat_w, MAX_SATELLITE_SINGLE_WEIGHT), 4),
                "sector": c.get("sector") or "Other",
                "master_rank": c.get("master_rank"),
                "thesis": f"Satellit-alpha: Tillväxt {round(float(c.get('revenue_growth') or 0.0)*100, 1)}%, Rank {c.get('master_rank')}"
            })

    total_w = sum(h["weight"] for h in holdings)
    if total_w > 0:
        for h in holdings:
            h["weight"] = round(h["weight"] / total_w, 4)

    sector_breakdown: dict[str, float] = {}
    for h in holdings:
        sec = h["sector"]
        sector_breakdown[sec] = round(sector_breakdown.get(sec, 0.0) + h["weight"], 4)

    metrics = {
        "holdings_count": len(holdings),
        "core_weight": round(sum(h["weight"] for h in holdings if h["segment_type"] == "CORE"), 4),
        "satellite_weight": round(sum(h["weight"] for h in holdings if h["segment_type"] == "SATELLITE"), 4),
        "avg_master_rank": round(sum(float(h["master_rank"] or 0.0) for h in holdings) / len(holdings), 1) if holdings else 0.0,
        "max_sector_weight": max(sector_breakdown.values()) if sector_breakdown else 0.0,
    }

    return {
        "holdings": holdings,
        "metrics": metrics,
        "sector_breakdown": sector_breakdown,
    }


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


def stress_test_portfolio(holdings: list[dict]) -> dict:
    """Stresstestar en portfölj mot 4 standardiserade kris-scenarier."""
    if not holdings:
        return {"scenarios": {}, "resilience_score": 50.0, "worst_scenario": None}

    total_weight = sum(float(h.get("weight") or 0.0) for h in holdings)
    norm_holdings = []
    for h in holdings:
        w = float(h.get("weight") or 0.0)
        norm_w = w / total_weight if total_weight > 0 else 1.0 / len(holdings)
        norm_holdings.append({**h, "weight": norm_w})

    scenario_results = {}
    drawdowns = []

    for key, sc in SCENARIOS.items():
        base_shock = sc["market_shock_pct"]
        asset_impacts = []

        for h in norm_holdings:
            sec = (h.get("sector") or "").lower()
            pe = float(h.get("pe") or h.get("pe_forward") or 20.0)
            mcap = float(h.get("market_cap") or 1e10)
            weight = float(h.get("weight") or 0.0)

            shock_multiplier = 1.0
            if key == "RATE_SHOCK_150BPS":
                if pe > 35.0:
                    shock_multiplier = 1.6
                elif pe < 15.0:
                    shock_multiplier = 0.6
            elif key == "TECH_SEMI_DRAWDOWN_25PCT":
                if "tech" in sec or "semi" in sec or "software" in sec:
                    shock_multiplier = 1.8
                elif "health" in sec or "defen" in sec or "util" in sec:
                    shock_multiplier = 0.3
            elif key == "SMALLCAP_LIQUIDITY_CRUNCH":
                if mcap < 5e9:  # Small/Micro
                    shock_multiplier = 1.7
                elif mcap > 1e11:  # Mega
                    shock_multiplier = 0.5
            elif key == "STAGFLATION_ENERGY_SPIKE":
                gm = float(h.get("gross_margin") or 0.40)
                if gm < 0.25:
                    shock_multiplier = 1.5
                elif gm > 0.60:
                    shock_multiplier = 0.6

            impact = base_shock * shock_multiplier
            asset_impacts.append({
                "ticker": h.get("ticker", "UNKNOWN"),
                "weight": round(weight, 4),
                "estimated_impact_pct": round(impact, 2),
                "weighted_contribution_pct": round(impact * weight, 2),
            })

        portfolio_drawdown = sum(a["weighted_contribution_pct"] for a in asset_impacts)
        drawdowns.append(portfolio_drawdown)

        scenario_results[key] = {
            "title": sc["title"],
            "description": sc["description"],
            "portfolio_drawdown_pct": round(portfolio_drawdown, 2),
            "asset_breakdown": asset_impacts,
        }

    worst_dd = min(drawdowns) if drawdowns else 0.0
    resilience_score = max(0.0, min(100.0, round(100.0 + worst_dd * 3.5, 1)))

    return {
        "scenarios": scenario_results,
        "resilience_score": resilience_score,
        "worst_drawdown_pct": round(worst_dd, 2),
    }

