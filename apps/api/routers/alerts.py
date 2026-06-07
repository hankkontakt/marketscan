"""Price alerts — create, list, delete, and manual trigger."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_user_supabase, get_supabase_admin
from apps.api.core.security import get_current_user, require_admin, User
from apps.api.schemas.portfolio import PriceAlertIn, PriceAlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[PriceAlertOut])
async def get_alerts(user: User = Depends(get_current_user), sb=Depends(get_user_supabase)):
    res = sb.table("price_alerts").select("*").eq("user_id", user.id).eq("active", True).execute()
    return res.data or []


@router.post("", response_model=PriceAlertOut, status_code=201)
async def create_alert(
    body: PriceAlertIn, user: User = Depends(get_current_user), sb=Depends(get_user_supabase)
):
    res = sb.table("price_alerts").insert({
        "user_id": user.id,
        "ticker": body.ticker.upper(),
        "condition": body.condition,
        "target_price": body.target_price,
        "note": body.note,
    }).execute()
    return res.data[0]


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str, user: User = Depends(get_current_user), sb=Depends(get_user_supabase)
):
    # P0-2: Add user_id ownership check to prevent IDOR
    res = (
        sb.table("price_alerts").delete()
        .eq("id", alert_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Larmet hittades inte")


@router.get("/check")
async def manual_alert_check(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Manually trigger price alert check logic.
    Requires admin role. Uses service-role client to bypass RLS."""
    alerts_res = sb.table("price_alerts").select("*").eq("active", True).execute()
    alerts = alerts_res.data or []

    if not alerts:
        return {"checked": 0, "triggered": 0, "message": "Inga aktiva larm"}

    unique_tickers = list({a["ticker"] for a in alerts})

    # Fetch prices from scan_results
    scan_res = (
        sb.table("scan_results")
        .select("ticker, price")
        .in_("ticker", unique_tickers)
        .execute()
    )
    price_map: dict[str, float] = {}
    for row in scan_res.data or []:
        p = row.get("price")
        if p is not None:
            price_map[row["ticker"]] = float(p)

    checked = 0
    triggered = 0
    now = datetime.now(timezone.utc).isoformat()

    for alert in alerts:
        ticker = alert["ticker"]
        current_price = price_map.get(ticker)

        if current_price is None:
            continue

        condition = alert["condition"]
        target_price = float(alert["target_price"])

        is_triggered = False
        if condition == "above" and current_price >= target_price:
            is_triggered = True
        elif condition == "below" and current_price <= target_price:
            is_triggered = True

        checked += 1

        if is_triggered:
            triggered += 1
            sb.table("price_alerts").update({
                "active": False,
                "triggered_at": now,
            }).eq("id", alert["id"]).execute()

    return {
        "checked": checked,
        "triggered": triggered,
        "total_active": len(alerts),
    }
