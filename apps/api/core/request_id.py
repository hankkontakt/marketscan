"""
Request ID middleware — adds X-Request-ID to every response,
logs structured request info.

Usage:
    from apps.api.core.request_id import RequestIDMiddleware, debug_router
    app.middleware("http")(RequestIDMiddleware)
"""
import uuid
import time
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, Response
from apps.api.core.security import require_admin, User
from apps.api.core.config import settings
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)

debug_router = APIRouter(prefix="/api/debug", tags=["debug"])


# ─── Request ID Middleware ───────────────────────────────────────────────────

async def RequestIDMiddleware(request: Request, call_next):
    """FastAPI 'http' middleware that adds X-Request-ID and logs structured info."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = time.monotonic()

    response: Response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s %s %dms [%s]",
        request.method, request.url.path, response.status_code,
        elapsed_ms, request_id,
    )

    return response


# ─── Client error capture ────────────────────────────────────────────────────

class ClientErrorIn(BaseModel):
    message: str
    stack: str | None = None
    url: str | None = None
    request_id: str | None = None
    user_agent: str | None = None


@debug_router.post("/client-error", status_code=200)
async def capture_client_error(body: ClientErrorIn):
    """Log client-side errors. Rate-limited via slowapi."""
    logger.warning("Client error: %s | url=%s | rid=%s", body.message[:200], body.url, body.request_id)
    try:
        from apps.api.dependencies import get_supabase_admin
        sb = get_supabase_admin()
        sb.table("client_errors").insert({
            "message": body.message[:500],
            "stack": body.stack[:2000] if body.stack else None,
            "url": body.url,
            "request_id": body.request_id,
        }).execute()
    except Exception as e:
        logger.debug("Could not store client error: %s", e)
    return {"ok": True}


# ─── Debug health / env ──────────────────────────────────────────────────────

@debug_router.get("/health")
async def debug_health(user: User = Depends(require_admin)):
    """Admin-protected health probe — checks all env vars and DB."""
    import os

    env = {
        "finnhub": bool(settings.FINNHUB_API_KEY),
        "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "r2": bool(settings.R2_KEY_ID and settings.R2_SECRET),
        "deepseek": bool(settings.DEEPSEEK_API_KEY),
        "gh_token": bool(os.environ.get("GH_DISPATCH_TOKEN", "")),
    }

    db = {"scan_results_rows": None, "last_pipeline_run": None, "pending_ticker_requests": None}
    try:
        sb = get_supabase()
        cnt = sb.table("scan_results").select("ticker", count="exact").execute()
        db["scan_results_rows"] = cnt.count or 0
    except Exception as e:
        db["scan_results_rows"] = f"Error: {e}"

    return {"env": env, "db": db, "settings": {"environment": settings.ENVIRONMENT}}
