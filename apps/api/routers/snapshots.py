"""Portfolio snapshots — daily value tracking for period returns."""
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from apps.api.dependencies import get_user_supabase as get_supabase
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import PeriodReturn, PortfolioHistoryOut, SnapshotOut

router = APIRouter(prefix="/api/portfolio", tags=["snapshots"])


@router.post("/snapshot", response_model=SnapshotOut, status_code=201)
async def create_snapshot(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    """Create a snapshot of today's portfolio value for the current user."""
    # Fetch portfolio + holdings
    port = (
        sb.table("portfolios").select("id").eq("user_id", user.id)
        .limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    holdings_res = (
        sb.table("holdings").select("*")
        .eq("portfolio_id", portfolio_id).execute()
    )
    holdings = holdings_res.data or []
    if not holdings:
        return await _build_empty_snapshot(user, sb)

    tickers = [h["ticker"] for h in holdings]
    scan_res = (
        sb.table("scan_results")
        .select("ticker, price")
        .in_("ticker", tickers).execute()
    )
    scan_map = {r["ticker"]: r.get("price") for r in (scan_res.data or [])}

    total_value = 0.0
    total_cost = 0.0
    has_cost = False
    for h in holdings:
        price = scan_map.get(h["ticker"])
        if price is not None:
            total_value += float(price) * float(h["shares"])
        if h.get("cost_basis") is not None:
            total_cost += float(h["cost_basis"]) * float(h["shares"])
            has_cost = True

    today_str = date.today().isoformat()

    res = sb.table("portfolio_snapshots").upsert({
        "user_id": user.id,
        "date": today_str,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2) if has_cost else None,
    }, on_conflict="user_id,date").execute()

    row = res.data[0] if res.data else {}
    return SnapshotOut(
        id=row.get("id", ""),
        user_id=row.get("user_id", user.id),
        date=row.get("date", today_str),
        total_value=float(row.get("total_value", total_value)),
        total_cost=float(row["total_cost"]) if row.get("total_cost") else None,
        created_at=str(row.get("created_at", "")),
    )


async def _build_empty_snapshot(user: User, sb) -> SnapshotOut:
    """Build a snapshot with zero value when user has no holdings."""
    today_str = date.today().isoformat()
    res = sb.table("portfolio_snapshots").upsert({
        "user_id": user.id,
        "date": today_str,
        "total_value": 0,
        "total_cost": None,
    }, on_conflict="user_id,date").execute()
    row = res.data[0] if res.data else {}
    return SnapshotOut(
        id=row.get("id", ""),
        user_id=row.get("user_id", user.id),
        date=row.get("date", today_str),
        total_value=0,
        total_cost=None,
        created_at=str(row.get("created_at", "")),
    )


@router.get("/history", response_model=PortfolioHistoryOut)
async def get_portfolio_history(
    periods: str = Query("1M,3M,6M,12M", description="Comma-separated period labels"),
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    """Return portfolio return % for each requested period based on snapshots."""
    period_labels = [p.strip() for p in periods.split(",") if p.strip()]
    period_map = _period_labels_to_days(period_labels)
    if not period_map:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Inga giltiga perioder angivna")

    # Fetch snapshots for this user, newest first
    res = (
        sb.table("portfolio_snapshots")
        .select("date, total_value, total_cost")
        .eq("user_id", user.id)
        .order("date", desc=True)
        .execute()
    )
    rows = res.data or []
    if not rows or len(rows) < 2:
        return PortfolioHistoryOut(
            periods={label: PeriodReturn(pct=None, positive=None) for label in period_labels}
        )

    # Build date->value lookup
    snapshots = {}
    for r in rows:
        d = r["date"] if isinstance(r["date"], str) else r["date"].isoformat()
        snapshots[d] = float(r["total_value"])

    today = date.today()
    result: dict[str, PeriodReturn] = {}

    for label, days_back in period_map.items():
        target_date = (today - timedelta(days=days_back)).isoformat()
        pct = _calc_return(snapshots, target_date)
        if pct is not None:
            result[label] = PeriodReturn(pct=round(pct, 2), positive=pct > 0)
        else:
            result[label] = PeriodReturn(pct=None, positive=None)

    return PortfolioHistoryOut(periods=result)


def _period_labels_to_days(labels: list[str]) -> dict[str, int]:
    """Convert period labels like '1M' to number of days."""
    mapping = {}
    for label in labels:
        upper = label.upper().strip()
        if upper.endswith("M") and upper[:-1].isdigit():
            months = int(upper[:-1])
            mapping[label] = months * 30
        elif upper.endswith("Y") and upper[:-1].isdigit():
            years = int(upper[:-1])
            mapping[label] = years * 365
    return mapping


def _calc_return(snapshots: dict[str, float], target_date: str) -> float | None:
    """
    Calculate return from target_date to the most recent snapshot.
    Finds the snapshot closest to (but not after) target_date.
    """
    if not snapshots:
        return None

    # Most recent date (today or latest snapshot)
    latest_date = max(snapshots.keys())
    latest_value = snapshots[latest_date]

    if latest_value == 0:
        return None

    # Find closest snapshot <= target_date
    sorted_dates = sorted(snapshots.keys())
    past_value = None
    for d in sorted_dates:
        if d <= target_date:
            past_value = snapshots[d]
        else:
            break

    if past_value is None or past_value == 0:
        return None

    return ((latest_value - past_value) / past_value) * 100
