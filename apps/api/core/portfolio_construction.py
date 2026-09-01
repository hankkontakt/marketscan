"""
portfolio_construction.py — Portfoljkonstruktion (ERC + Black-Litterman).

Riskparitet (ERC): robust baslinje som bara kraver kovariansmatris.
Black-Litterman: kombinerar marknadsprior med AI-views for posterior-vikter.

All ren NumPy/SciPy — inga externa beroenden.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from scipy.optimize import minimize
    HAS_NUMPY_SCIPY = True
except ImportError:
    np = None  # type: ignore
    minimize = None  # type: ignore
    HAS_NUMPY_SCIPY = False


def equal_risk_contribution(cov) -> list[float] | object:
    """Equal Risk Contribution (ERC / Risk Parity).

    Varje tillgang bidrar lika mycket till portfoljrisken.
    Long-only, summa=1.
    """
    if not HAS_NUMPY_SCIPY:
        raise NotImplementedError("Heavy optimization requires numpy and scipy.")
    cov = np.asarray(cov)
    n = cov.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    def _risk_contribution(weights: np.ndarray) -> np.ndarray:
        port_var = weights @ cov @ weights
        if port_var <= 0:
            return np.zeros(n)
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
        return np.ones(n) / n

    w = result.x
    w = np.maximum(w, 0)
    w = w / w.sum()
    return w


def black_litterman(
    market_caps,
    cov,
    views: list[dict],
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    max_position_pct: float = 0.25,
    target_volatility: Optional[float] = None,
):
    """Black-Litterman portfoljkonstruktion med AI-views."""
    if not HAS_NUMPY_SCIPY:
        raise NotImplementedError("Heavy optimization requires numpy and scipy.")
    market_caps = np.asarray(market_caps)
    cov = np.asarray(cov)
    n = len(market_caps)
    if n == 0:
        return np.array([])

    total_mcap = market_caps.sum()
    w_mkt = market_caps / total_mcap if total_mcap > 0 else np.ones(n) / n
    pi = risk_aversion * cov @ w_mkt

    k = len(views)
    if k == 0:
        er = pi
        cov_post = cov
    else:
        P = np.zeros((k, n))
        Q = np.zeros(k)
        omega_diag = np.zeros(k)

        for i, view in enumerate(views):
            idx = view["ticker_idx"]
            conf = min(max(view.get("confidence", 0.5), 0.05), 0.95)
            P[i, idx] = 1.0
            Q[i] = view.get("expected_excess_return", 0.0)
            asset_var = cov[idx, idx]
            omega_diag[i] = asset_var * (1.0 - conf) / conf

        Omega = np.diag(omega_diag)
        tau_sigma = tau * cov
        tau_sigma_inv = np.linalg.pinv(tau_sigma)
        omega_inv = np.linalg.pinv(Omega)

        M_inv = tau_sigma_inv + P.T @ omega_inv @ P
        M = np.linalg.pinv(M_inv)

        er = M @ (tau_sigma_inv @ pi + P.T @ omega_inv @ Q)
        cov_post = cov + M

    def _neg_utility(weights: np.ndarray) -> float:
        port_return = weights @ er
        port_var = weights @ cov_post @ weights
        return -(port_return - 0.5 * risk_aversion * port_var)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, max_position_pct)] * n
    x0 = np.ones(n) / n

    res = minimize(
        _neg_utility, x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if res.success:
        weights = np.maximum(res.x, 0)
        weights = weights / weights.sum()
    else:
        logger.warning("BL-optimering konvergerade inte: %s — anvander marknadsvikter", res.message)
        weights = w_mkt

    if target_volatility is not None and target_volatility > 0:
        port_vol = float(np.sqrt(weights @ cov_post @ weights))
        if port_vol > target_volatility:
            cash = 1.0 - (target_volatility / port_vol)
            weights = weights / weights.sum() * (1 - cash)
            logger.info("BL: vol constraint applied (%.1f%% -> %.1f%%)", port_vol * 100, target_volatility * 100)

    return weights


def portfolio_stats(
    weights,
    cov,
    expected_returns=None,
) -> dict:
    """Berakna portfoljstatistik."""
    if not HAS_NUMPY_SCIPY:
        return {"expected_return": 0, "volatility": 0, "sharpe": 0, "var_95": 0}
    weights = np.asarray(weights)
    cov = np.asarray(cov)
    if len(weights) == 0:
        return {"expected_return": 0, "volatility": 0, "sharpe": 0, "var_95": 0}

    vol = float(np.sqrt(weights @ cov @ weights))
    ret = float(weights @ expected_returns) if expected_returns is not None else 0.0
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
    """Optimerar och konstruerar en Barbell-portfolj med sektortak och riskkontroll."""
    if not candidates:
        return {"holdings": [], "metrics": {}, "sector_breakdown": {}}

    core_pool = []
    satellite_pool = []

    for c in candidates:
        seg = c.get("segment", "large_cap")
        rank = float(c.get("master_rank") or 0.0)
        pctl = float(c.get("master_rank_pctl") or rank)
        if seg in ("large_cap", "mid_cap") and (rank >= 65.0 or pctl >= 60.0):
            core_pool.append(c)
        else:
            satellite_pool.append(c)

    core_pool.sort(key=lambda x: float(x.get("master_rank_pctl") or x.get("master_rank") or 0.0), reverse=True)
    satellite_pool.sort(key=lambda x: float(x.get("master_rank_pctl") or x.get("master_rank") or 0.0), reverse=True)

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
                "thesis": f"Satellit-alpha: Tillvaxt {round(float(c.get('revenue_growth') or 0.0)*100, 1)}%, Rank {c.get('master_rank')}"
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
        "title": "Rantechock (+150 bps)",
        "description": "Kraftigt stigande marknadsrantor som pressar hogt varderade tillvaxtmultiplar och hogt belanade bolag (motsvarande 2022).",
        "market_shock_pct": -12.0,
    },
    "TECH_SEMI_DRAWDOWN_25PCT": {
        "title": "Teknik- & Halvledarnedgang (-25%)",
        "description": "Cyklisk avkylning och multipelkontraktion inom tech och halvledare.",
        "market_shock_pct": -15.0,
    },
    "SMALLCAP_LIQUIDITY_CRUNCH": {
        "title": "Smabolags- & Likviditetskris (-20%)",
        "description": "Likviditeten torkar upp i smabolagssegmentet med kraftig spreadvidgning som foljd.",
        "market_shock_pct": -10.0,
    },
    "STAGFLATION_ENERGY_SPIKE": {
        "title": "Stagflations- & Ravaruchock (+30% Olja)",
        "description": "Ihallande kostnadsinflation som pressar bruttomarginaler for bolag utan prissattningskraft.",
        "market_shock_pct": -8.0,
    },
}


def stress_test_portfolio(holdings: list[dict]) -> dict:
    """Stresstestar en portfolj mot 4 standardiserade kris-scenarier."""
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
                if mcap < 5e9:
                    shock_multiplier = 1.7
                elif mcap > 1e11:
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
