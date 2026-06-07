"""Portfolio & holdings CRUD — fully RLS-protected via Supabase."""
import json
import logging
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.dependencies import get_user_supabase, get_supabase_admin
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import HoldingIn, HoldingOut, PortfolioOut
from apps.api.core.enrichment import enrich_with_scan_data
from apps.api.core.avanza_import import parse_avanza_csv, build_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ─── Portfolio ──────────────────────────────────────────────────────────────

@router.get("", response_model=PortfolioOut)
async def get_portfolio(user: User = Depends(get_current_user), sb=Depends(get_user_supabase)):
    port = (
        sb.table("portfolios").select("*").eq("user_id", user.id)
        .order("created_at").limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio = port.data[0]

    holdings_res = (
        sb.table("holdings").select("*")
        .eq("portfolio_id", portfolio["id"]).execute()
    )
    holdings = holdings_res.data or []

    enrich_with_scan_data(holdings, sb)

    portfolio["holdings"] = holdings
    return portfolio


@router.post("/holdings", response_model=HoldingOut, status_code=201)
async def add_holding(
    body: HoldingIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
    sb_admin=Depends(get_supabase_admin),
):
    port = (
        sb.table("portfolios").select("id").eq("user_id", user.id)
        .limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    ticker = body.ticker.upper()

    # If ticker not in universe, queue it for the next pipeline run.
    # Uses admin client because regular users lack the UPDATE policy on
    # user_ticker_requests (needed for upsert on conflict).
    try:
        exists = (
            sb.table("scan_results")
            .select("ticker")
            .eq("ticker", ticker)
            .limit(1)
            .execute()
        )
        if not exists.data:
            sb_admin.table("user_ticker_requests").upsert(
                {
                    "ticker": ticker,
                    "user_id": user.id,
                    "name": body.name,
                    "source": "portfolio",
                    "added_to_universe": False,
                },
                on_conflict="ticker",
            ).execute()
            logger.info("Queued out-of-universe ticker %s (portfolio) for next pipeline run", ticker)
    except Exception as e:
        # Non-fatal — holding is still saved
        logger.debug("Could not queue ticker request for %s: %s", ticker, e)

    res = sb.table("holdings").insert({
        "portfolio_id": portfolio_id,
        "ticker": ticker,
        "shares": body.shares,
        "cost_basis": body.cost_basis,
    }).execute()
    return res.data[0]


@router.delete("/holdings/{holding_id}", status_code=204)
async def remove_holding(
    holding_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    # P0-2: Verify ownership — delete only if holding belongs to user's own portfolio
    port = (
        sb.table("portfolios").select("id").eq("user_id", user.id)
        .limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    res = (
        sb.table("holdings").delete()
        .eq("id", holding_id)
        .eq("portfolio_id", portfolio_id)  # ownership check
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Innehavet hittades inte")


# ─── Portfolio risk ────────────────────────────────────────────────────────────


class SectorAllocation(BaseModel):
    sector: str
    value: float
    pct: float


class PortfolioRiskOut(BaseModel):
    tickers: list[str]
    sector_allocation: list[SectorAllocation]
    concentration_pct: float
    total_value: float
    count: int
    score_avg: float | None = None


@router.get("/risk", response_model=PortfolioRiskOut)
async def get_portfolio_risk(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Portfolio risk metrics: sector allocation, concentration, avg score."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return PortfolioRiskOut(tickers=[], sector_allocation=[], concentration_pct=0, total_value=0, count=0, score_avg=None)

    holdings = sb.table("holdings").select("*").eq("portfolio_id", port.data[0]["id"]).execute()
    items = holdings.data or []
    if not items:
        return PortfolioRiskOut(tickers=[], sector_allocation=[], concentration_pct=0, total_value=0, count=0, score_avg=None)

    tickers = [h["ticker"] for h in items]
    scan = sb.table("scan_results").select("ticker,price,sector,score_total").in_("ticker", tickers).execute()
    scan_map = {r["ticker"]: r for r in (scan.data or [])}

    total_value = 0.0
    sector_values: dict[str, float] = Counter()
    scores = []
    for h in items:
        info = scan_map.get(h["ticker"])
        price = info.get("price") if info else h.get("cost_basis")
        if price is None:
            continue
        val = float(price) * float(h["shares"])
        total_value += val
        sector = (info or {}).get("sector") or "Övrigt"
        sector_values[sector] += val
        score = (info or {}).get("score_total")
        if score is not None:
            scores.append(float(score))

    allocation = [
        SectorAllocation(sector=s, value=round(v, 2), pct=round(v / total_value * 100, 1))
        for s, v in sector_values.most_common()
    ]

    concentration_pct = round((sector_values.most_common(1)[0][1] / total_value * 100), 1) if sector_values else 0
    score_avg = round(sum(scores) / len(scores), 1) if scores else None

    return PortfolioRiskOut(
        tickers=tickers,
        sector_allocation=allocation,
        concentration_pct=concentration_pct,
        total_value=round(total_value, 2),
        count=len(items),
        score_avg=score_avg,
    )


# ─── Diversification Health (F3) ───────────────────────────────────────────────


class DiversificationOut(BaseModel):
    score: float
    max_holding_pct: float
    num_holdings: int
    sector_allocation: list[SectorAllocation]
    top_holding: str | None = None
    message: str


@router.get("/diversification", response_model=DiversificationOut)
async def get_diversification(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Portfolio diversification health score and sector breakdown."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return DiversificationOut(score=0, max_holding_pct=0, num_holdings=0, sector_allocation=[], message="Ingen portfölj hittad — lägg till innehav för att se diversifiering")

    holdings = sb.table("holdings").select("*").eq("portfolio_id", port.data[0]["id"]).execute()
    items = holdings.data or []
    if not items:
        return DiversificationOut(score=0, max_holding_pct=0, num_holdings=0, sector_allocation=[], message="Inga innehav — lägg till aktier för att se diversifiering")

    tickers = [h["ticker"] for h in items]
    scan = sb.table("scan_results").select("ticker,price,sector,score_total").in_("ticker", tickers).execute()
    scan_map = {r["ticker"]: r for r in (scan.data or [])}

    total_value = 0.0
    holding_values: list[tuple[str, float]] = []
    sector_values: dict[str, float] = Counter()

    for h in items:
        info = scan_map.get(h["ticker"])
        price = info.get("price") if info else h.get("cost_basis")
        if price is None:
            continue
        val = float(price) * float(h["shares"])
        total_value += val
        holding_values.append((h["ticker"], val))
        sector = (info or {}).get("sector") or "Övrigt"
        sector_values[sector] += val

    if total_value == 0:
        return DiversificationOut(score=0, max_holding_pct=0, num_holdings=len(items), sector_allocation=[], message="Portföljvärdet är noll — kontrollera dina priser")

    # Max holding concentration
    holding_values.sort(key=lambda x: x[1], reverse=True)
    max_pct = round((holding_values[0][1] / total_value) * 100, 1) if holding_values else 0

    # Sector allocation
    allocation = [
        SectorAllocation(sector=s, value=round(v, 2), pct=round(v / total_value * 100, 1))
        for s, v in sector_values.most_common()
    ]

    # Score: 0-100
    # Factors: number of holdings (max 30), sector spread, max holding size
    n = len(items)
    holding_score = min(30, n * 6)  # 0-30 points, 5 holdings = 30
    sector_count = len(sector_values)
    sector_score = min(25, sector_count * 8)  # 0-25 points, 3+ sectors = 24
    concentration_penalty = max(0, 25 - (max_pct / 4)) if n > 1 else 0  # 0-25 penalty
    diversity_score = max_pct > 50 and n > 1 and 0 or 10  # 0 or 10
    score = min(100, round(holding_score + sector_score + concentration_penalty + diversity_score))

    # Human message
    if n == 1:
        msg = f"Endast ett innehav ({holding_values[0][0]}). Överväg att bredda portföljen för att minska risken."
    elif max_pct > 50:
        msg = f"Hög koncentration i {holding_values[0][0]} ({max_pct}% av portföljen). Överväg att balansera om."
    elif n < 5:
        msg = f"Ganska få innehav ({n} st). Fler aktier kan sprida risken."
    elif sector_count < 3:
        msg = f"Portföljen är koncentrerad till {sector_count} sektor(er). Överväg sektorspridning."
    else:
        msg = f"Hyfsad diversifiering över {sector_count} sektorer med {n} innehav."

    return DiversificationOut(
        score=score,
        max_holding_pct=max_pct,
        num_holdings=n,
        sector_allocation=allocation,
        top_holding=holding_values[0][0] if holding_values else None,
        message=msg,
    )


# ─── Avanza Import ────────────────────────────────────────────────────────────


class ImportPreviewItem(BaseModel):
    name: str
    ticker: str | None = None
    shares: float | None = None
    cost_basis: float | None = None
    current_price: float | None = None
    mapped: bool = False


class ImportPreviewIn(BaseModel):
    rows: list[dict]


class ImportConfirmIn(BaseModel):
    rows: list[ImportPreviewItem]


class ImportPreviewOut(BaseModel):
    rows: list[ImportPreviewItem]
    mapped_count: int
    unmapped_count: int
    total: int


class ImportConfirmIn(BaseModel):
    rows: list[ImportPreviewItem]


@router.post("/import/preview", response_model=ImportPreviewOut)
async def import_preview(rows: ImportPreviewIn):
    """Preview Avanza CSV import with ticker mapping.
    Accepts parsed rows (sent from frontend after client-side CSV parse)."""
    preview = build_preview([r.model_dump() for r in rows.rows])
    mapped = [r for r in preview if r["mapped"]]
    unmapped = [r for r in preview if not r["mapped"]]

    return ImportPreviewOut(
        rows=[ImportPreviewItem(**r) for r in preview],
        mapped_count=len(mapped),
        unmapped_count=len(unmapped),
        total=len(preview),
    )


@router.post("/import/confirm", status_code=201)
async def import_confirm(
    body: ImportConfirmIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Confirm import: create holdings and user_ticker_requests."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    created = 0
    for row in body.rows:
        if not row.ticker or row.shares is None:
            continue

        ticker = row.ticker.upper()

        # Create user_ticker_request if not in universe
        exists = sb.table("scan_results").select("ticker").eq("ticker", ticker).limit(1).execute()
        if not exists.data:
            sb.table("user_ticker_requests").upsert({
                "ticker": ticker,
                "user_id": user.id,
                "name": row.name,
                "source": "import",
            }, on_conflict="ticker").execute()

        sb.table("holdings").insert({
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "shares": row.shares,
            "cost_basis": row.cost_basis,
        }).execute()
        created += 1

    return {"created": created, "total": len(body.rows)}
