"""
Event Intelligence Engine v2 (Phase 4)
Separates EventRisk (upcoming binary uncertainty), EventOutcome (surprise vs estimate), and MarketResponse.
Eliminates the legacy '+5 proximity catalyst boost'.
"""
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from enum import Enum
from pydantic import BaseModel, Field

class EventRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class MarketVerdict(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    PENDING = "PENDING"

class EventStateOutput(BaseModel):
    listing_id: Optional[str] = None
    event_type: str
    event_date: date
    is_confirmed: bool = False
    days_to_event: int
    event_risk_level: EventRiskLevel = EventRiskLevel.LOW
    proximity_alpha_boost: float = 0.0  # INVARIANT: MUST ALWAYS BE 0.0 in v2

    # Outcome
    actual_eps: Optional[float] = None
    estimated_eps: Optional[float] = None
    eps_surprise_pct: Optional[float] = None

    # Market response
    gap_pct: Optional[float] = None
    volume_multiple_1d: Optional[float] = None
    market_verdict: MarketVerdict = MarketVerdict.PENDING

def evaluate_event_state(
    event_type: str,
    event_date: date,
    is_confirmed: bool = False,
    today: Optional[date] = None,
    actual_eps: Optional[float] = None,
    estimated_eps: Optional[float] = None,
    post_event_open: Optional[float] = None,
    pre_event_close: Optional[float] = None,
    post_event_volume: Optional[float] = None,
    avg_volume: Optional[float] = None
) -> EventStateOutput:
    today_dt = today or date.today()
    days_to_event = (event_date - today_dt).days

    # 1. Evaluate EventRisk (uncertainty level)
    if days_to_event < 0:
        # Completed event
        risk_level = EventRiskLevel.LOW
    elif days_to_event <= 7:
        risk_level = EventRiskLevel.HIGH if is_confirmed else EventRiskLevel.MEDIUM
    elif days_to_event <= 21:
        risk_level = EventRiskLevel.MEDIUM
    else:
        risk_level = EventRiskLevel.LOW

    # 2. Evaluate Outcome (if completed)
    surprise_pct = None
    if actual_eps is not None and estimated_eps is not None and abs(estimated_eps) > 0.0001:
        surprise_pct = round((actual_eps - estimated_eps) / abs(estimated_eps), 4)

    # 3. Evaluate Market Response
    gap_pct = None
    if post_event_open is not None and pre_event_close is not None and pre_event_close > 0:
        gap_pct = round((post_event_open / pre_event_close) - 1.0, 4)

    vol_mult = None
    if post_event_volume is not None and avg_volume is not None and avg_volume > 0:
        vol_mult = round(post_event_volume / avg_volume, 2)

    verdict = MarketVerdict.PENDING
    if gap_pct is not None:
        if gap_pct >= 0.03:
            verdict = MarketVerdict.POSITIVE
        elif gap_pct <= -0.03:
            verdict = MarketVerdict.NEGATIVE
        else:
            verdict = MarketVerdict.NEUTRAL

    return EventStateOutput(
        event_type=event_type,
        event_date=event_date,
        is_confirmed=is_confirmed,
        days_to_event=days_to_event,
        event_risk_level=risk_level,
        proximity_alpha_boost=0.0,  # Zero boost invariant verified
        actual_eps=actual_eps,
        estimated_eps=estimated_eps,
        eps_surprise_pct=surprise_pct,
        gap_pct=gap_pct,
        volume_multiple_1d=vol_mult,
        market_verdict=verdict
    )
