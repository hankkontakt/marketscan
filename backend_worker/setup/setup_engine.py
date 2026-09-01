"""
SetupState Machine & Engine (Phase 5)
Calculates descriptive short-term price structure state:
CONFIRMED | PULLBACK | NEUTRAL | EXTENDED | DAMAGED | EVENT_RISK | INSUFFICIENT
"""
from enum import Enum
from typing import Optional, List, Dict, Any
import numpy as np
from pydantic import BaseModel, Field

class SetupState(str, Enum):
    CONFIRMED = "CONFIRMED"
    PULLBACK = "PULLBACK"
    NEUTRAL = "NEUTRAL"
    EXTENDED = "EXTENDED"
    DAMAGED = "DAMAGED"
    EVENT_RISK = "EVENT_RISK"
    INSUFFICIENT = "INSUFFICIENT"

SETUP_UI_COPY = {
    SetupState.CONFIRMED: "Bekräftad trend",
    SetupState.PULLBACK: "Kontrollerad rekyl",
    SetupState.NEUTRAL: "Neutral setup",
    SetupState.EXTENDED: "Utsträckt",
    SetupState.DAMAGED: "Skadad prisbild",
    SetupState.EVENT_RISK: "Rapport/event nära",
    SetupState.INSUFFICIENT: "Otillräcklig data",
}

class SetupResult(BaseModel):
    state: SetupState
    ui_label_sv: str
    atr_extension_ma20: Optional[float] = None
    dist_ma50_pct: Optional[float] = None
    dist_ma200_pct: Optional[float] = None
    rsi_14: Optional[float] = None
    reason_codes: List[str] = Field(default_factory=list)
    shadow_score: Optional[float] = None

def compute_setup_state(
    price: Optional[float],
    ma20: Optional[float] = None,
    ma50: Optional[float] = None,
    ma200: Optional[float] = None,
    atr: Optional[float] = None,
    rsi_14: Optional[float] = None,
    days_to_earnings: Optional[int] = None,
    recent_gap_pct: Optional[float] = None
) -> SetupResult:
    reasons = []

    # 1. Check for missing data
    if price is None or price <= 0:
        return SetupResult(
            state=SetupState.INSUFFICIENT,
            ui_label_sv=SETUP_UI_COPY[SetupState.INSUFFICIENT],
            reason_codes=["MISSING_PRICE_DATA"]
        )

    # 2. Event window override
    if days_to_earnings is not None and 0 <= days_to_earnings <= 7:
        return SetupResult(
            state=SetupState.EVENT_RISK,
            ui_label_sv=SETUP_UI_COPY[SetupState.EVENT_RISK],
            rsi_14=rsi_14,
            reason_codes=["EARNINGS_INSIDE_7D_WINDOW"]
        )

    # 3. Compute extensions and distances
    dist_ma50 = ((price / ma50) - 1.0) if (ma50 is not None and ma50 > 0) else None
    dist_ma200 = ((price / ma200) - 1.0) if (ma200 is not None and ma200 > 0) else None

    atr_ext_ma20 = None
    if ma20 is not None and atr is not None and atr > 0:
        atr_ext_ma20 = (price - ma20) / atr

    # 4. DAMAGED State: Sharp recent adverse gap or broken long-term trend
    if recent_gap_pct is not None and recent_gap_pct <= -0.12:
        reasons.append("SEVERE_POST_EVENT_GAP_DOWN")
        return SetupResult(
            state=SetupState.DAMAGED,
            ui_label_sv=SETUP_UI_COPY[SetupState.DAMAGED],
            atr_extension_ma20=atr_ext_ma20,
            dist_ma50_pct=dist_ma50,
            dist_ma200_pct=dist_ma200,
            rsi_14=rsi_14,
            reason_codes=reasons
        )

    if dist_ma200 is not None and dist_ma200 < -0.10:
        reasons.append("PRICE_BELOW_MA200_BY_OVER_10PCT")
        return SetupResult(
            state=SetupState.DAMAGED,
            ui_label_sv=SETUP_UI_COPY[SetupState.DAMAGED],
            atr_extension_ma20=atr_ext_ma20,
            dist_ma50_pct=dist_ma50,
            dist_ma200_pct=dist_ma200,
            rsi_14=rsi_14,
            reason_codes=reasons
        )

    # 5. EXTENDED State: ATR stretched or extreme overbought
    if (atr_ext_ma20 is not None and atr_ext_ma20 > 2.5) or (rsi_14 is not None and rsi_14 >= 78.0) or (dist_ma50 is not None and dist_ma50 > 0.30):
        reasons.append("STATISTICALLY_EXTENDED_VS_ATR_MA")
        return SetupResult(
            state=SetupState.EXTENDED,
            ui_label_sv=SETUP_UI_COPY[SetupState.EXTENDED],
            atr_extension_ma20=atr_ext_ma20,
            dist_ma50_pct=dist_ma50,
            dist_ma200_pct=dist_ma200,
            rsi_14=rsi_14,
            reason_codes=reasons
        )

    # 6. PULLBACK State: Long trend intact (above MA200) but pulling back in short term
    if dist_ma200 is not None and dist_ma200 >= 0:
        if (dist_ma50 is not None and -0.12 <= dist_ma50 <= -0.02) or (rsi_14 is not None and 35.0 <= rsi_14 <= 48.0):
            reasons.append("CONTROLLED_PULLBACK_IN_UPTREND")
            return SetupResult(
                state=SetupState.PULLBACK,
                ui_label_sv=SETUP_UI_COPY[SetupState.PULLBACK],
                atr_extension_ma20=atr_ext_ma20,
                dist_ma50_pct=dist_ma50,
                dist_ma200_pct=dist_ma200,
                rsi_14=rsi_14,
                reason_codes=reasons
            )

    # 7. CONFIRMED State: Healthy uptrend
    if (dist_ma50 is not None and dist_ma50 > 0) and (dist_ma200 is not None and dist_ma200 > 0) and (rsi_14 is not None and 50.0 <= rsi_14 <= 75.0):
        reasons.append("HEALTHY_UPTREND_STRUCTURE")
        return SetupResult(
            state=SetupState.CONFIRMED,
            ui_label_sv=SETUP_UI_COPY[SetupState.CONFIRMED],
            atr_extension_ma20=atr_ext_ma20,
            dist_ma50_pct=dist_ma50,
            dist_ma200_pct=dist_ma200,
            rsi_14=rsi_14,
            reason_codes=reasons
        )

    # Default: NEUTRAL
    reasons.append("NO_STATISTICAL_EDGE")
    return SetupResult(
        state=SetupState.NEUTRAL,
        ui_label_sv=SETUP_UI_COPY[SetupState.NEUTRAL],
        atr_extension_ma20=atr_ext_ma20,
        dist_ma50_pct=dist_ma50,
        dist_ma200_pct=dist_ma200,
        rsi_14=rsi_14,
        reason_codes=reasons
    )
