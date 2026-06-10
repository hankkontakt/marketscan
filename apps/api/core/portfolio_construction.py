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
