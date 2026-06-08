"""
Admin endpoints — Kontrollpanel backend.
Requires admin role.
Supports pipeline trigger, health/diagnostics, queue management, coverage.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from collections import Counter
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient
from apps.api.core.security import get_current_user, require_admin, User
from apps.api.core.config import settings
from apps.api.dependencies import get_supabase, get_supabase_admin


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PipelineRunOut(BaseModel):
    id: str
    run_type: str
    status: str
    tickers_ok: int | None = None
    tickers_err: int | None = None
    duration_s: float | None = None
    error_msg: str | None = None
    started_at: str | None = None


class SystemStatusOut(BaseModel):
    scan_rows: int
    last_runs: list[PipelineRunOut]


class ScoreDistributionOut(BaseModel):
    buckets: list[dict]
    total: int
    by_signal: dict[str, int]


class UniverseStatsOut(BaseModel):
    by_sector: dict[str, int]
    by_segment: dict[str, int]
    by_country: dict[str, int]
    low_liquidity: int
    total: int


class PipelineTriggerIn(BaseModel):
    mode: str = "morning"  # morning, evening, weekly, smallcap, targeted, refresh_missing, retry_rate_limited
    tickers: list[str] | None = None  # for targeted mode


class PipelineQueueItem(BaseModel):
    ticker: str
    name: str | None = None
    source: str | None = None
    user_id: str | None = None
    created_at: str | None = None


class HealthCheckItem(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class HealthCheckOut(BaseModel):
    env: dict[str, bool]
    db: dict[str, int | None]
    checks: list[HealthCheckItem]


class UsersListOut(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    created_at: str | None = None


# ─── Status ───────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SystemStatusOut)
def system_status(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Pipeline health, latest run, scan freshness."""
    _ = user  # admin access verified
    scan_count = sb.table("scan_results").select("ticker", count="exact").execute()
    last_run = (
        sb.table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(5)
        .execute()
    )
    return {
        "scan_rows": scan_count.count or 0,
        "last_runs": last_run.data or [],
    }


@router.get("/pipeline-runs", response_model=list[PipelineRunOut])
def pipeline_runs(
    limit: int = 20,
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    res = (
        sb.table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


@router.get("/users", response_model=list[UsersListOut])
def list_users(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    profiles = sb.table("profiles").select("*").order("created_at").execute()
    return profiles.data or []


@router.get("/score-distribution", response_model=ScoreDistributionOut)
def score_distribution(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Score histogram for monitoring model drift."""
    res = sb.table("scan_results").select("score_total, segment, entry_signal").execute()
    rows = res.data or []
    buckets = [0] * 10
    for r in rows:
        s = r.get("score_total")
        if s is not None:
            idx = min(int(s // 10), 9)
            buckets[idx] += 1
    return {
        "buckets": [{"range": f"{i*10}-{i*10+9}", "count": c} for i, c in enumerate(buckets)],
        "total": len(rows),
        "by_signal": {
            sig: sum(1 for r in rows if r.get("entry_signal") == sig)
            for sig in ["STARK", "OK", "VÄNTA", "EJ_AKTUELL"]
        },
    }


@router.get("/universe", response_model=UniverseStatsOut)
def universe_stats(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
):
    """Coverage by sector and segment."""
    res = sb.table("scan_results").select("sector, segment, country, low_liquidity").execute()
    rows = res.data or []
    return {
        "by_sector": dict(Counter(r.get("sector") for r in rows if r.get("sector"))),
        "by_segment": dict(Counter(r.get("segment") for r in rows)),
        "by_country": dict(Counter(r.get("country") for r in rows if r.get("country"))),
        "low_liquidity": sum(1 for r in rows if r.get("low_liquidity")),
        "total": len(rows),
    }


# ─── Pipeline Trigger ─────────────────────────────────────────────────────────

@router.post("/pipeline/trigger", status_code=202)
async def trigger_pipeline(
    body: PipelineTriggerIn,
    user: User = Depends(require_admin),
):
    """Trigger a GitHub Actions pipeline run via workflow_dispatch.

    Requires GH_DISPATCH_TOKEN env var (PAT with workflow scope).
    Returns 202 + link to the workflow run.
    """
    import os
    token = os.environ.get("GH_DISPATCH_TOKEN", "")
    if not token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "GH_DISPATCH_TOKEN saknas — pipeline-trigger ej konfigurerad")

    inputs: dict[str, str] = {"mode": body.mode}
    if body.tickers:
        inputs["tickers"] = ",".join(body.tickers[:50])

    try:
        async with AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.github.com/repos/hankkontakt/marketscan/actions/workflows/pipeline.yml/dispatches",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"ref": "main", "inputs": inputs},
            )
            if resp.status_code not in (204, 201, 200):
                logger.warning("GitHub dispatch failed: %s %s", resp.status_code, resp.text)
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"GitHub API svarade {resp.status_code}")

        return {
            "status": "triggered",
            "mode": body.mode,
            "link": "https://github.com/hankkontakt/marketscan/actions",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Pipeline trigger failed: %s", e)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kunde inte starta pipeline: {e}")


@router.get("/pipeline/queue", response_model=list[PipelineQueueItem])
def pipeline_queue(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Pending user ticker requests (out-of-universe tickers queue)."""
    res = (
        sb.table("user_ticker_requests")
        .select("ticker, name, source, user_id, created_at")
        .eq("added_to_universe", False)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return res.data or []


# ─── Health / Diagnostics ─────────────────────────────────────────────────────

@router.get("/health", response_model=HealthCheckOut)
async def admin_health_check(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase),
    sb_admin=Depends(get_supabase_admin),
):
    """Comprehensive health check: env vars, DB, external APIs."""
    import os

    # Env checks
    finnhub_set = bool(settings.FINNHUB_API_KEY)
    supabase_set = bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)
    r2_set = bool(settings.R2_KEY_ID and settings.R2_SECRET and settings.R2_ENDPOINT)
    deepseek_set = bool(settings.DEEPSEEK_API_KEY)
    gh_token_set = bool(os.environ.get("GH_DISPATCH_TOKEN", ""))

    # DB checks
    scan_results_rows = None
    last_pipeline_run = None
    pending_requests = None
    try:
        cnt = sb.table("scan_results").select("ticker", count="exact").execute()
        scan_results_rows = cnt.count or 0
    except Exception as e:
        logger.warning("DB check failed: %s", e)

    try:
        run = (
            sb.table("pipeline_runs")
            .select("started_at")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if run.data:
            last_pipeline_run = run.data[0].get("started_at")
    except Exception:
        pass

    try:
        pend = (
            sb.table("user_ticker_requests")
            .select("ticker", count="exact")
            .eq("added_to_universe", False)
            .execute()
        )
        pending_requests = pend.count or 0
    except Exception:
        pass

    # Service probes
    checks: list[HealthCheckItem] = []

    # Finnhub probe
    if finnhub_set:
        try:
            async with AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": "AAPL"},
                    headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
                )
                ok = r.status_code == 200
                checks.append(HealthCheckItem(
                    name="Finnhub API",
                    ok=ok,
                    detail=f"HTTP {r.status_code}" if not ok else "svarar",
                ))
        except Exception as e:
            checks.append(HealthCheckItem(name="Finnhub API", ok=False, detail=str(e)))
    else:
        checks.append(HealthCheckItem(name="Finnhub API", ok=False, detail="Nyckel saknas"))

    # Supabase probe
    try:
        sb_admin.table("scan_results").select("ticker").limit(1).execute()
        checks.append(HealthCheckItem(name="Supabase", ok=True, detail="svarar"))
    except Exception as e:
        checks.append(HealthCheckItem(name="Supabase", ok=False, detail=str(e)))

    # DeepSeek probe
    if deepseek_set:
        checks.append(HealthCheckItem(name="DeepSeek API", ok=True, detail="nyckel satt"))
    else:
        checks.append(HealthCheckItem(name="DeepSeek API", ok=False, detail="Nyckel saknas"))

    # R2 probe
    if r2_set:
        checks.append(HealthCheckItem(name="R2 Storage", ok=True, detail="nycklar satta"))
    else:
        checks.append(HealthCheckItem(name="R2 Storage", ok=False, detail="Nycklar saknas"))

    return {
        "env": {
            "finnhub": finnhub_set,
            "supabase": supabase_set,
            "r2": r2_set,
            "deepseek": deepseek_set,
            "gh_token": gh_token_set,
        },
        "db": {
            "scan_results_rows": scan_results_rows,
            "last_pipeline_run": last_pipeline_run,
            "pending_ticker_requests": pending_requests,
        },
        "checks": checks,
    }


@router.post("/diagnostics")
def run_diagnostics(
    mode: str = "quick",
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Run self-diagnostics. Modes: quick, full."""
    results = {}

    # Quick: DB row counts
    try:
        sr = sb.table("scan_results").select("ticker", count="exact").execute()
        results["scan_results"] = sr.count or 0
    except Exception as e:
        results["scan_results"] = f"Fel: {e}"

    try:
        pr = sb.table("pipeline_runs").select("id", count="exact").execute()
        results["pipeline_runs"] = pr.count or 0
    except Exception as e:
        results["pipeline_runs"] = f"Fel: {e}"

    try:
        ut = sb.table("user_ticker_requests").select("ticker", count="exact").execute()
        results["pending_requests"] = ut.count or 0
    except Exception as e:
        results["pending_requests"] = f"Fel: {e}"

    if mode == "full":
        # Additional checks
        try:
            recent = sb.table("pipeline_runs").select("*").order("started_at", desc=True).limit(1).execute()
            results["latest_run"] = recent.data[0] if recent.data else None
        except Exception as e:
            results["latest_run"] = f"Fel: {e}"

    return results


# ─── Cache management ─────────────────────────────────────────────────────────

@router.post("/cache/clear")
def clear_ai_cache(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Clear AI analysis cache in Supabase."""
    try:
        sb.table("ai_cache").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        return {"cleared": True}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Kunde inte rensa cache: {e}")


# ─── Candidates / Blacklist ───────────────────────────────────────────────────

class CandidateItem(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None


class CandidatesListOut(BaseModel):
    candidates: list[CandidateItem]


@router.get("/candidates", response_model=CandidatesListOut)
def list_candidates(
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Return discovery candidates (tickers from user_ticker_requests not yet in universe)."""
    res = (
        sb.table("user_ticker_requests")
        .select("ticker, name")
        .eq("added_to_universe", False)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"candidates": [CandidateItem(ticker=r["ticker"], name=r.get("name")) for r in (res.data or [])]}


@router.post("/candidates/{ticker}/approve")
def approve_candidate(
    ticker: str,
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Mark ticker as added to universe (removes from queue)."""
    sb.table("user_ticker_requests").update({"added_to_universe": True}).eq("ticker", ticker.upper()).execute()
    return {"ok": True}


@router.post("/candidates/{ticker}/reject")
def reject_candidate(
    ticker: str,
    user: User = Depends(require_admin),
    sb=Depends(get_supabase_admin),
):
    """Remove ticker from queue without adding."""
    sb.table("user_ticker_requests").delete().eq("ticker", ticker.upper()).execute()
    return {"ok": True}


# ─── GitHub Actions status (read-only) ────────────────────────────────────────

@router.get("/github-status")
async def github_actions_status(
    user: User = Depends(require_admin),
):
    """Read-only status of recent GitHub Actions workflow runs."""
    import os
    token = os.environ.get("GH_DISPATCH_TOKEN", "")
    if not token:
        return {"runs": []}

    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.github.com/repos/hankkontakt/marketscan/actions/runs",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                params={"per_page": 10, "page": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "runs": [
                        {
                            "id": r["id"],
                            "name": r.get("name") or r.get("event", ""),
                            "status": r.get("status", "unknown"),
                            "conclusion": r.get("conclusion"),
                            "created_at": r.get("created_at"),
                            "html_url": r.get("html_url"),
                        }
                        for r in data.get("workflow_runs", [])
                    ]
                }
            return {"runs": [], "error": f"GitHub API svarade {resp.status_code}"}
    except Exception as e:
        return {"runs": [], "error": str(e)}
