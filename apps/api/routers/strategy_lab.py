"""
Strategy Lab API — backtesting, signal analytics, and strategy management.

Endpoints:
  GET    /api/strategies              — list user strategies + public strategies
  POST   /api/strategies              — create strategy
  PUT    /api/strategies/{id}         — update strategy
  DELETE /api/strategies/{id}         — delete strategy
  POST   /api/strategies/{id}/run     — trigger a new backtest run (async via DB flag)
  GET    /api/strategies/{id}/results — backtest results + equity curve
  GET    /api/strategies/compare      — compare multiple runs side-by-side
  GET    /api/signal-analytics        — all signal transition statistics
  GET    /api/signal-analytics/{from_signal}/{to_signal} — specific transition stats
"""
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, field_validator

from apps.api.dependencies import get_user_supabase
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["strategy-lab"])

# ─── Pydantic Models ──────────────────────────────────────────────────────────

REBALANCE_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly"}
POSITION_SIZING_METHODS = {"equal", "score_weighted", "kelly"}


class StrategyIn(BaseModel):
    name:             str
    description:      str | None = None
    filter_json:      dict = {}
    max_positions:    int = 20
    position_sizing:  str = "equal"
    rebalance_freq:   str = "monthly"
    initial_capital:  float = 100_000.0
    commission_pct:   float = 0.001
    is_public:        bool = False

    @field_validator("position_sizing")
    @classmethod
    def validate_sizing(cls, v: str) -> str:
        if v not in POSITION_SIZING_METHODS:
            raise ValueError(f"position_sizing must be one of {sorted(POSITION_SIZING_METHODS)}")
        return v

    @field_validator("rebalance_freq")
    @classmethod
    def validate_freq(cls, v: str) -> str:
        if v not in REBALANCE_FREQUENCIES:
            raise ValueError(f"rebalance_freq must be one of {sorted(REBALANCE_FREQUENCIES)}")
        return v


class StrategyUpdate(BaseModel):
    name:            str | None = None
    description:     str | None = None
    filter_json:     dict | None = None
    max_positions:   int | None = None
    position_sizing: str | None = None
    rebalance_freq:  str | None = None
    initial_capital: float | None = None
    commission_pct:  float | None = None
    is_public:       bool | None = None


# ─── Strategies CRUD ──────────────────────────────────────────────────────────

@router.get("/api/strategies")
async def list_strategies(
    include_public: bool = Query(True),
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    List user's own strategies + optionally public strategies from others.
    Returns latest run metrics per strategy.
    """
    # Own strategies
    own = (
        sb.table("strategies")
        .select("*, strategy_runs(id, status, total_return_pct, sharpe_ratio, max_drawdown_pct, cagr_pct, completed_at)")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    strategies = own.data or []

    if include_public:
        pub = (
            sb.table("strategies")
            .select("id, name, description, max_positions, position_sizing, rebalance_freq, created_at, strategy_runs(id, status, total_return_pct, sharpe_ratio, max_drawdown_pct, cagr_pct)")
            .eq("is_public", True)
            .neq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        # Tag ownership
        for s in (pub.data or []):
            s["_is_own"] = False
        for s in strategies:
            s["_is_own"] = True
        strategies = strategies + (pub.data or [])

    return strategies


@router.post("/api/strategies", status_code=201)
async def create_strategy(
    body: StrategyIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Create a new strategy."""
    payload = {
        "user_id":          user.id,
        "name":             body.name,
        "description":      body.description,
        "filter_json":      body.filter_json,
        "max_positions":    body.max_positions,
        "position_sizing":  body.position_sizing,
        "rebalance_freq":   body.rebalance_freq,
        "initial_capital":  body.initial_capital,
        "commission_pct":   body.commission_pct,
        "is_public":        body.is_public,
    }
    res = sb.table("strategies").insert(payload).execute()
    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Misslyckades skapa strategi")
    return res.data[0]


@router.put("/api/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Update a strategy. Only the owner can update."""
    existing = (
        sb.table("strategies").select("id")
        .eq("id", strategy_id).eq("user_id", user.id).limit(1).execute()
    )
    if not existing.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi hittades inte")

    updates: dict = {}
    if body.name is not None:            updates["name"] = body.name
    if body.description is not None:     updates["description"] = body.description
    if body.filter_json is not None:     updates["filter_json"] = body.filter_json
    if body.max_positions is not None:   updates["max_positions"] = body.max_positions
    if body.position_sizing is not None: updates["position_sizing"] = body.position_sizing
    if body.rebalance_freq is not None:  updates["rebalance_freq"] = body.rebalance_freq
    if body.initial_capital is not None: updates["initial_capital"] = body.initial_capital
    if body.commission_pct is not None:  updates["commission_pct"] = body.commission_pct
    if body.is_public is not None:       updates["is_public"] = body.is_public

    if not updates:
        return existing.data[0]

    res = (
        sb.table("strategies").update(updates)
        .eq("id", strategy_id).eq("user_id", user.id).execute()
    )
    return res.data[0] if res.data else {"ok": True}


@router.delete("/api/strategies/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Delete a strategy and all associated runs."""
    existing = (
        sb.table("strategies").select("id")
        .eq("id", strategy_id).eq("user_id", user.id).limit(1).execute()
    )
    if not existing.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi hittades inte")

    # Cascade: runs + equity deleted via FK ON DELETE CASCADE in migration
    sb.table("strategies").delete().eq("id", strategy_id).execute()
    return None


# ─── Backtest Runs ────────────────────────────────────────────────────────────

@router.post("/api/strategies/{strategy_id}/run", status_code=202)
async def trigger_backtest(
    strategy_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Queue a new backtest run for the strategy.
    Returns the run_id immediately (status: pending).
    The actual computation is done by backend_worker/strategy_backtester.py
    which picks up pending runs from the DB.

    For now, we also attempt to run it synchronously in the background task
    if DATABASE_URL is available (worker mode). This is best-effort.
    """
    # Verify strategy ownership (or public access)
    strat = (
        sb.table("strategies").select("*")
        .eq("id", strategy_id)
        .execute()
    )
    if not strat.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi hittades inte")

    strat_data = strat.data[0]
    if strat_data["user_id"] != user.id and not strat_data.get("is_public"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Åtkomst nekad")

    # Create a pending run record using service client (needs insert on strategy_runs)
    # The actual run is created by backend_worker; for the API we use the user client
    # with RLS (user_id match).
    run_payload = {
        "strategy_id": strategy_id,
        "user_id":     user.id,
        "status":      "pending",
    }
    run_res = sb.table("strategy_runs").insert(run_payload).execute()
    if not run_res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Misslyckades köa backtest")

    run = run_res.data[0]
    run_id = run["id"]

    # Attempt background execution in-process (best-effort — works if DATABASE_URL set)
    def _run_backtest():
        import os
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            logger.warning("DATABASE_URL not set — backtest queued for external worker")
            return
        try:
            from backend_worker.strategy_backtester import run_backtest
            run_backtest(strategy_id, dsn, existing_run_id=run_id)
            logger.info("Backtest %s completed in background", run_id)
        except Exception as exc:
            logger.error("Backtest %s failed: %s", run_id, exc)

    background_tasks.add_task(_run_backtest)

    return {"run_id": run_id, "status": "pending", "message": "Backtest köat"}


@router.get("/api/strategies/{strategy_id}/results")
async def get_backtest_results(
    strategy_id: str,
    run_id: str | None = Query(None, description="Specifikt run-id, eller senaste om utelämnat"),
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Get backtest results for a strategy.
    Returns metrics + equity curve.
    """
    # Check strategy access
    strat = (
        sb.table("strategies").select("id, user_id, is_public")
        .eq("id", strategy_id).limit(1).execute()
    )
    if not strat.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Strategi hittades inte")

    s = strat.data[0]
    if s["user_id"] != user.id and not s.get("is_public"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Åtkomst nekad")

    # Get run
    run_q = (
        sb.table("strategy_runs")
        .select("*")
        .eq("strategy_id", strategy_id)
    )
    if run_id:
        run_q = run_q.eq("id", run_id)
    else:
        run_q = run_q.order("created_at", desc=True).limit(1)

    run_res = run_q.execute()
    if not run_res.data:
        return {"status": "no_runs", "message": "Inga backtester hittades"}

    run = run_res.data[0]
    current_run_id = run["id"]

    # Get equity curve
    equity_res = (
        sb.table("strategy_daily_equity")
        .select("date, portfolio_value, daily_return_pct, num_positions")
        .eq("run_id", current_run_id)
        .order("date", desc=False)
        .execute()
    )

    return {
        "run":         run,
        "equity_curve": equity_res.data or [],
    }


@router.get("/api/strategies/compare")
async def compare_strategies(
    run_ids: str = Query(..., description="Kommaseparerade run-IDs (max 5)"),
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Compare multiple backtest runs side-by-side.
    Returns metrics for each run + normalized equity curves.
    """
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    if not ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Inga run-IDs")
    if len(ids) > 5:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Max 5 runs")

    results = []
    for rid in ids:
        run_res = (
            sb.table("strategy_runs")
            .select("*, strategies(name, position_sizing, rebalance_freq, filter_json, user_id, is_public)")
            .eq("id", rid)
            .limit(1).execute()
        )
        if not run_res.data:
            continue

        run = run_res.data[0]
        strat = run.get("strategies") or {}

        # Access control: own or public
        if strat.get("user_id") != user.id and not strat.get("is_public"):
            continue

        equity_res = (
            sb.table("strategy_daily_equity")
            .select("date, portfolio_value")
            .eq("run_id", rid)
            .order("date", desc=False)
            .execute()
        )

        # Normalize to 100 at start
        equity = equity_res.data or []
        if equity and equity[0].get("portfolio_value"):
            base = float(equity[0]["portfolio_value"])
            for row in equity:
                pv = row.get("portfolio_value")
                row["normalized"] = round(float(pv) / base * 100, 2) if pv and base else None

        results.append({
            "run_id":       rid,
            "strategy_name": strat.get("name") or "–",
            "metrics":      {
                "total_return_pct":  run.get("total_return_pct"),
                "cagr_pct":          run.get("cagr_pct"),
                "sharpe_ratio":      run.get("sharpe_ratio"),
                "sortino_ratio":     run.get("sortino_ratio"),
                "max_drawdown_pct":  run.get("max_drawdown_pct"),
                "calmar_ratio":      run.get("calmar_ratio"),
                "volatility":        run.get("volatility"),
                "win_rate_pct":      run.get("win_rate_pct"),
                "total_trades":      run.get("total_trades"),
                "avg_hold_days":     run.get("avg_hold_days"),
                "profit_factor":     run.get("profit_factor"),
            },
            "equity_curve": equity,
        })

    return results


# ─── Signal Analytics ─────────────────────────────────────────────────────────

@router.get("/api/signal-analytics")
async def get_signal_analytics(
    field: str | None = Query(None, description="entry_signal eller trend_signal"),
    min_samples: int = Query(5, ge=2),
    sb=Depends(get_user_supabase),
):
    """
    All cached signal transition statistics.
    Public endpoint (signal_persistence_cache has public read RLS).
    """
    q = (
        sb.table("signal_persistence_cache")
        .select("*")
        .gte("sample_count", min_samples)
        .order("sample_count", desc=True)
    )
    if field:
        q = q.eq("field", field)

    res = q.execute()
    rows = res.data or []

    # Enrich: add a human-readable label for the transition
    for r in rows:
        r["label"] = f"{r.get('from_signal', '?')} → {r.get('to_signal', '?')}"

    return rows


@router.get("/api/signal-analytics/{field}/{from_signal}/{to_signal}")
async def get_signal_analytics_detail(
    field: str,
    from_signal: str,
    to_signal: str,
    sb=Depends(get_user_supabase),
):
    """
    Detailed statistics for a specific signal transition.
    Also includes recent example transitions (last 30 days).
    """
    # Cache entry
    cache = (
        sb.table("signal_persistence_cache")
        .select("*")
        .eq("field", field)
        .eq("from_signal", from_signal)
        .eq("to_signal", to_signal)
        .limit(1).execute()
    )

    stats = cache.data[0] if cache.data else None

    # Recent examples
    examples = (
        sb.table("signal_transitions")
        .select("ticker, transition_date, price_at, score_total_at")
        .eq("field", field)
        .eq("from_value", from_signal)
        .eq("to_value", to_signal)
        .order("transition_date", desc=True)
        .limit(20)
        .execute()
    )

    # Enrich with current name from scan_results
    example_rows = examples.data or []
    if example_rows:
        tickers = list({r["ticker"] for r in example_rows})
        names_res = (
            sb.table("scan_results")
            .select("ticker, name, score_total, entry_signal")
            .in_("ticker", tickers).execute()
        )
        names_map = {r["ticker"]: r for r in (names_res.data or [])}
        for r in example_rows:
            info = names_map.get(r["ticker"], {})
            r["name"]          = info.get("name") or r["ticker"]
            r["current_score"] = info.get("score_total")
            r["current_signal"] = info.get("entry_signal")

    return {
        "stats":    stats,
        "examples": example_rows,
        "label":    f"{from_signal} → {to_signal}",
        "field":    field,
    }
