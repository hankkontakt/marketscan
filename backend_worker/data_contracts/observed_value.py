"""
ObservedValue & Provenance Data Contracts (Phase 2)
"""
from enum import Enum
from typing import TypeVar, Generic, Optional, List, Any
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

class SourceTier(str, Enum):
    A = "A"  # Authoritative (Exchanges, SEC/Finansinspektionen, official IR)
    B = "B"  # Licensed / Structured (Börsdata, EODHD)
    C = "C"  # Aggregator (Yahoo Finance, Finnhub)
    D = "D"  # AI / Web extraction (RAG, qualitative reports)

class QualityFlag(str, Enum):
    OK = "OK"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    UNIT_CONVERTED = "UNIT_CONVERTED"
    OUTLIER_TRIMMED = "OUTLIER_TRIMMED"
    DISAGREEMENT = "DISAGREEMENT"
    INCOMPLETE = "INCOMPLETE"

T = TypeVar("T")

class ObservedValue(BaseModel, Generic[T]):
    security_id: str
    listing_id: Optional[str] = None
    field_name: str
    value: Optional[T]
    unit: Optional[str] = None
    currency: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    as_of: datetime = Field(default_factory=_now_utc)
    available_at: datetime = Field(default_factory=_now_utc)
    fetched_at: datetime = Field(default_factory=_now_utc)
    source_id: str
    source_tier: SourceTier = SourceTier.B
    quality_flags: List[QualityFlag] = Field(default_factory=list)
    transform_version: str = "v2.0"

    @property
    def is_point_in_time_valid(self) -> bool:
        """Point-in-time invariant: available_at cannot be in the future relative to observation."""
        return self.available_at <= self.fetched_at

    @property
    def reliability_score(self) -> float:
        """
        Base reliability score [0.0 - 1.0] derived from source tier and quality flags.
        Tier A = 1.0, Tier B = 0.95, Tier C = 0.80, Tier D = 0.50
        """
        if self.value is None:
            return 0.0

        tier_weights = {
            SourceTier.A: 1.0,
            SourceTier.B: 0.95,
            SourceTier.C: 0.80,
            SourceTier.D: 0.50,
        }
        base = tier_weights.get(self.source_tier, 0.70)
        if QualityFlag.STALE in self.quality_flags:
            base *= 0.7
        if QualityFlag.ESTIMATED in self.quality_flags:
            base *= 0.8
        if QualityFlag.DISAGREEMENT in self.quality_flags:
            base *= 0.85
        if QualityFlag.OUTLIER_TRIMMED in self.quality_flags:
            base *= 0.9
        return max(0.0, min(1.0, base))
