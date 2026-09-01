"""
Decision API v2 Schemas & Data Contracts (Phase 6)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend_worker.ranking_v2.master_rank_v2 import ThesisBand, FactorDriver
from backend_worker.setup.setup_engine import SetupState
from backend_worker.risk.risk_engine import RiskState, DataGrade

class PriceQuote(BaseModel):
    value: float
    currency: str
    change_pct: float
    as_of: str

class MasterRankDetails(BaseModel):
    score: float
    band: ThesisBand
    segment_percentile: float
    weighted_coverage: float
    model_version: str

class SetupDetails(BaseModel):
    state: SetupState
    ui_label_sv: str
    reason_codes: List[str] = Field(default_factory=list)

class RiskDetails(BaseModel):
    state: RiskState
    dominant_risk: str
    liquidity_grade: str
    risk_flags: List[str] = Field(default_factory=list)

class DataGradeDetails(BaseModel):
    grade: DataGrade
    weighted_coverage: float
    critical_warnings: List[str] = Field(default_factory=list)

class DecisionRowV2(BaseModel):
    decision_snapshot_id: str
    listing_id: str
    ticker: str
    name: str
    segment: str
    sector: Optional[str] = None
    country: str = "SE"
    price: PriceQuote
    master_rank: MasterRankDetails
    setup: SetupDetails
    risk: RiskDetails
    data_grade: DataGradeDetails
    positive_drivers: List[FactorDriver] = Field(default_factory=list)
    negative_drivers: List[FactorDriver] = Field(default_factory=list)

class ScreenerResponseV2(BaseModel):
    total_count: int
    rows: List[DecisionRowV2]
    as_of: str
    snapshot_id: str
    active_filters: Dict[str, Any] = Field(default_factory=dict)

class StockDecisionV2(BaseModel):
    decision_snapshot_id: str
    listing_id: str
    ticker: str
    name: str
    segment: str
    sector: Optional[str] = None
    country: str
    price: PriceQuote
    master_rank: MasterRankDetails
    setup: SetupDetails
    risk: RiskDetails
    data_grade: DataGradeDetails
    positive_drivers: List[FactorDriver] = Field(default_factory=list)
    negative_drivers: List[FactorDriver] = Field(default_factory=list)
    factor_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    factor_reliabilities: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
