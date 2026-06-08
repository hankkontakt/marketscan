"""
FastAPI main — Vercel serverless entrypoint.
"""
import logging
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from apps.api.core.config import settings
from apps.api.core.logging_config import setup_logging
from apps.api.core.security_headers import add_security_headers
from apps.api.core.rate_limiter import add_rate_limiting
from apps.api.core.request_id import RequestIDMiddleware, debug_router

from apps.api.routers import (
    screener, stocks, portfolio, ai, admin, profile,
    watchlist, alerts, saved_screens, snapshots, markets, calendar,
    options, prediction, smallcap, backtests, sector_rotation_router, paper_trading_router,
    notifications, transactions, macro_regime, insider,
)
from apps.api.routers import risk, smart_alerts, strategy_lab

setup_logging()
logger = logging.getLogger(__name__)
logger.info("Starting MarketScan API v2.0.0")

app = FastAPI(
    title="MarketScan API",
    version="2.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# ── Middleware ────────────────────────────────────────────────────
# NOTE on order: Starlette's add_middleware() PREPENDS — the LAST one added
# becomes the OUTERMOST layer. So CORSMiddleware is NOT outermost here
# (RequestIDMiddleware, added later, wraps it). That means an *unhandled*
# exception in a route bubbles up PAST CORSMiddleware to Starlette's
# ServerErrorMiddleware, whose 500 response has NO CORS headers — the browser
# then reports it as a network/CORS failure ("Nätverksfel") instead of a
# readable error. The global exception handler below fixes that systemically
# by attaching CORS headers to every error response itself.
_CORS_ORIGIN_REGEX = re.compile(r"https://[a-z0-9-]+-hankkontakts-projects\.vercel\.app")


def _cors_headers_for(request: Request) -> dict[str, str]:
    """Return CORS headers echoing the request Origin if it is allowed.
    Mirrors the CORSMiddleware allow-list so error responses are not blocked."""
    origin = request.headers.get("origin")
    if origin and (origin in settings.CORS_ORIGINS or _CORS_ORIGIN_REGEX.fullmatch(origin)):
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Allow all Vercel deployments under hankkontakt's org (preview + production)
    allow_origin_regex=r"https://[a-z0-9-]+-hankkontakts-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers & rate limiting
add_security_headers(app)
add_rate_limiting(app)

# Request ID middleware — log structured request info
app.middleware("http")(RequestIDMiddleware)  # function, not class — no ()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so an unhandled error NEVER reaches the browser as a bare,
    CORS-less 500 (which surfaces as "Nätverksfel"). We log the real error
    server-side and return a JSON body WITH CORS headers so the frontend can
    show a readable message and the status code."""
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internt serverfel ({type(exc).__name__})"},
        headers=_cors_headers_for(request),
    )

app.include_router(debug_router)
app.include_router(screener.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(portfolio.router)
app.include_router(ai.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(profile.router)
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(saved_screens.router)
app.include_router(snapshots.router)
app.include_router(markets.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(options.router, prefix="/api")
app.include_router(paper_trading_router.router)
app.include_router(prediction.router, prefix="/api")
app.include_router(backtests.router, prefix="/api")
app.include_router(sector_rotation_router.router, prefix="/api")
app.include_router(smallcap.router, prefix="/api")
app.include_router(notifications.router)
app.include_router(transactions.router)
app.include_router(macro_regime.router, prefix="/api")
app.include_router(insider.router, prefix="/api")

# Mega-project routers
app.include_router(risk.router)            # /api/portfolio/analytics, /optimize, /rebalance, ...
app.include_router(smart_alerts.router)    # /api/alerts, /api/score-history, /api/signal-transitions
app.include_router(strategy_lab.router)    # /api/strategies, /api/signal-analytics


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
