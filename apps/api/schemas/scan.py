from pydantic import BaseModel, Field
from typing import Literal


class ScanRow(BaseModel):
    ticker: str
    name: str
    segment: Literal["large_cap", "mid_cap", "small_cap", "micro_cap", "unknown"]
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
    pe_trailing_raw: float | None = None
    pe_forward_raw: float | None = None
    roe: float | None = None
    roa: float | None = None
    roe_raw: float | None = None
    roa_raw: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    revenue_growth_raw: float | None = None
    earnings_growth_raw: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    vol_20d: float | None = None

    # BOOL_NOT_OPTIONAL_GOTCHA: columns are NULL-able in DB and the COPY loader
    # writes explicit NULL when the source parquet had NaN (bypasses the column
    # DEFAULT false).  Pydantic rejects None for a strict `bool`, which made the
    # whole /scan endpoint 500 (ResponseValidationError) once such a row landed.
    # Tolerate None (treated as falsy by all consumers).
    low_liquidity: bool | None = False
    has_holding: bool | None = False
    scan_date: str | None = None

    # MEWS (#3)
    mews_score: float | None = None
    mews_flag: bool | None = False
    mews_fcf_yield: float | None = None
    mews_small_size: float | None = None
    mews_low_ps: float | None = None
    mews_operating_leverage: float | None = None
    mews_revenue_accel: float | None = None
    mews_clean_accruals: float | None = None

    # Fallback-basdata (när varken scan_results eller Finnhub har data):
    # universe_registry (market) + qmj_scores (senaste scan_date-raden).
    # Additiva fält — score_*-fälten ovan förblir None (ärligt).
    market: str | None = None
    alpha_rank: float | None = None
    quality_z: float | None = None
    momentum_z: float | None = None
    value_z: float | None = None
    analyst_z: float | None = None
    analyst_upside: float | None = None
    analyst_count: int | None = None
    trend_tech: str | None = None
    currency: str | None = None
    master_rank: float | None = None
    master_rank_pctl: float | None = None
    liquidity_grade: str | None = None
    turnover_20d_median: float | None = None
    tier: str | None = None
    stratum: str | None = None
