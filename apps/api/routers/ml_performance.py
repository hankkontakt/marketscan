"""
ml_performance.py — Admin-only ML/AI prestanda-endpoints
=========================================================

Exponerar data för AI-prestanda-dashboarden (admin-only):

  GET /api/ml-performance/summary        — modell-metrics (IC, hit-rate, DSR)
  GET /api/ml-performance/outcomes       — prediktionsutfall (predicted vs actual)
  GET /api/ml-performance/deciles        — decil-spread analys
  GET /api/ml-performance/ic-trend       — IC-trend över tid
  GET /api/ml-performance/top-picks      — senaste topp-prediktioner + utfall

Alla endpoints: require_admin (service_role + JWT admin-roll).
"""

import logging
import math
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from apps.api.core.security import require_admin, User
from apps.api.dependencies import get_supabase_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml-performance", tags=["ml-performance"])


# ── Pydantic-schemas ─────────────────────────────────────────────────────────

class ModelSummaryOut(BaseModel):
    model_version:  str
    trained_at:     Optional[str]
    n_rows:         Optional[int]
    ic:             Optional[float]
    hit_rate:       Optional[float]
    decile_spread:  Optional[float]
    n_folds:        Optional[int]
    model_type:     Optional[str]
    n_features:     Optional[int]
    # Live tracking från prediction_outcomes
    outcomes_total:     int = 0
    outcomes_evaluated: int = 0
    live_ic:            Optional[float] = None
    live_hit_rate:      Optional[float] = None


class OutcomeRow(BaseModel):
    ticker:             str
    predicted_at:       str
    predicted_return:   Optional[float]
    ml_rank:            Optional[int]
    score_total:        Optional[float]
    price_at:           Optional[float]
    realized_return_30d: Optional[float]
    price_30d:          Optional[float]
    evaluated_at:       Optional[str]
    error:              Optional[float] = None  # realized - predicted (normaliserat)


class DecileRow(BaseModel):
    decile:      int
    avg_return:  float
    n_dates:     int
    label:       str


class IcPoint(BaseModel):
    month:  str   # "2026-01"
    ic:     float
    n:      int


class TopPickRow(BaseModel):
    ticker:             str
    predicted_at:       str
    ml_rank:            int
    predicted_return:   float
    realized_return_30d: Optional[float]
    outcome_status:     str  # "pending", "win", "loss", "evaluated"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_model_metrics(universe: str = "universe") -> dict:
    """Laddar metrics från ranker eller XGBoost (JSON-fil, inga pickle-imports)."""
    import os, json
    from pathlib import Path

    # Finn stock-scanner-fix-rooten via SCANNER_PATH env eller relativ sökväg
    scanner_root = Path(os.environ.get("SCANNER_PATH", "/app/stock-scanner-fix"))

    ranker_file = scanner_root / "models" / f"ml_ranker_{universe}_metrics.json"
    xgb_file    = scanner_root / "models" / f"ml_{universe}_metrics.json"

    for metrics_file in [ranker_file, xgb_file]:
        if metrics_file.exists():
            try:
                return json.loads(metrics_file.read_text())
            except Exception:
                continue
    return {}


def _spearman_ic(preds, actuals) -> float:
    """Snabb Spearman-korrelation utan scipy (rankar manuellt)."""
    if len(preds) < 3:
        return 0.0
    try:
        from scipy.stats import spearmanr
        ic, _ = spearmanr(preds, actuals)
        return float(ic) if not math.isnan(ic) else 0.0
    except ImportError:
        # Fallback: Pearson på rankade vektorer
        n = len(preds)
        rank_p = sorted(range(n), key=lambda i: preds[i])
        rank_a = sorted(range(n), key=lambda i: actuals[i])
        rp = [0.0] * n; ra = [0.0] * n
        for rank, idx in enumerate(rank_p): rp[idx] = rank
        for rank, idx in enumerate(rank_a): ra[idx] = rank
        mp = sum(rp) / n; ma = sum(ra) / n
        num = sum((rp[i]-mp)*(ra[i]-ma) for i in range(n))
        den = (sum((rp[i]-mp)**2 for i in range(n)) * sum((ra[i]-ma)**2 for i in range(n))) ** 0.5
        return num / den if den else 0.0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=ModelSummaryOut)
def get_ml_summary(
    universe: str = Query("universe"),
    _user: User = Depends(require_admin),
    sb = Depends(get_supabase_admin),
):
    """Modell-metrics + live tracking-statistik från prediction_outcomes."""
    metrics = _load_model_metrics(universe)
    tm = metrics.get("test_metrics", metrics)

    # Live IC från prediction_outcomes (utvärderade rader)
    live_ic = live_hit_rate = None
    outcomes_total = outcomes_evaluated = 0

    try:
        total_res = sb.table("prediction_outcomes").select(
            "id", count="exact"
        ).eq("model_version", "ranker_v1").execute()
        outcomes_total = total_res.count or 0

        eval_res = sb.table("prediction_outcomes").select(
            "predicted_return,realized_return_30d", count="exact"
        ).eq("model_version", "ranker_v1").not_.is_("evaluated_at", "null").limit(2000).execute()
        outcomes_evaluated = eval_res.count or 0

        rows = eval_res.data or []
        if len(rows) >= 10:
            preds   = [r["predicted_return"] for r in rows if r.get("predicted_return") is not None]
            actuals = [r["realized_return_30d"] for r in rows if r.get("realized_return_30d") is not None]
            n = min(len(preds), len(actuals))
            if n >= 10:
                live_ic = round(_spearman_ic(preds[:n], actuals[:n]), 4)
                # Hit-rate: predicted_return > median → actual > 0
                med = sorted(preds[:n])[n // 2]
                hits = sum(1 for p, a in zip(preds[:n], actuals[:n]) if (p > med) == (a > 0))
                live_hit_rate = round(hits / n, 4)
    except Exception as e:
        logger.debug("Live metrics query failed: %s", e)

    return ModelSummaryOut(
        model_version   = metrics.get("universe", universe),
        trained_at      = metrics.get("trained_at"),
        n_rows          = metrics.get("n_rows"),
        ic              = tm.get("ic") or tm.get("wf_avg_ic") or tm.get("cpcv_avg_ic"),
        hit_rate        = tm.get("hit_rate") or tm.get("wf_avg_hit_rate") or tm.get("cpcv_avg_hitrate"),
        decile_spread   = tm.get("wf_avg_spread"),
        n_folds         = tm.get("n_folds"),
        model_type      = tm.get("model_type", "xgboost_regressor"),
        n_features      = tm.get("n_features"),
        outcomes_total      = outcomes_total,
        outcomes_evaluated  = outcomes_evaluated,
        live_ic             = live_ic,
        live_hit_rate       = live_hit_rate,
    )


@router.get("/outcomes", response_model=list[OutcomeRow])
def get_outcomes(
    days: int = Query(90, ge=7, le=365),
    limit: int = Query(200, ge=10, le=1000),
    evaluated_only: bool = Query(False),
    _user: User = Depends(require_admin),
    sb = Depends(get_supabase_admin),
):
    """Senaste prediktionsutfall (predicted vs actual)."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    q = (
        sb.table("prediction_outcomes")
        .select("ticker,predicted_at,predicted_return,ml_rank,score_total,"
                "price_at,realized_return_30d,price_30d,evaluated_at")
        .gte("predicted_at", cutoff)
        .order("predicted_at", desc=True)
        .limit(limit)
    )
    if evaluated_only:
        q = q.not_.is_("evaluated_at", "null")

    res = q.execute()
    rows = []
    for r in (res.data or []):
        pred = r.get("predicted_return")
        actual = r.get("realized_return_30d")
        error = None
        if pred is not None and actual is not None:
            # Normaliserad felterm (actual - predicted, i avkastnings-skala)
            error = round(float(actual) - float(pred), 4)
        rows.append(OutcomeRow(
            ticker              = r["ticker"],
            predicted_at        = str(r["predicted_at"]),
            predicted_return    = r.get("predicted_return"),
            ml_rank             = r.get("ml_rank"),
            score_total         = r.get("score_total"),
            price_at            = r.get("price_at"),
            realized_return_30d = r.get("realized_return_30d"),
            price_30d           = r.get("price_30d"),
            evaluated_at        = str(r["evaluated_at"]) if r.get("evaluated_at") else None,
            error               = error,
        ))
    return rows


@router.get("/ic-trend", response_model=list[IcPoint])
def get_ic_trend(
    months: int = Query(12, ge=3, le=36),
    _user: User = Depends(require_admin),
    sb = Depends(get_supabase_admin),
):
    """IC-trend per månad (från utvärderade prediction_outcomes).

    Visar om modellen förbättras eller försämras över tid.
    """
    cutoff = (date.today() - timedelta(days=months * 31)).isoformat()
    res = sb.table("prediction_outcomes").select(
        "predicted_at,predicted_return,realized_return_30d"
    ).not_.is_("evaluated_at", "null").gte("predicted_at", cutoff).execute()

    rows = res.data or []
    if not rows:
        return []

    # Gruppera per månad
    from collections import defaultdict
    by_month: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.get("predicted_return") is None or r.get("realized_return_30d") is None:
            continue
        month = str(r["predicted_at"])[:7]  # "2026-01"
        by_month[month].append((r["predicted_return"], r["realized_return_30d"]))

    points = []
    for month in sorted(by_month.keys()):
        pairs = by_month[month]
        if len(pairs) < 5:
            continue
        preds, actuals = zip(*pairs)
        ic = _spearman_ic(list(preds), list(actuals))
        points.append(IcPoint(month=month, ic=round(ic, 4), n=len(pairs)))

    return points


@router.get("/deciles", response_model=list[DecileRow])
def get_decile_analysis(
    days: int = Query(90, ge=30, le=365),
    n_deciles: int = Query(5, ge=3, le=10),
    _user: User = Depends(require_admin),
    sb = Depends(get_supabase_admin),
):
    """Genomsnittlig avkastning per decil (topp- vs botten-prediktioner).

    Hög spread topp→botten = modellen separerar bra aktier från dåliga.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    res = sb.table("prediction_outcomes").select(
        "predicted_at,ml_rank,realized_return_30d"
    ).not_.is_("evaluated_at", "null").gte("predicted_at", cutoff).execute()

    rows = [r for r in (res.data or [])
            if r.get("ml_rank") is not None and r.get("realized_return_30d") is not None]

    if len(rows) < n_deciles * 2:
        return []

    # Sortera efter ml_rank (0 = sämst, 100 = bäst)
    ranks   = [float(r["ml_rank"]) for r in rows]
    returns = [float(r["realized_return_30d"]) for r in rows]

    # Dela in i N grupper baserat på ml_rank-percentil
    sorted_pairs = sorted(zip(ranks, returns))
    n = len(sorted_pairs)
    bin_size = n // n_deciles

    result = []
    decile_labels = {
        0: "Botten",
        n_deciles - 1: "Topp",
    }
    for i in range(n_deciles):
        start = i * bin_size
        end   = start + bin_size if i < n_deciles - 1 else n
        chunk = sorted_pairs[start:end]
        avg_ret = sum(p[1] for p in chunk) / len(chunk) if chunk else 0.0
        result.append(DecileRow(
            decile      = i,
            avg_return  = round(avg_ret, 4),
            n_dates     = len(chunk),
            label       = decile_labels.get(i, str(i + 1)),
        ))

    return result


@router.get("/top-picks", response_model=list[TopPickRow])
def get_top_picks(
    days: int = Query(30, ge=7, le=90),
    top_n: int = Query(20, ge=5, le=50),
    _user: User = Depends(require_admin),
    sb = Depends(get_supabase_admin),
):
    """Senaste topp-prediktioner (ml_rank >= 90) med utfall (om utvärderade)."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    res = sb.table("prediction_outcomes").select(
        "ticker,predicted_at,ml_rank,predicted_return,realized_return_30d,evaluated_at"
    ).gte("predicted_at", cutoff).gte("ml_rank", 90).order(
        "ml_rank", desc=True
    ).limit(top_n).execute()

    result = []
    for r in (res.data or []):
        real = r.get("realized_return_30d")
        eval_at = r.get("evaluated_at")
        if eval_at is None:
            status = "pending"
        elif real is not None and real > 0:
            status = "win"
        elif real is not None:
            status = "loss"
        else:
            status = "evaluated"

        result.append(TopPickRow(
            ticker              = r["ticker"],
            predicted_at        = str(r["predicted_at"]),
            ml_rank             = int(r["ml_rank"]),
            predicted_return    = float(r.get("predicted_return") or 0),
            realized_return_30d = real,
            outcome_status      = status,
        ))
    return result
