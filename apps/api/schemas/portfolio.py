from pydantic import BaseModel, Field
from datetime import datetime


class HoldingIn(BaseModel):
    ticker: str
    shares: float = Field(..., gt=0)
    cost_basis: float | None = None


class HoldingOut(BaseModel):
    id: str
    portfolio_id: str
    ticker: str
    shares: float
    cost_basis: float | None = None
    added_at: datetime

    # Enriched from scan_results (joined in API)
    name: str | None = None
    price: float | None = None
    change_pct: float | None = None
    score_total: float | None = None
    entry_signal: str | None = None


class PortfolioOut(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: datetime
    holdings: list[HoldingOut] = []


class WatchlistItem(BaseModel):
    id: str
    ticker: str
    added_at: datetime
    # Enriched
    name: str | None = None
    price: float | None = None
    change_pct: float | None = None
    score_total: float | None = None
    entry_signal: str | None = None


class PriceAlertIn(BaseModel):
    ticker: str
    condition: str = Field(..., pattern="^(above|below)$")
    target_price: float = Field(..., gt=0)
    note: str | None = None


class PriceAlertOut(BaseModel):
    id: str
    ticker: str
    condition: str
    target_price: float
    note: str | None = None
    active: bool
    triggered_at: datetime | None = None
    created_at: datetime


class SavedScreenIn(BaseModel):
    name: str
    filter_json: dict


class SavedScreenOut(BaseModel):
    id: str
    name: str
    filter_json: dict
    created_at: datetime
