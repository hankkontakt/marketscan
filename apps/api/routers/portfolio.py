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
from apps.api.core.avanza_import import (
    parse_avanza_csv, build_preview,
    parse_positioner_csv, parse_inkopskurser_csv, get_buy_date,
)

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
    current_price: float | None = None   # derived from marknadsvarde / shares
    marknadsvarde: float | None = None   # total market value at export time
    mapped: bool = False
    purchase_date: str | None = None   # YYYY-MM-DD from inkopskurser
    isin: str | None = None
    av_typ: str | None = None          # "STOCK" | "FUND" | ""


class ImportPreviewIn(BaseModel):
    rows: list[dict]


class ImportPreviewOut(BaseModel):
    rows: list[ImportPreviewItem]
    mapped_count: int
    unmapped_count: int
    total: int


class ImportConfirmIn(BaseModel):
    rows: list[ImportPreviewItem]


# New endpoint input: raw CSV text (positioner + optional inkopskurser)
class AvanzaImportIn(BaseModel):
    positioner_csv: str
    inkopskurser_csv: str | None = None


@router.post("/import/preview", response_model=ImportPreviewOut)
async def import_preview(rows: ImportPreviewIn):
    """Preview Avanza CSV import with ticker mapping.
    Accepts parsed rows (sent from frontend after client-side CSV parse)."""
    preview = build_preview(rows.rows)  # rows.rows is already list[dict]
    mapped = [r for r in preview if r["mapped"]]
    unmapped = [r for r in preview if not r["mapped"]]

    return ImportPreviewOut(
        rows=[ImportPreviewItem(**r) for r in preview],
        mapped_count=len(mapped),
        unmapped_count=len(unmapped),
        total=len(preview),
    )


@router.post("/import/avanza/preview", response_model=ImportPreviewOut)
async def import_avanza_preview(body: AvanzaImportIn):
    """
    Parse Avanza positioner + inkopskurser CSV and return an enriched import preview.

    positioner_csv:  raw text of the 'positioner_per_konto' or 'positioner_sammanstallda' file
    inkopskurser_csv: raw text of the 'inkopskurs' file (optional — used for purchase dates)
    """
    rows = parse_positioner_csv(body.positioner_csv)

    inkopskurser: dict = {}
    if body.inkopskurser_csv:
        inkopskurser = parse_inkopskurser_csv(body.inkopskurser_csv)

    preview: list[ImportPreviewItem] = []
    for row in rows:
        isin = row.get("isin") or ""
        shares = row.get("shares")
        purchase_date = None
        if isin and shares is not None:
            purchase_date = get_buy_date(isin, shares, inkopskurser)

        preview.append(ImportPreviewItem(
            name=row["name"],
            ticker=row["ticker"],
            shares=row["shares"],
            cost_basis=row["cost_basis"],
            current_price=row.get("current_price"),
            marknadsvarde=row.get("marknadsvarde"),
            mapped=row["mapped"],
            purchase_date=purchase_date,
            isin=isin or None,
            av_typ=row.get("av_typ"),
        ))

    mapped_count = sum(1 for r in preview if r.mapped)
    unmapped_count = len(preview) - mapped_count

    return ImportPreviewOut(
        rows=preview,
        mapped_count=mapped_count,
        unmapped_count=unmapped_count,
        total=len(preview),
    )


@router.post("/import/confirm", status_code=201)
async def import_confirm(
    body: ImportConfirmIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Confirm import: create holdings + optional buy transactions.
    Rows with av_typ='FUND' or no ticker are silently skipped.
    """
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    stocks_created = 0
    funds_created = 0

    for row in body.rows:
        if row.shares is None:
            continue

        # ── Funds: save to fund_holdings ──────────────────────────────────────
        if row.av_typ == "FUND":
            if not row.isin:
                continue
            try:
                fund_data: dict = {
                    "portfolio_id": portfolio_id,
                    "isin":          row.isin,
                    "name":          row.name,
                    "shares":        row.shares,
                    "cost_basis":    row.cost_basis,
                    "current_price": row.current_price,
                    "marknadsvarde": row.marknadsvarde,
                }
                if row.purchase_date:
                    fund_data["purchase_date"] = row.purchase_date
                sb.table("fund_holdings").insert(fund_data).execute()
                funds_created += 1
            except Exception as e:
                logger.debug("Could not save fund holding %s: %s", row.isin, e)
            continue

        # ── Stocks: save to holdings ───────────────────────────────────────────
        if not row.ticker:
            continue

        ticker = row.ticker.upper()

        # Queue out-of-universe tickers for next pipeline run
        try:
            exists = sb.table("scan_results").select("ticker").eq("ticker", ticker).limit(1).execute()
            if not exists.data:
                sb.table("user_ticker_requests").upsert({
                    "ticker": ticker,
                    "user_id": user.id,
                    "name": row.name,
                    "source": "import",
                }, on_conflict="ticker").execute()
        except Exception as e:
            logger.debug("Could not queue ticker request for %s: %s", ticker, e)

        # Insert the holding
        sb.table("holdings").insert({
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "shares": row.shares,
            "cost_basis": row.cost_basis,
        }).execute()

        # If purchase_date is known, also record a buy transaction so TWR works
        if row.purchase_date:
            try:
                tx_data: dict = {
                    "user_id": user.id,
                    "portfolio_id": portfolio_id,
                    "ticker": ticker,
                    "type": "buy",
                    "shares": row.shares,
                    "price": row.cost_basis,
                    "note": "Importerad från Avanza",
                    "traded_at": row.purchase_date,
                }
                if row.cost_basis is not None and row.shares is not None:
                    tx_data["amount"] = round(row.cost_basis * row.shares, 2)
                sb.table("transactions").insert(tx_data).execute()
            except Exception as e:
                logger.debug("Could not create import transaction for %s: %s", ticker, e)

        stocks_created += 1

    return {
        "created": stocks_created + funds_created,
        "stocks_created": stocks_created,
        "funds_created": funds_created,
        "total": len(body.rows),
    }


# ─── Fund Holdings ────────────────────────────────────────────────────────────


class FundHoldingOut(BaseModel):
    id: str
    isin: str
    name: str
    shares: float
    cost_basis: float | None = None
    current_price: float | None = None
    marknadsvarde: float | None = None
    purchase_date: str | None = None
    added_at: str | None = None
    # Derived
    return_pct: float | None = None
    current_value: float | None = None
    cost_value: float | None = None


@router.get("/funds", response_model=list[FundHoldingOut])
async def get_fund_holdings(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Return all fund holdings for the user's portfolio."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return []
    portfolio_id = port.data[0]["id"]

    res = sb.table("fund_holdings").select("*").eq("portfolio_id", portfolio_id).execute()
    funds = res.data or []

    out = []
    for f in funds:
        shares = float(f.get("shares") or 0)
        cost_basis = float(f["cost_basis"]) if f.get("cost_basis") is not None else None
        current_price = float(f["current_price"]) if f.get("current_price") is not None else None
        marknadsvarde = float(f["marknadsvarde"]) if f.get("marknadsvarde") is not None else None

        # Prefer stored marknadsvarde; otherwise calculate from current_price
        current_value = marknadsvarde if marknadsvarde else (current_price * shares if current_price else None)
        cost_value = cost_basis * shares if cost_basis else None

        return_pct: float | None = None
        if cost_basis and current_price and cost_basis > 0:
            return_pct = round((current_price - cost_basis) / cost_basis * 100, 2)

        out.append(FundHoldingOut(
            id=f["id"],
            isin=f["isin"],
            name=f["name"],
            shares=shares,
            cost_basis=cost_basis,
            current_price=current_price,
            marknadsvarde=marknadsvarde,
            purchase_date=f.get("purchase_date"),
            added_at=f.get("added_at"),
            return_pct=return_pct,
            current_value=round(current_value, 2) if current_value else None,
            cost_value=round(cost_value, 2) if cost_value else None,
        ))

    return out


@router.delete("/funds/{fund_id}", status_code=204)
async def remove_fund_holding(
    fund_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Remove a fund holding (ownership-verified via RLS)."""
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")
    portfolio_id = port.data[0]["id"]

    res = (
        sb.table("fund_holdings").delete()
        .eq("id", fund_id)
        .eq("portfolio_id", portfolio_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fondinnehavet hittades inte")
