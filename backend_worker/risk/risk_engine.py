"""
Risk & Investability Engine v2 (Phase 5)
Calculates multi-dimensional RiskState (LOW, MEDIUM, HIGH, VERY_HIGH, EVENT, INSUFFICIENT)
and DataGrade (A-F) based on factor coverage, freshness, and source reliability.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RiskState(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    EVENT = "EVENT"
    INSUFFICIENT = "INSUFFICIENT"

class DataGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"

class RiskResult(BaseModel):
    risk_state: RiskState
    data_grade: DataGrade
    liquidity_grade: str  # 'A'-'F'
    dominant_risk: str
    risk_flags: List[str] = Field(default_factory=list)
    critical_warnings: List[str] = Field(default_factory=list)

def compute_data_grade(
    weighted_coverage: float,
    has_price: bool = True,
    has_critical_stale_data: bool = False,
    is_tradable: bool = True
) -> DataGrade:
    """
    Compute DataGrade A-F based on weighted factor coverage and freshness.
    Grade A: >= 90% coverage, no stale critical fields, active tradable identity.
    Grade B: 80% - 89% coverage
    Grade C: 70% - 79% coverage
    Grade D: 60% - 69% coverage
    Grade E: 45% - 59% coverage
    Grade F: < 45% coverage or inactive/delisted identity
    """
    if not is_tradable or not has_price:
        return DataGrade.F

    if has_critical_stale_data:
        weighted_coverage = max(0.0, weighted_coverage - 0.20)

    if weighted_coverage >= 0.90:
        return DataGrade.A
    elif weighted_coverage >= 0.80:
        return DataGrade.B
    elif weighted_coverage >= 0.70:
        return DataGrade.C
    elif weighted_coverage >= 0.60:
        return DataGrade.D
    elif weighted_coverage >= 0.45:
        return DataGrade.E
    else:
        return DataGrade.F

def compute_risk_state(
    liquidity_grade: str = "B",
    debt_to_equity: Optional[float] = None,
    volatility_20d: Optional[float] = None,
    days_to_earnings: Optional[int] = None,
    weighted_coverage: float = 0.85,
    is_tradable: bool = True
) -> RiskResult:
    risk_flags = []
    warnings = []

    if not is_tradable:
        return RiskResult(
            risk_state=RiskState.INSUFFICIENT,
            data_grade=DataGrade.F,
            liquidity_grade=liquidity_grade,
            dominant_risk="SECURITY_INACTIVE",
            risk_flags=["INACTIVE_SECURITY"],
            critical_warnings=["Instrument is inactive, merged or delisted"]
        )

    data_grade = compute_data_grade(weighted_coverage, is_tradable=is_tradable)
    if data_grade in (DataGrade.E, DataGrade.F):
        warnings.append(f"Low data quality grade ({data_grade.value})")

    # 1. Event risk
    is_event_near = (days_to_earnings is not None and 0 <= days_to_earnings <= 5)
    if is_event_near:
        risk_flags.append("EARNINGS_IMMINENT")

    # 2. Balance sheet / leverage risk
    is_high_debt = (debt_to_equity is not None and debt_to_equity > 2.5)
    if is_high_debt:
        risk_flags.append("HIGH_LEVERAGE_DEBT")

    # 3. Market / Volatility risk
    is_high_vol = (volatility_20d is not None and volatility_20d > 0.45)
    if is_high_vol:
        risk_flags.append("HIGH_REALIZED_VOLATILITY")

    # 4. Liquidity risk
    is_illiquid = liquidity_grade in ("E", "F")
    if is_illiquid:
        risk_flags.append(f"POOR_LIQUIDITY_GRADE_{liquidity_grade}")

    # Determine overall RiskState & Dominant Risk
    if is_high_debt and is_illiquid:
        risk_state = RiskState.VERY_HIGH
        dominant = "LEVERAGE_AND_ILLIQUIDITY"
    elif is_high_debt:
        risk_state = RiskState.HIGH
        dominant = "BALANCE_SHEET_LEVERAGE"
    elif is_illiquid:
        risk_state = RiskState.HIGH
        dominant = "LOW_LIQUIDITY"
    elif is_event_near:
        risk_state = RiskState.EVENT
        dominant = "IMMINENT_EARNINGS_EVENT"
    elif is_high_vol:
        risk_state = RiskState.MEDIUM
        dominant = "MARKET_VOLATILITY"
    else:
        risk_state = RiskState.LOW
        dominant = "NORMAL_UNCERTAINTY"

    return RiskResult(
        risk_state=risk_state,
        data_grade=data_grade,
        liquidity_grade=liquidity_grade,
        dominant_risk=dominant,
        risk_flags=risk_flags,
        critical_warnings=warnings
    )
