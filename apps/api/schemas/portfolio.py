from pydantic import BaseModel, Field
from datetime import datetime


class HoldingIn(BaseModel):
    ticker: str
    shares: float = Field(..., gt=0)
    cost_basis: float | None = None
    name: str | None = None


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

    # Fallback-berikning (när scan_results saknar rad): universe_registry +
    # qmj_scores. Additiva fält — score_total/entry_signal förblir None.
    market: str | None = None
    alpha_rank: float | None = None
    quality_z: float | None = None
    momentum_z: float | None = None
    value_z: float | None = None
    stratum: str | None = None

    # V3-beslutsdata (champion-data) — additiv berikning från
    # current_decisions_v3. Inga legacy-fält; None när vyn saknar träff.
    thesis_band: str | None = None
    setup_state: str | None = None
    risk_state: str | None = None
    data_grade: str | None = None
    decision_id: str | None = None
    master_rank_score: float | None = None
    segment_percentile: float | None = None
    tradability_state: str | None = None
    is_actionable: bool | None = None
    v3_snapshot_id: str | None = None


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


class PeriodReturn(BaseModel):
    """Return for a single period (1M, 3M, 6M, 12M)."""
    pct: float | None = None
    positive: bool | None = None


class PortfolioHistoryOut(BaseModel):
    """Map of period labels to their return data."""
    periods: dict[str, PeriodReturn]


class SnapshotOut(BaseModel):
    id: str
    user_id: str
    date: str
    total_value: float
    total_cost: float | None = None
    created_at: str
