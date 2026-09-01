from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field
import uuid

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

class SecurityState(str, Enum):
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"
    SUSPENDED = "SUSPENDED"
    ACQUISITION_PENDING = "ACQUISITION_PENDING"
    DELISTING_PENDING = "DELISTING_PENDING"
    MERGED = "MERGED"
    DELISTED = "DELISTED"
    BANKRUPT = "BANKRUPT"
    UNKNOWN = "UNKNOWN"

    @property
    def is_tradable(self) -> bool:
        """Only ACTIVE listings receive live trading recommendations."""
        return self == SecurityState.ACTIVE

    @property
    def allows_live_thesis(self) -> bool:
        """Thesis may exist for ACTIVE or ACQUISITION_PENDING, but not DELISTED/MERGED."""
        return self in (SecurityState.ACTIVE, SecurityState.ACQUISITION_PENDING, SecurityState.HALTED)

class CorporateActionType(str, Enum):
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    DELISTING = "DELISTING"
    BANKRUPTCY = "BANKRUPTCY"
    SPINOFF = "SPINOFF"
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    TICKER_CHANGE = "TICKER_CHANGE"
    OTHER = "OTHER"

class Issuer(BaseModel):
    issuer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    legal_name: str
    country: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    lei: Optional[str] = None
    cik: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)

class Security(BaseModel):
    security_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issuer_id: str
    isin: Optional[str] = None
    figi: Optional[str] = None
    share_class: str = "Common"
    is_primary: bool = True
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)

class Listing(BaseModel):
    listing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    security_id: str
    mic: str
    ticker: str
    currency: str
    state: SecurityState = SecurityState.ACTIVE
    is_primary_listing: bool = True
    valid_from: datetime = Field(default_factory=_now_utc)
    valid_to: Optional[datetime] = None
    verified_at: datetime = Field(default_factory=_now_utc)

class CorporateAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    security_id: str
    listing_id: Optional[str] = None
    action_type: CorporateActionType
    effective_date: date
    deal_terms: Dict[str, Any] = Field(default_factory=dict)
    successor_security_id: Optional[str] = None
    source: Optional[str] = None
    verified_at: datetime = Field(default_factory=_now_utc)
