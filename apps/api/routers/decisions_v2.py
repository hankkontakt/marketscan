"""
Decision API v2 Router (Phase 6)
Single canonical server contract for Screener, Stock Page, Compare, Watchlist and Portfolio.
"""
from typing import Optional, List
import logging
from datetime import datetime, date, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from apps.api.core.feature_flags import is_feature_enabled
from apps.api.schemas.decision_v2 import (
    DecisionRowV2,
    ScreenerResponseV2,
    StockDecisionV2,
    PriceQuote,
    MasterRankDetails,
    SetupDetails,
    RiskDetails,
    DataGradeDetails,
)
from apps.api.dependencies import get_supabase
from backend_worker.security_master.models import SecurityState
from backend_worker.security_master.backfill import build_benchmark_security_master
from backend_worker.ranking_v2.master_rank_v2 import compute_master_rank_v2, ThesisBand
from backend_worker.setup.setup_engine import compute_setup_state, SETUP_UI_COPY, SetupState
from backend_worker.risk.risk_engine import compute_risk_state, RiskState, DataGrade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/decisions", tags=["decisions-v2"])

# Cached resolver
_SECURITY_RESOLVER = build_benchmark_security_master()

def _build_decision_row_from_dict(row: dict, snapshot_id: str) -> DecisionRowV2:
    ticker = str(row.get("ticker", "")).upper()
    name = row.get("name", ticker)
    segment = row.get("segment", "unknown")
    sector = row.get("sector")
    country = row.get("country", "SE")
    currency = row.get("currency", "SEK" if country == "SE" else "USD")

    price_val = float(row.get("price") or 0.0)
    change_val = float(row.get("change_pct") or 0.0)

    # Tradability check
    is_tradable, sec_state, expl = _SECURITY_RESOLVER.enforce_tradability_gate(ticker)

    # 1. MasterRank v2
    mr_res = compute_master_rank_v2(row, segment=segment, is_tradable=is_tradable)

    # 2. SetupState
    setup_res = compute_setup_state(
        price=price_val,
        ma20=float(row.get("ma20")) if row.get("ma20") else None,
        ma50=float(row.get("ma50")) if row.get("ma50") else None,
        ma200=float(row.get("ma200")) if row.get("ma200") else None,
        atr=float(row.get("atr")) if row.get("atr") else None,
        rsi_14=float(row.get("rsi_14") or row.get("rsi") or 50.0),
        days_to_earnings=int(row.get("days_to_earnings")) if row.get("days_to_earnings") is not None else None
    )

    # 3. RiskState & DataGrade
    risk_res = compute_risk_state(
        liquidity_grade=row.get("liquidity_grade", "B"),
        debt_to_equity=float(row.get("debt_to_equity")) if row.get("debt_to_equity") is not None else None,
        volatility_20d=float(row.get("vol_20d")) if row.get("vol_20d") is not None else None,
        days_to_earnings=int(row.get("days_to_earnings")) if row.get("days_to_earnings") is not None else None,
        weighted_coverage=mr_res.weighted_coverage,
        is_tradable=is_tradable
    )

    listing = _SECURITY_RESOLVER.resolve_listing_by_ticker(ticker)
    listing_id = listing.listing_id if listing else str(uuid.uuid4())

    now_str = datetime.now(timezone.utc).isoformat()

    return DecisionRowV2(
        decision_snapshot_id=snapshot_id,
        listing_id=listing_id,
        ticker=ticker,
        name=name,
        segment=segment,
        sector=sector,
        country=country,
        price=PriceQuote(
            value=price_val,
            currency=currency,
            change_pct=change_val,
            as_of=now_str
        ),
        master_rank=MasterRankDetails(
            score=mr_res.master_rank,
            band=mr_res.thesis_band,
            segment_percentile=float(row.get("master_rank_pctl") or row.get("pctl") or 50.0),
            weighted_coverage=mr_res.weighted_coverage,
            model_version=mr_res.model_version
        ),
        setup=SetupDetails(
            state=setup_res.state,
            ui_label_sv=setup_res.ui_label_sv,
            reason_codes=setup_res.reason_codes
        ),
        risk=RiskDetails(
            state=risk_res.risk_state,
            dominant_risk=risk_res.dominant_risk,
            liquidity_grade=risk_res.liquidity_grade,
            risk_flags=risk_res.risk_flags
        ),
        data_grade=DataGradeDetails(
            grade=risk_res.data_grade,
            weighted_coverage=mr_res.weighted_coverage,
            critical_warnings=mr_res.warnings + risk_res.critical_warnings
        ),
        positive_drivers=mr_res.positive_drivers,
        negative_drivers=mr_res.negative_drivers
    )


@router.get("/screener", response_model=ScreenerResponseV2)
async def get_screener_decisions(
    segment: Optional[str] = Query(None),
    thesis_band: Optional[str] = Query(None),
    setup_state: Optional[str] = Query(None),
    risk_state: Optional[str] = Query(None),
    data_grade: Optional[str] = Query(None),
    min_coverage: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    sb=Depends(get_supabase)
):
    """
    Canonical decision endpoint for Screener table.
    Returns versioned DecisionRowV2 items without client-side joins.
    """
    snapshot_id = f"snap_{date.today().isoformat()}"
    rows_data = []

    # Query scan_results if Supabase available
    if sb is not None:
        try:
            q = sb.table("scan_results").select("*")
            if segment:
                q = q.eq("segment", segment)
            res = q.limit(limit).execute()
            rows_data = res.data or []
        except Exception as exc:
            logger.debug("Database lookup skipped in demo/mock mode: %s", exc)

    if not rows_data:
        # Fallback to seeded benchmark cohort for local/test runs
        import json
        from pathlib import Path
        fixture_p = Path("data/fixtures/benchmark_cohort_v1.json")
        if fixture_p.exists():
            cohort_data = json.loads(fixture_p.read_text(encoding="utf-8")).get("cohort", [])
            rows_data = [
                {
                    "ticker": item["ticker"],
                    "name": item["name"],
                    "segment": "small_cap" if ".ST" in item["ticker"] or ".HE" in item["ticker"] else "large_cap",
                    "price": 100.0,
                    "change_pct": 0.015,
                    "roe": 0.25,
                    "operating_margin": 0.20,
                    "pe_trailing": 20.0,
                    "score_momentum": 75.0
                }
                for item in cohort_data
            ]

    decision_rows = []
    for r in rows_data:
        row_v2 = _build_decision_row_from_dict(r, snapshot_id)

        # Apply filters
        if thesis_band and row_v2.master_rank.band.value != thesis_band:
            continue
        if setup_state and row_v2.setup.state.value != setup_state:
            continue
        if risk_state and row_v2.risk.state.value != risk_state:
            continue
        if data_grade and row_v2.data_grade.grade.value != data_grade:
            continue
        if min_coverage and row_v2.data_grade.weighted_coverage < min_coverage:
            continue

        decision_rows.append(row_v2)

    return ScreenerResponseV2(
        total_count=len(decision_rows),
        rows=decision_rows[:limit],
        as_of=datetime.now(timezone.utc).isoformat(),
        snapshot_id=snapshot_id,
        active_filters={
            "segment": segment,
            "thesis_band": thesis_band,
            "setup_state": setup_state,
            "risk_state": risk_state,
            "data_grade": data_grade,
        }
    )


@router.get("/stock/{ticker}", response_model=StockDecisionV2)
async def get_stock_decision(ticker: str, sb=Depends(get_supabase)):
    """
    Canonical decision endpoint for Stock Page.
    """
    ticker_clean = ticker.strip().upper()
    snapshot_id = f"snap_{date.today().isoformat()}"
    stock_dict = {}

    if sb is not None:
        try:
            res = sb.table("scan_results").select("*").eq("ticker", ticker_clean).limit(1).execute()
            if res.data and len(res.data) > 0:
                stock_dict = res.data[0]
        except Exception as exc:
            logger.debug("Database single stock lookup skipped: %s", exc)

    if not stock_dict:
        stock_dict = {
            "ticker": ticker_clean,
            "name": ticker_clean,
            "segment": "large_cap",
            "price": 100.0,
            "change_pct": 0.0,
            "roe": 0.20,
            "pe_trailing": 18.0,
            "score_momentum": 60.0
        }

    row_v2 = _build_decision_row_from_dict(stock_dict, snapshot_id)
    is_tradable, _, _ = _SECURITY_RESOLVER.enforce_tradability_gate(ticker_clean)
    mr_res = compute_master_rank_v2(stock_dict, segment=row_v2.segment, is_tradable=is_tradable)

    return StockDecisionV2(
        decision_snapshot_id=snapshot_id,
        listing_id=row_v2.listing_id,
        ticker=row_v2.ticker,
        name=row_v2.name,
        segment=row_v2.segment,
        sector=row_v2.sector,
        country=row_v2.country,
        price=row_v2.price,
        master_rank=row_v2.master_rank,
        setup=row_v2.setup,
        risk=row_v2.risk,
        data_grade=row_v2.data_grade,
        positive_drivers=row_v2.positive_drivers,
        negative_drivers=row_v2.negative_drivers,
        factor_scores=mr_res.factor_scores,
        factor_reliabilities=mr_res.factor_reliabilities,
        warnings=mr_res.warnings
    )
