"""
Smart Alerts API — compound alert rule management + score history.

Endpoints:
  GET    /api/alerts              — list user's alert rules
  POST   /api/alerts              — create compound alert rule
  PUT    /api/alerts/{id}         — update rule (name, conditions, active)
  DELETE /api/alerts/{id}         — delete rule
  GET    /api/alerts/triggered    — triggered alert history (last 30 days)
  GET    /api/score-history/{ticker} — score/price timeline for a ticker
  GET    /api/score-history/movers   — top score movers over N days
"""
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from apps.api.dependencies import get_user_supabase
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alerts"])

# ─── Rule Types ──────────────────────────────────────────────────────────────

VALID_RULE_TYPES = {
    "price_cross",
    "score_change",
    "signal_change",
    "screen_match",
    "insider_cluster",
    "volatility_spike",
}


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class Condition(BaseModel):
    field: str
    op:    Literal[">=", "<=", ">", "<", "=", "!="]
    value: float | str


class AlertRuleIn(BaseModel):
    name:              str
    rule_type:         str
    ticker:            str | None = None
    conditions:        list[Condition] = []
    score_change_min:  float | None = None
    insider_min_count: int | None = None
    vol_spike_min_pct: float | None = None
    trigger_once:      bool = False
    active:            bool = True

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in VALID_RULE_TYPES:
            raise ValueError(f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
        return v


class AlertRuleUpdate(BaseModel):
    name:              str | None = None
    conditions:        list[Condition] | None = None
    score_change_min:  float | None = None
    insider_min_count: int | None = None
    vol_spike_min_pct: float | None = None
    trigger_once:      bool | None = None
    active:            bool | None = None


# ─── Alert Rules CRUD ─────────────────────────────────────────────────────────

@router.get("/api/alerts")
def list_alerts(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """List all alert rules for the current user."""
    res = (
        sb.table("alert_rules")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


@router.post("/api/alerts", status_code=201)
def create_alert(
    body: AlertRuleIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Create a new compound alert rule."""
    payload = {
        "user_id":           user.id,
        "name":              body.name,
        "rule_type":         body.rule_type,
        "ticker":            body.ticker,
        "conditions":        [c.model_dump() for c in body.conditions],
        "score_change_min":  body.score_change_min,
        "insider_min_count": body.insider_min_count,
        "vol_spike_min_pct": body.vol_spike_min_pct,
        "trigger_once":      body.trigger_once,
        "active":            body.active,
    }
    res = sb.table("alert_rules").insert(payload).execute()
    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Misslyckades skapa larm")
    return res.data[0]


@router.put("/api/alerts/{rule_id}")
def update_alert(
    rule_id: str,
    body: AlertRuleUpdate,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Update an existing alert rule."""
    # Verify ownership
    existing = (
        sb.table("alert_rules").select("id,user_id")
        .eq("id", rule_id).eq("user_id", user.id).limit(1).execute()
    )
    if not existing.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Larmregel hittades inte")

    updates: dict = {}
    if body.name is not None:              updates["name"] = body.name
    if body.conditions is not None:        updates["conditions"] = [c.model_dump() for c in body.conditions]
    if body.score_change_min is not None:  updates["score_change_min"] = body.score_change_min
    if body.insider_min_count is not None: updates["insider_min_count"] = body.insider_min_count
    if body.vol_spike_min_pct is not None: updates["vol_spike_min_pct"] = body.vol_spike_min_pct
    if body.trigger_once is not None:      updates["trigger_once"] = body.trigger_once
    if body.active is not None:            updates["active"] = body.active

    if not updates:
        return existing.data[0]

    res = (
        sb.table("alert_rules").update(updates)
        .eq("id", rule_id).eq("user_id", user.id).execute()
    )
    return res.data[0] if res.data else {"ok": True}


@router.delete("/api/alerts/{rule_id}", status_code=204)
def delete_alert(
    rule_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Delete an alert rule (and cascade-delete triggered_alerts)."""
    existing = (
        sb.table("alert_rules").select("id")
        .eq("id", rule_id).eq("user_id", user.id).limit(1).execute()
    )
    if not existing.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Larmregel hittades inte")

    sb.table("alert_rules").delete().eq("id", rule_id).execute()
    return None


# ─── Triggered Alerts History ─────────────────────────────────────────────────

@router.get("/api/alerts/triggered")
def get_triggered_alerts(
    limit: int = Query(50, ge=1, le=200),
    rule_type: str | None = Query(None),
    ticker: str | None = Query(None),
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Return triggered alert history for the current user (last 30 days)."""
    q = (
        sb.table("triggered_alerts")
        .select("*")
        .eq("user_id", user.id)
        .order("triggered_at", desc=True)
        .limit(limit)
    )
    if rule_type:
        q = q.eq("rule_type", rule_type)
    if ticker:
        q = q.eq("ticker", ticker.upper())

    res = q.execute()
    return res.data or []


# ─── Score History ────────────────────────────────────────────────────────────

@router.get("/api/score-history/{ticker}")
def get_score_history(
    ticker: str,
    days: int = Query(90, ge=7, le=730, description="Antal dagar bakåt"),
    fields: str = Query(
        "scan_date,score_total,score_value,score_momentum,score_quality,"
        "score_growth,score_risk,score_dividend,entry_signal,trend_signal,price",
        description="Kommaseparerade kolumner",
    ),
    sb=Depends(get_user_supabase),
):
    """
    Score and signal history for a specific ticker.
    Public — no auth required (score_history has public read RLS).
    """
    ticker_upper = ticker.upper()
    # Validate requested fields
    allowed = {
        "scan_date", "score_total", "score_value", "score_momentum",
        "score_quality", "score_growth", "score_risk", "score_dividend",
        "entry_signal", "trend_signal", "piotroski_f", "price", "vol_20d",
    }
    requested = {f.strip() for f in fields.split(",") if f.strip()}
    safe_fields = ",".join(requested & allowed) or "scan_date,score_total,entry_signal"

    res = (
        sb.table("score_history")
        .select(safe_fields)
        .eq("ticker", ticker_upper)
        .gte("scan_date", f"(NOW() - INTERVAL '{days} days')::date")
        .order("scan_date", desc=False)
        .execute()
    )
    return res.data or []


@router.get("/api/score-history/movers")
def get_score_movers(
    days: int = Query(7, ge=1, le=30),
    min_change: float = Query(5.0, ge=1.0, description="Minimum poängändring"),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["up", "down", "both"] = Query("both"),
    sb=Depends(get_user_supabase),
):
    """
    Tickers with largest score changes over the past N days.
    Public endpoint — no auth required.
    """
    # Use raw SQL via Supabase RPC for the CTE query, or approximate with two queries
    # Current scores from scan_results
    curr_res = (
        sb.table("scan_results")
        .select("ticker, name, score_total, entry_signal, trend_signal, sector")
        .execute()
    )
    curr_map = {r["ticker"]: r for r in (curr_res.data or [])}

    # Previous scores from score_history
    prev_res = (
        sb.table("score_history")
        .select("ticker, score_total, scan_date")
        .lte("scan_date", f"(NOW() - INTERVAL '{days} days')::date")
        .order("ticker")
        .order("scan_date", desc=True)
        .limit(5000)
        .execute()
    )
    # Take most recent snapshot per ticker that is ≥ days ago
    prev_map: dict[str, float] = {}
    for r in (prev_res.data or []):
        if r["ticker"] not in prev_map and r.get("score_total") is not None:
            prev_map[r["ticker"]] = float(r["score_total"])

    # Compute changes
    movers = []
    for ticker, curr in curr_map.items():
        curr_score = curr.get("score_total")
        prev_score = prev_map.get(ticker)
        if curr_score is None or prev_score is None:
            continue
        change = float(curr_score) - prev_score
        if abs(change) >= min_change:
            movers.append({**curr, "score_change": round(change, 2), "prev_score": round(prev_score, 2)})

    # Filter and sort
    if direction == "up":
        movers = [m for m in movers if m["score_change"] > 0]
        movers.sort(key=lambda x: x["score_change"], reverse=True)
    elif direction == "down":
        movers = [m for m in movers if m["score_change"] < 0]
        movers.sort(key=lambda x: x["score_change"])
    else:
        movers.sort(key=lambda x: abs(x["score_change"]), reverse=True)

    return movers[:limit]


# ─── Signal Transitions ───────────────────────────────────────────────────────

@router.get("/api/signal-transitions/{ticker}")
def get_signal_transitions(
    ticker: str,
    days: int = Query(90, ge=7, le=730),
    sb=Depends(get_user_supabase),
):
    """Signal transition history for a specific ticker. Public endpoint."""
    res = (
        sb.table("signal_transitions")
        .select("transition_date, field, from_value, to_value, score_total_at, price_at")
        .eq("ticker", ticker.upper())
        .gte("transition_date", f"(NOW() - INTERVAL '{days} days')::date")
        .order("transition_date", desc=True)
        .execute()
    )
    return res.data or []
