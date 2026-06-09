"""
Portfolio Risk Analytics API — deep risk metrics, optimization, and rebalancing.

Endpoints:
  GET /api/portfolio/analytics      — full risk report (reads from nightly cache)
  GET /api/portfolio/analytics/factor — factor exposure vs benchmark
  GET /api/portfolio/optimize       — optimal portfolio weights (HRP / min-variance / equal)
  GET /api/portfolio/rebalance      — drift analysis + buy/sell suggestions
  POST /api/portfolio/rebalance/targets — save target allocations
  GET /api/portfolio/rebalance/targets  — get saved targets

Cache: risk metrics are computed nightly by risk_analyzer.py and stored in
portfolio_risk_cache. If no cache exists (new user, first day), the endpoint
returns a simplified version computed from scan_results in real-time.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.dependencies import get_user_supabase
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["risk"])


# ─── Response Models ──────────────────────────────────────────────────────────

class RiskMetrics(BaseModel):
    sharpe_ratio:     float | None = None
    sortino_ratio:    float | None = None
    calmar_ratio:     float | None = None
    total_return_pct: float | None = None
    cagr_pct:         float | None = None
    volatility_ann:   float | None = None
    max_drawdown_pct: float | None = None
    var_95_pct:       float | None = None   # 1-day 95% VaR
    cvar_95_pct:      float | None = None   # 1-day 95% CVaR
    beta_market:      float | None = None
    num_holdings:     int | None = None
    top_holding_pct:  float | None = None
    sector_hhi:       float | None = None   # 0=diversified, 1=concentrated
    computed_at:      str | None = None
    is_cached:        bool = False          # True if from nightly cache


class CorrelationOut(BaseModel):
    tickers: list[str]
    matrix:  list[list[float]]


class OptimizeOut(BaseModel):
    method:        str
    weights:       dict[str, float]   # {ticker: weight (0-1)}
    expected_return_pct: float | None = None
    expected_vol_pct:    float | None = None


class HoldingDrift(BaseModel):
    ticker:         str
    name:           str | None = None
    current_pct:    float
    target_pct:     float | None = None
    drift_pct:      float
    action:         str          # "buy" | "sell" | "hold"
    amount_sek:     float | None = None


class RebalanceOut(BaseModel):
    total_value:    float
    drifted:        bool
    holdings:       list[HoldingDrift]
    target_name:    str | None = None


class FactorExposureOut(BaseModel):
    factor_value:     float | None = None
    factor_momentum:  float | None = None
    factor_quality:   float | None = None
    factor_growth:    float | None = None
    factor_dividend:  float | None = None
    factor_risk:      float | None = None
    bench_value:      float | None = None
    bench_momentum:   float | None = None
    bench_quality:    float | None = None
    bench_growth:     float | None = None
    bench_dividend:   float | None = None
    bench_risk:       float | None = None
    computed_at:      str | None = None


class RebalTargetIn(BaseModel):
    name:    str = "Mitt mål"
    targets: list[dict]       # [{ticker, target_pct}] or [{sector, target_pct}]
    method:  str = "ticker"   # "ticker" | "sector"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_portfolio_id(user_id: str, sb) -> str | None:
    port = (
        sb.table("portfolios").select("id")
        .eq("user_id", user_id).limit(1).execute()
    )
    return port.data[0]["id"] if port.data else None


def _get_holdings_with_prices(portfolio_id: str, sb) -> list[dict]:
    h = sb.table("holdings").select("*").eq("portfolio_id", portfolio_id).execute()
    if not h.data:
        return []
    tickers = [x["ticker"] for x in h.data]
    scan = (
        sb.table("scan_results")
        .select("ticker, name, price, sector, score_total")
        .in_("ticker", tickers).execute()
    )
    scan_map = {r["ticker"]: r for r in (scan.data or [])}
    for item in h.data:
        info = scan_map.get(item["ticker"], {})
        item["price"]       = info.get("price") or item.get("cost_basis")
        item["name"]        = info.get("name") or item["ticker"]
        item["sector"]      = info.get("sector")
        item["score_total"] = info.get("score_total")
    return h.data


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/analytics", response_model=RiskMetrics)
def get_risk_analytics(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Full portfolio risk metrics.
    Returns cached nightly computation if available, otherwise computes
    simplified metrics from scan_results (no historical price data needed).
    """
    # Try nightly cache first
    cache = (
        sb.table("portfolio_risk_cache")
        .select("*")
        .eq("user_id", user.id)
        .limit(1).execute()
    )

    if cache.data:
        c = cache.data[0]
        return RiskMetrics(
            sharpe_ratio     = c.get("sharpe_ratio"),
            sortino_ratio    = c.get("sortino_ratio"),
            calmar_ratio     = c.get("calmar_ratio"),
            total_return_pct = c.get("total_return_pct"),
            cagr_pct         = c.get("cagr_pct"),
            volatility_ann   = c.get("volatility_ann"),
            max_drawdown_pct = c.get("max_drawdown_pct"),
            var_95_pct       = c.get("var_95_pct"),
            cvar_95_pct      = c.get("cvar_95_pct"),
            beta_market      = c.get("beta_market"),
            num_holdings     = c.get("num_holdings"),
            top_holding_pct  = c.get("top_holding_pct"),
            sector_hhi       = c.get("sector_hhi"),
            computed_at      = str(c.get("computed_at", "")),
            is_cached        = True,
        )

    # Fallback: simplified real-time metrics from scan_results
    portfolio_id = _get_portfolio_id(user.id, sb)
    if not portfolio_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")

    holdings = _get_holdings_with_prices(portfolio_id, sb)
    if not holdings:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inga innehav hittade")

    # Calculate simplified metrics using scan_results data
    total_value = sum(
        float(h.get("price") or 0) * float(h.get("shares") or 0)
        for h in holdings
    )
    if total_value == 0:
        return RiskMetrics(num_holdings=len(holdings), is_cached=False)

    weights = [
        float(h.get("price") or 0) * float(h.get("shares") or 0) / total_value
        for h in holdings
    ]

    # Fetch beta and vol from scan_results
    tickers = [h["ticker"] for h in holdings]
    scan = (
        sb.table("scan_results")
        .select("ticker, beta, vol_20d")
        .in_("ticker", tickers).execute()
    )
    scan_map = {r["ticker"]: r for r in (scan.data or [])}

    # Portfolio beta (weighted)
    betas  = [float(scan_map.get(h["ticker"], {}).get("beta") or 1.0) for h in holdings]
    port_beta = sum(b * w for b, w in zip(betas, weights))

    # Portfolio vol (simplified: weighted avg vol × sqrt of correlation assumption 0.5)
    vols = [float(scan_map.get(h["ticker"], {}).get("vol_20d") or 0.015) for h in holdings]
    port_vol_daily = sum(v * w for v, w in zip(vols, weights))
    import math
    port_vol_ann = round(port_vol_daily * math.sqrt(252) * 100, 2)

    # Sharpe approximation (no historical returns available without cache)
    # Use scan_results score as proxy for quality

    # Top holding concentration
    top_holding_pct = round(max(weights) * 100, 2)

    # Sector HHI
    from collections import Counter
    sector_values: dict[str, float] = Counter()
    for h, w in zip(holdings, weights):
        sector_values[h.get("sector") or "Övrigt"] += w
    sector_hhi = round(sum(v ** 2 for v in sector_values.values()), 4)

    # Return-based metrics (Sharpe, Sortino, drawdown, VaR/CVaR, CAGR) need a
    # price-return time series, which scan_results doesn't have. Compute them
    # live from 1y daily history (Yahoo via httpx). Best-effort — if there isn't
    # enough history we keep the simplified beta/vol from scan_results.
    live = {}
    try:
        from apps.api.core.risk_calc import compute_live_risk
        live = compute_live_risk(holdings)
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("live risk computation skipped: %s", e)

    return RiskMetrics(
        sharpe_ratio     = live.get("sharpe_ratio"),
        sortino_ratio    = live.get("sortino_ratio"),
        total_return_pct = live.get("total_return_pct"),
        cagr_pct         = live.get("cagr_pct"),
        max_drawdown_pct = live.get("max_drawdown_pct"),
        var_95_pct       = live.get("var_95_pct"),
        cvar_95_pct      = live.get("cvar_95_pct"),
        beta_market      = live.get("beta_market") if live.get("beta_market") is not None else round(port_beta, 4),
        volatility_ann   = live.get("volatility_ann") if live.get("volatility_ann") is not None else port_vol_ann,
        num_holdings     = len(holdings),
        top_holding_pct  = top_holding_pct,
        sector_hhi       = sector_hhi,
        is_cached        = False,
    )


@router.get("/analytics/factor", response_model=FactorExposureOut)
def get_factor_exposure(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Portfolio factor exposure vs benchmark universe average."""
    cache = (
        sb.table("portfolio_factor_exposure")
        .select("*").eq("user_id", user.id).limit(1).execute()
    )
    if cache.data:
        c = cache.data[0]
        return FactorExposureOut(
            factor_value    = c.get("factor_value"),
            factor_momentum = c.get("factor_momentum"),
            factor_quality  = c.get("factor_quality"),
            factor_growth   = c.get("factor_growth"),
            factor_dividend = c.get("factor_dividend"),
            factor_risk     = c.get("factor_risk"),
            bench_value     = c.get("bench_value"),
            bench_momentum  = c.get("bench_momentum"),
            bench_quality   = c.get("bench_quality"),
            bench_growth    = c.get("bench_growth"),
            bench_dividend  = c.get("bench_dividend"),
            bench_risk      = c.get("bench_risk"),
            computed_at     = str(c.get("computed_at", "")),
        )

    # Real-time fallback: compute from current scan_results
    portfolio_id = _get_portfolio_id(user.id, sb)
    if not portfolio_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")

    holdings = _get_holdings_with_prices(portfolio_id, sb)
    if not holdings:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inga innehav hittade")

    tickers = [h["ticker"] for h in holdings]
    total_value = sum(float(h.get("price") or 0) * float(h.get("shares") or 0) for h in holdings)
    if total_value == 0:
        return FactorExposureOut()

    scan = (
        sb.table("scan_results")
        .select("ticker,score_value,score_momentum,score_quality,score_growth,score_dividend,score_risk")
        .in_("ticker", tickers).execute()
    )
    scan_map = {r["ticker"]: r for r in (scan.data or [])}

    # Benchmark averages
    bench = (
        sb.table("scan_results")
        .select("score_value,score_momentum,score_quality,score_growth,score_dividend,score_risk")
        .execute()
    )
    bench_rows = bench.data or []

    def _wavg(field: str) -> float | None:
        total_w = 0.0
        weighted = 0.0
        for h in holdings:
            price = float(h.get("price") or 0)
            shares = float(h.get("shares") or 0)
            w = price * shares / total_value
            v = scan_map.get(h["ticker"], {}).get(field)
            if v is not None:
                weighted += float(v) * w
                total_w += w
        return round(weighted / total_w, 2) if total_w > 0 else None

    def _bavg(field: str) -> float | None:
        vals = [float(r[field]) for r in bench_rows if r.get(field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return FactorExposureOut(
        factor_value    = _wavg("score_value"),
        factor_momentum = _wavg("score_momentum"),
        factor_quality  = _wavg("score_quality"),
        factor_growth   = _wavg("score_growth"),
        factor_dividend = _wavg("score_dividend"),
        factor_risk     = _wavg("score_risk"),
        bench_value     = _bavg("score_value"),
        bench_momentum  = _bavg("score_momentum"),
        bench_quality   = _bavg("score_quality"),
        bench_growth    = _bavg("score_growth"),
        bench_dividend  = _bavg("score_dividend"),
        bench_risk      = _bavg("score_risk"),
    )


@router.get("/analytics/correlation", response_model=CorrelationOut)
def get_correlation(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Correlation matrix from nightly cache."""
    cache = (
        sb.table("portfolio_risk_cache")
        .select("correlation_matrix,tickers_ordered")
        .eq("user_id", user.id).limit(1).execute()
    )
    if not cache.data or not cache.data[0].get("correlation_matrix"):
        # Return single identity matrix if no cache
        portfolio_id = _get_portfolio_id(user.id, sb)
        tickers = []
        if portfolio_id:
            h = sb.table("holdings").select("ticker").eq("portfolio_id", portfolio_id).execute()
            tickers = [r["ticker"] for r in (h.data or [])]
        n = max(len(tickers), 1)
        import numpy as np
        matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        return CorrelationOut(tickers=tickers, matrix=matrix)

    c = cache.data[0]
    return CorrelationOut(
        tickers = c.get("tickers_ordered") or [],
        matrix  = c.get("correlation_matrix") or [],
    )


@router.get("/optimize", response_model=list[OptimizeOut])
def get_optimized_weights(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Return HRP and min-variance optimal weights from nightly cache."""
    cache = (
        sb.table("portfolio_risk_cache")
        .select("hrp_weights,minvar_weights,tickers_ordered")
        .eq("user_id", user.id).limit(1).execute()
    )

    portfolio_id = _get_portfolio_id(user.id, sb)
    if not portfolio_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")

    holdings = _get_holdings_with_prices(portfolio_id, sb)
    if not holdings:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inga innehav hittade")

    tickers = [h["ticker"] for h in holdings]
    n = len(tickers)

    if cache.data and cache.data[0].get("hrp_weights"):
        c = cache.data[0]
        hrp_w    = c.get("hrp_weights") or {}
        minvar_w = c.get("minvar_weights") or {}
    else:
        # Fallback: equal weights
        hrp_w    = {t: round(1.0 / n, 6) for t in tickers}
        minvar_w = hrp_w

    # Equal weight for comparison
    equal_w = {t: round(1.0 / n, 6) for t in tickers}

    return [
        OptimizeOut(method="hrp",    weights=hrp_w),
        OptimizeOut(method="minvar", weights=minvar_w),
        OptimizeOut(method="equal",  weights=equal_w),
    ]


@router.get("/rebalance", response_model=RebalanceOut)
def get_rebalance_suggestions(
    target_name: str | None = None,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Drift analysis: compare current allocation vs target.
    If no target is set, compare vs HRP optimal weights.
    Drift threshold: 5% absolute difference triggers a buy/sell suggestion.
    """
    DRIFT_THRESHOLD = 5.0  # percent

    portfolio_id = _get_portfolio_id(user.id, sb)
    if not portfolio_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")

    holdings = _get_holdings_with_prices(portfolio_id, sb)
    if not holdings:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inga innehav hittade")

    total_value = sum(
        float(h.get("price") or 0) * float(h.get("shares") or 0)
        for h in holdings
    )
    if total_value == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Inga priser tillgängliga")

    # Current weights
    current_weights = {
        h["ticker"]: round(
            float(h.get("price") or 0) * float(h.get("shares") or 0) / total_value * 100,
            2,
        )
        for h in holdings
    }

    # Target weights
    target_weights: dict[str, float] = {}
    loaded_target_name: str | None = None

    if target_name:
        target_res = (
            sb.table("rebalancing_targets")
            .select("*").eq("user_id", user.id).eq("name", target_name).limit(1).execute()
        )
        if target_res.data:
            tgt = target_res.data[0]
            loaded_target_name = tgt["name"]
            for entry in (tgt.get("targets") or []):
                ticker = entry.get("ticker")
                pct    = entry.get("target_pct")
                if ticker and pct is not None:
                    target_weights[ticker] = float(pct)

    if not target_weights:
        # Use HRP optimal weights from cache if available
        cache = (
            sb.table("portfolio_risk_cache")
            .select("hrp_weights").eq("user_id", user.id).limit(1).execute()
        )
        if cache.data and cache.data[0].get("hrp_weights"):
            hrp = cache.data[0]["hrp_weights"]
            target_weights = {t: round(float(v) * 100, 2) for t, v in hrp.items()}
            loaded_target_name = "HRP-optimalt"
        else:
            # Fallback: equal weight
            n = len(holdings)
            target_weights = {h["ticker"]: round(100.0 / n, 2) for h in holdings}
            loaded_target_name = "Lika viktning"

    # Compute drift
    drift_items = []
    drifted = False
    holdings_map = {h["ticker"]: h for h in holdings}

    for ticker, curr_pct in current_weights.items():
        tgt_pct = target_weights.get(ticker)
        drift   = curr_pct - (tgt_pct or 0)
        h       = holdings_map[ticker]

        if tgt_pct is not None and abs(drift) >= DRIFT_THRESHOLD:
            drifted = True
            if drift > 0:
                action = "sell"
                amount = round(abs(drift / 100) * total_value, 0)
            else:
                action = "buy"
                amount = round(abs(drift / 100) * total_value, 0)
        else:
            action = "hold"
            amount = None

        drift_items.append(HoldingDrift(
            ticker      = ticker,
            name        = h.get("name") or ticker,
            current_pct = round(curr_pct, 2),
            target_pct  = round(tgt_pct, 2) if tgt_pct is not None else None,
            drift_pct   = round(drift, 2),
            action      = action,
            amount_sek  = amount,
        ))

    # Sort: sell first, then buy, then hold
    order = {"sell": 0, "buy": 1, "hold": 2}
    drift_items.sort(key=lambda x: (order.get(x.action, 3), abs(x.drift_pct or 0)))

    return RebalanceOut(
        total_value  = round(total_value, 2),
        drifted      = drifted,
        holdings     = drift_items,
        target_name  = loaded_target_name,
    )


@router.post("/rebalance/targets", status_code=201)
def save_rebalance_targets(
    body: RebalTargetIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Save target allocations for rebalancing calculations."""
    import json as _json
    res = sb.table("rebalancing_targets").upsert({
        "user_id": user.id,
        "name":    body.name,
        "targets": body.targets,
        "method":  body.method,
    }, on_conflict="user_id,name").execute()
    return res.data[0] if res.data else {"ok": True}


@router.get("/rebalance/targets")
def get_rebalance_targets(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """List saved target allocations."""
    res = (
        sb.table("rebalancing_targets")
        .select("id,name,method,targets,updated_at")
        .eq("user_id", user.id).execute()
    )
    return res.data or []
