from pydantic import BaseModel, Field
from typing import Literal


class ScanRow(BaseModel):
    ticker: str
    name: str
    segment: Literal["large_cap", "mid_cap", "small_cap", "micro_cap"]
    sector: str | None = None
    country: str = "SE"

    score_total: float | None = None
    score_value: float | None = None
    score_quality: float | None = None
    score_momentum: float | None = None
    score_growth: float | None = None
    score_risk: float | None = None
    score_size: float | None = None
    score_dividend: float | None = None
    score_sentiment: float | None = None

    entry_signal: Literal["STARK", "OK", "VÄNTA", "EJ_AKTUELL"] | None = None
    confidence_label: Literal["Hög", "Medel", "Låg"] | None = None
    trend_signal: Literal["Upptrend", "Sidled", "Nedtrend"] | None = None
    predicted_return: float | None = None
    ml_rank: int | None = None
    piotroski_f: int | None = Field(None, ge=0, le=9)

    price: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    pe_trailing: float | None = None
    pe_forward: float | None = None
    roe: float | None = None
    roa: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    vol_20d: float | None = None

    low_liquidity: bool = False
    has_holding: bool = False
    scan_date: str | None = None


class ScanFilters(BaseModel):
    segments: list[str] = ["large_cap", "mid_cap"]
    score_min: float = 0
    score_max: float = 100
    sector: str | None = None
    country: str | None = None
    entry_signal: str | None = None
    trend_signal: str | None = None
    piotroski_min: int | None = None
    pe_max: float | None = None
    roe_min: float | None = None
    dividend_yield_min: float | None = None
    exclude_low_liquidity: bool = False
    limit: int = Field(200, ge=1, le=500)
    search: str | None = None
