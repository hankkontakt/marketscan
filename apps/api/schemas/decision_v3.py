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
    # Legacy-compat context joined into the published projection during the
    # migration window (plan section 27: Kurs/Idag + segment columns).
    name: str | None = None
    segment: str | None = None
    price: float | None = None
    change_pct: float | None = None
    # Dated, sourced FX context (Phase 4): SEK per 1 unit of the listing
    # currency; NULL means no dated rate exists — never approximate.
    fx_rate_sek: float | None = None
    fx_rate_date: str | None = None
    fx_source: str | None = None


class ScreenerProjectionV3(BaseModel):
    snapshot_id: str
    as_of: str
    total_count: int
    rows: list[DecisionProjectionV3]


class CurrentSnapshotV3(BaseModel):
    current_snapshot_id: str | None = None
    published_at: str | None = None
    master_model_version: str | None = None
    code_sha: str | None = None
    manifest_count: int
    actionable_count: int
    excluded_count: int
    quality_report: dict[str, Any] = Field(default_factory=dict)