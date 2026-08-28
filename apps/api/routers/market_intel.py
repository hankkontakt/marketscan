"""
market_intel.py — Market intelligence endpoints (read-only)
===========================================================

Exponerar data från backend_worker-skrivna tabeller (read-only, RLS public read):

  GET /api/market-intel/shorts/{ticker}      — senaste short_positions-raderna (30 d)
  GET /api/market-intel/qmj/rank             — top-50 QMJ-rank senaste scan_date
  GET /api/market-intel/clusters/{ticker}    — insider_cluster_signals-rad
  GET /api/market-intel/factor-metrics       — senaste 90 dagarna factor_metrics

Alla endpoints: anon-klient (get_supabase) — RLS tillåter public read på tabellerna
(migrationer 029/041/042/043). Endpoints VARABAR data, inga beslut.
"""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-intel", tags=["market-intel"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ShortPositionOut(BaseModel):
    scan_date: str
    total_short_pct: float | None = None
    is_new_discovery: bool = False
    delta_pp: float | None = None


class QmjRankOut(BaseModel):
    ticker: str
    alpha_rank: float | None = None
    quality_z: float | None = None
    momentum_z: float | None = None
    value_z: float | None = None
    payout_z: float | None = None
    insider_z: float | None = None
    warning_flags: list[str] = []
    as_of_date: str | None = None
    exclusion_reason: str | None = None


class InsiderClusterSignalOut(BaseModel):
    ticker: str
    cluster_score: float | None = None
    is_cluster: bool = False
    exec_buy_90d: bool = False
    unique_sellers_30d: int = 0
    total_sell_amount_30d: float | None = None
    updated_at: str | None = None


class FactorMetricOut(BaseModel):
    factor: str
    horizon_days: int
    computed_date: str
    n: int = 0
    rank_ic: float | None = None
    decile_spread: float | None = None
    decile_spread_net: float | None = None
    win_rate: float | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/shorts/{ticker}", response_model=list[ShortPositionOut])
def get_short_positions(ticker: str, sb=Depends(get_supabase)):
    """Senaste short_positions-raderna för ticker (senaste 30 dagar).

    Läser från short_positions (migration 041, skrivs av fi_short_positions.py).
    """
    t = ticker.upper().strip()
    from_date = (date.today() - timedelta(days=30)).isoformat()

    try:
        res = (
            sb.table("short_positions")
            .select("scan_date,total_short_pct,is_new_discovery,delta_pp")
            .eq("ticker", t)
            .gte("scan_date", from_date)
            .order("scan_date", desc=True)
            .execute()
        )
    except Exception as e:
        logger.warning("short_positions query failed for %s: %s", t, e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa short_positions: {e}",
        )

    rows = res.data or []
    return [
        ShortPositionOut(
            scan_date=r.get("scan_date", ""),
            total_short_pct=float(r["total_short_pct"]) if r.get("total_short_pct") is not None else None,
            is_new_discovery=bool(r.get("is_new_discovery", False)),
            delta_pp=float(r["delta_pp"]) if r.get("delta_pp") is not None else None,
        )
        for r in rows
    ]


@router.get("/qmj/rank", response_model=list[QmjRankOut])
def get_qmj_rank(sb=Depends(get_supabase)):
    """Top-50 QMJ-rank från senaste scan_date.

    alpha_rank NOT NULL, exclusion_reason IS NULL (hårda filter exkluderade),
    sorterade på alpha_rank DESC. Läser från qmj_scores (migration 043).
    """
    # 1. Senaste scan_date
    try:
        latest = (
            sb.table("qmj_scores")
            .select("scan_date")
            .order("scan_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning("qmj_scores latest scan_date query failed: %s", e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa qmj_scores: {e}",
        )

    if not (latest.data or []):
        return []

    scan_date = latest.data[0]["scan_date"]

    # 2. Top-50 för den scan_date
    try:
        res = (
            sb.table("qmj_scores")
            .select("ticker,alpha_rank,quality_z,momentum_z,value_z,payout_z,insider_z,warning_flags,as_of_date,exclusion_reason")
            .eq("scan_date", scan_date)
            .not_.is_("alpha_rank", "null")
            .is_("exclusion_reason", "null")
            .order("alpha_rank", desc=True)
            .limit(50)
            .execute()
        )
    except Exception as e:
        logger.warning("qmj_scores rank query failed: %s", e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa qmj_scores: {e}",
        )

    rows = res.data or []
    return [
        QmjRankOut(
            ticker=r["ticker"],
            alpha_rank=float(r["alpha_rank"]) if r.get("alpha_rank") is not None else None,
            quality_z=float(r["quality_z"]) if r.get("quality_z") is not None else None,
            momentum_z=float(r["momentum_z"]) if r.get("momentum_z") is not None else None,
            value_z=float(r["value_z"]) if r.get("value_z") is not None else None,
            payout_z=float(r["payout_z"]) if r.get("payout_z") is not None else None,
            insider_z=float(r["insider_z"]) if r.get("insider_z") is not None else None,
            warning_flags=r.get("warning_flags") or [],
            as_of_date=r.get("as_of_date"),
            exclusion_reason=r.get("exclusion_reason"),
        )
        for r in rows
    ]


@router.get("/qmj/{ticker}", response_model=QmjRankOut)
def get_qmj_ticker(ticker: str, sb=Depends(get_supabase)):
    """Senaste QMJ-raden för ticker (inkl. exclusion_reason — för badge-display).

    Supplement till /qmj/rank som filtrerar bort exkluderade rader.
    """
    t = ticker.upper().strip()

    try:
        res = (
            sb.table("qmj_scores")
            .select("ticker,alpha_rank,quality_z,momentum_z,value_z,payout_z,insider_z,warning_flags,as_of_date,exclusion_reason")
            .eq("ticker", t)
            .order("scan_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning("qmj_scores query failed for %s: %s", t, e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa qmj_scores: {e}",
        )

    rows = res.data or []
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ingen QMJ-rad för {t}")

    r = rows[0]
    return QmjRankOut(
        ticker=t,
        alpha_rank=float(r["alpha_rank"]) if r.get("alpha_rank") is not None else None,
        quality_z=float(r["quality_z"]) if r.get("quality_z") is not None else None,
        momentum_z=float(r["momentum_z"]) if r.get("momentum_z") is not None else None,
        value_z=float(r["value_z"]) if r.get("value_z") is not None else None,
        payout_z=float(r["payout_z"]) if r.get("payout_z") is not None else None,
        insider_z=float(r["insider_z"]) if r.get("insider_z") is not None else None,
        warning_flags=r.get("warning_flags") or [],
        as_of_date=r.get("as_of_date"),
        exclusion_reason=r.get("exclusion_reason"),
    )


@router.get("/clusters/{ticker}", response_model=InsiderClusterSignalOut)
def get_cluster_signal(ticker: str, sb=Depends(get_supabase)):
    """insider_cluster_signals-raden för ticker.

    Läser från insider_cluster_signals (migration 029 + 044, skrivs av
    insider_cluster.py). 404 om ticker saknar signal.
    """
    t = ticker.upper().strip()

    try:
        res = (
            sb.table("insider_cluster_signals")
            .select("cluster_score,is_cluster,exec_buy_90d,unique_sellers_30d,total_sell_amount_30d,updated_at")
            .eq("ticker", t)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning("insider_cluster_signals query failed for %s: %s", t, e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa insider_cluster_signals: {e}",
        )

    rows = res.data or []
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Inga klustersignaler för {t}")

    r = rows[0]
    return InsiderClusterSignalOut(
        ticker=t,
        cluster_score=float(r["cluster_score"]) if r.get("cluster_score") is not None else None,
        is_cluster=bool(r.get("is_cluster", False)),
        exec_buy_90d=bool(r.get("exec_buy_90d", False)),
        unique_sellers_30d=int(r.get("unique_sellers_30d", 0)),
        total_sell_amount_30d=float(r["total_sell_amount_30d"]) if r.get("total_sell_amount_30d") is not None else None,
        updated_at=r.get("updated_at"),
    )


@router.get("/factor-metrics", response_model=list[FactorMetricOut])
def get_factor_metrics(sb=Depends(get_supabase)):
    """Senaste 90 dagarna av factor_metrics, sorterade på computed_date DESC.

    Läser från factor_metrics (migration 042, skrivs av signal_analytics.py).
    """
    from_date = (date.today() - timedelta(days=90)).isoformat()

    try:
        res = (
            sb.table("factor_metrics")
            .select("factor,horizon_days,computed_date,n,rank_ic,decile_spread,decile_spread_net,win_rate")
            .gte("computed_date", from_date)
            .order("computed_date", desc=True)
            .execute()
        )
    except Exception as e:
        logger.warning("factor_metrics query failed: %s", e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Kunde inte läsa factor_metrics: {e}",
        )

    rows = res.data or []
    return [
        FactorMetricOut(
            factor=r["factor"],
            horizon_days=int(r.get("horizon_days", 0)),
            computed_date=r.get("computed_date", ""),
            n=int(r.get("n", 0)),
            rank_ic=float(r["rank_ic"]) if r.get("rank_ic") is not None else None,
            decile_spread=float(r["decile_spread"]) if r.get("decile_spread") is not None else None,
            decile_spread_net=float(r["decile_spread_net"]) if r.get("decile_spread_net") is not None else None,
            win_rate=float(r["win_rate"]) if r.get("win_rate") is not None else None,
        )
        for r in rows
    ]


# ─── Radar: signaler samlade per bolag (kandidatradarn) ────────────────────────

class RadarEventOut(BaseModel):
    headline: str
    bearing: str | None = None
    confidence: float | None = None
    published_at: str | None = None
    message_url: str | None = None


class RadarItemOut(BaseModel):
    ticker: str
    name: str | None = None
    stratum: str | None = None
    alpha_rank: float | None = None
    quality_z: float | None = None
    momentum_z: float | None = None
    value_z: float | None = None
    payout_z: float | None = None
    insider_z: float | None = None
    exclusion_reason: str | None = None
    short_pct: float | None = None
    new_disclosure: bool = False
    cluster_score: float | None = None
    sellers_30d: int = 0
    news_48h: int = 0
    mention_surge: float | None = None
    top_events: list[RadarEventOut] = []
    warnings: list[str] = []


class RadarResponse(BaseModel):
    total: int
    items: list[RadarItemOut]


RADAR_THEMES = {"ipo", "order", "vinstvarning", "ledning", "regulatorik",
                "sector-ai", "sector-forsvar"}


@router.get("/radar", response_model=RadarResponse)
def get_radar(theme: str | None = None, sort: str = "activity", limit: int = 40,
              sb=Depends(get_supabase)):
    """Kandidatradarn — alla signaler samlade per bolag.

    Sortering: 'activity' (nyheter 48h + surge) eller 'rank' (alpha_rank).
    Läsar qmj_scores (senaste scan) + shorts + insiderkluster + nyheter 48h.
    Visar data, inga beslut (ärlighetstexten lever i UI:t).
    """
    import datetime as _dt

    if sort not in ("activity", "rank"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "sort måste vara activity|rank")
    if theme and theme not in RADAR_THEMES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"okänt tema: {theme}")

    try:
        res_scan = (
            sb.table("qmj_scores")
            .select("scan_date")
            .order("scan_date", desc=True)
            .limit(1)
            .execute()
        )
        scan_dates = res_scan.data or []
        scan_date = scan_dates[0]["scan_date"] if scan_dates else None

        qmj = {}
        if scan_date:
            res = (
                sb.table("qmj_scores")
                .select("ticker,stratum,alpha_rank,quality_z,momentum_z,value_z,"
                        "payout_z,insider_z,exclusion_reason")
                .eq("scan_date", scan_date)
                .execute()
            )
            qmj = {r["ticker"]: r for r in (res.data or [])}

        since = (_dt.datetime.utcnow() - timedelta(hours=48)).isoformat()
        news_query = (
            sb.table("news_events")
            .select("ticker,headline,bearing,confidence,published_at,message_url,"
                    "source_category,mention_surge")
            .gte("published_at", since)
            .not_.is_("ticker", "null")
            .limit(400)
        )
        if theme:
            news_query = news_query.eq("source_category", theme)
        res_news = news_query.execute()
        news_rows = res_news.data or []

        res_shorts = (
            sb.table("short_positions")
            .select("ticker,total_short_pct,is_new_discovery,scan_date")
            .gte("scan_date", (date.today() - timedelta(days=7)).isoformat())
            .execute()
        )
        shorts: dict[str, dict] = {}
        for r in (res_shorts.data or []):
            t = r.get("ticker")
            if not t:
                continue
            sd = str(r.get("scan_date") or "")
            if t not in shorts or sd > str(shorts[t].get("scan_date") or ""):
                shorts[t] = r

        res_clusters = (
            sb.table("insider_cluster_signals")
            .select("ticker,cluster_score,unique_sellers_30d")
            .execute()
        )
        clusters = {r["ticker"]: r for r in (res_clusters.data or [])}

        res_names = (
            sb.table("universe_registry")
            .select("ticker,name")
            .eq("status", "listed")
            .execute()
        )
        names = {r["ticker"]: r["name"] for r in (res_names.data or [])}
    except Exception as e:
        logger.warning("radar query failed: %s", e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"Kunde inte läsa radardata: {e}")

    news_by_ticker: dict[str, dict] = {}
    for r in news_rows:
        t = r.get("ticker")
        if not t:
            continue
        bucket = news_by_ticker.setdefault(t, {"count": 0, "surge": None, "events": []})
        bucket["count"] += 1
        if r.get("mention_surge") and (bucket["surge"] is None
                                       or r["mention_surge"] > bucket["surge"]):
            bucket["surge"] = r["mention_surge"]
        if len(bucket["events"]) < 3:
            bucket["events"].append({
                "headline": r.get("headline", ""),
                "bearing": r.get("bearing"),
                "confidence": float(r["confidence"]) if r.get("confidence") is not None else None,
                "published_at": r.get("published_at"),
                "message_url": r.get("message_url"),
            })

    items = []
    for t, row in qmj.items():
        s = shorts.get(t, {})
        c = clusters.get(t, {})
        nb = news_by_ticker.get(t, {"count": 0, "surge": None, "events": []})
        warnings = []
        if row.get("exclusion_reason"):
            warnings.append(str(row["exclusion_reason"]))
        short_pct = float(s["total_short_pct"]) if s.get("total_short_pct") is not None else None
        if short_pct is not None and short_pct >= 8:
            warnings.append("blankning")
        elif s.get("is_new_discovery"):
            warnings.append("ny blankning")
        if int(c.get("unique_sellers_30d") or 0) >= 3:
            warnings.append("säljkluster")

        items.append(RadarItemOut(
            ticker=t,
            name=names.get(t),
            stratum=row.get("stratum"),
            alpha_rank=float(row["alpha_rank"]) if row.get("alpha_rank") is not None else None,
            quality_z=float(row["quality_z"]) if row.get("quality_z") is not None else None,
            momentum_z=float(row["momentum_z"]) if row.get("momentum_z") is not None else None,
            value_z=float(row["value_z"]) if row.get("value_z") is not None else None,
            payout_z=float(row["payout_z"]) if row.get("payout_z") is not None else None,
            insider_z=float(row["insider_z"]) if row.get("insider_z") is not None else None,
            exclusion_reason=row.get("exclusion_reason"),
            short_pct=short_pct,
            new_disclosure=bool(s.get("is_new_discovery", False)),
            cluster_score=float(c["cluster_score"]) if c.get("cluster_score") is not None else None,
            sellers_30d=int(c.get("unique_sellers_30d") or 0),
            news_48h=int(nb["count"]),
            mention_surge=float(nb["surge"]) if nb.get("surge") is not None else None,
            top_events=[RadarEventOut(**e) for e in nb["events"]],
            warnings=warnings,
        ))

    if sort == "rank":
        items.sort(key=lambda i: (i.alpha_rank is not None,
                                  i.alpha_rank if i.alpha_rank is not None else -1),
                   reverse=True)
    else:
        items.sort(key=lambda i: (i.news_48h, i.mention_surge or 0), reverse=True)

    items = items[: max(1, min(limit, 100))]
    return RadarResponse(total=len(items), items=items)