"""Read-only V3 projections of immutable published decision manifests."""
from typing import Any

from pydantic import BaseModel, Field


class DecisionProjectionV3(BaseModel):
    decision_id: str
    decision_snapshot_id: str
    listing_id: str
    ticker: str
    mic: str
    currency: str
    tradability_state: str
    decision_time: str
    master_rank_score: float | None = None
    thesis_band: str
    segment_percentile: float | None = None
    setup_vector: dict[str, Any] = Field(default_factory=dict)
    setup_state: str
    risk_vector: dict[str, Any] = Field(default_factory=dict)
    risk_state: str
    is_actionable: bool
    data_grade: str
    coverage: float
    stale_critical_count: int
    street_context: dict[str, Any] = Field(default_factory=dict)
    positive_drivers: list[dict[str, Any]] = Field(default_factory=list)
    negative_drivers: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)
    published_at: str


class ScreenerProjectionV3(BaseModel):
    snapshot_id: str
    as_of: str
    total_count: int
    rows: list[DecisionProjectionV3]
