"""
FastAPI main — Vercel serverless entrypoint.
Stateless: no module-level mutable state (Vercel spins up/down).
Bundle must stay under 500 MB: NO pandas/xgboost/yfinance imports here.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.core.config import settings
from apps.api.core.logging_config import setup_logging
from apps.api.routers import (
    screener, stocks, portfolio, ai, admin, profile,
    watchlist, alerts, saved_screens, snapshots,
)

setup_logging()
logger = logging.getLogger(__name__)
logger.info("Starting MarketScan API v2.0.0")

app = FastAPI(
    title="MarketScan API",
    version="2.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
