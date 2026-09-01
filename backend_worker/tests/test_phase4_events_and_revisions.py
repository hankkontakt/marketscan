"""
Phase 4 Verification Tests: Event & Analyst Revision Engines
- Pre-event proximity neutrality (zero alpha boost)
- EventRisk categorization (HIGH/MEDIUM/LOW)
- EventOutcome EPS surprise calculation
- MarketResponse gap and volume multiples
- Analyst revisions 30d deltas, breadth, and single dispersion penalty
"""
from datetime import date, timedelta
import pytest
from backend_worker.events_v2.event_engine import evaluate_event_state, EventRiskLevel, MarketVerdict
from backend_worker.analysts_v2.revisions_engine import compute_analyst_revisions

def test_event_proximity_neutrality_and_risk():
    today = date(2026, 9, 1)
    event_date = date(2026, 9, 4)  # 3 days away

    state = evaluate_event_state(
        event_type="EARNINGS",
        event_date=event_date,
        is_confirmed=True,
        today=today
    )
    assert state.days_to_event == 3
    assert state.event_risk_level == EventRiskLevel.HIGH
    assert state.proximity_alpha_boost == 0.0  # Masterplan invariant: proximity != positive alpha

def test_event_outcome_and_market_response():
    today = date(2026, 9, 1)
    event_date = date(2026, 8, 30)  # past event

    state = evaluate_event_state(
        event_type="EARNINGS",
        event_date=event_date,
        is_confirmed=True,
        today=today,
        actual_eps=2.50,
        estimated_eps=2.00,
        pre_event_close=100.0,
        post_event_open=108.0,
        post_event_volume=2_000_000,
        avg_volume=1_000_000
    )
    assert state.eps_surprise_pct == 0.25  # +25% beat
    assert state.gap_pct == 0.08          # +8% opening gap
    assert state.volume_multiple_1d == 2.0
    assert state.market_verdict == MarketVerdict.POSITIVE

def test_analyst_revisions_breadth_and_deltas():
    revs = compute_analyst_revisions(
        current_target=120.0,
        target_30d_ago=100.0,
        current_eps_fy1=5.50,
        eps_fy1_30d_ago=5.00,
        up_revisions=8,
        down_revisions=2,
        target_std_dev=12.0,
        analyst_count=10
    )
    assert revs.target_revision_30d == 0.20   # +20% target upgrade
    assert revs.eps_revision_30d == 0.10      # +10% EPS upgrade
    assert revs.revision_breadth == 0.60      # (8 - 2) / 10 = +0.60
    assert revs.dispersion_ratio == 0.10      # 12 / 120 = 0.10 (low dispersion)
    assert revs.reliability >= 0.80

def test_analyst_dispersion_single_penalty():
    # Low dispersion case
    revs_low_disp = compute_analyst_revisions(
        current_target=100.0, target_30d_ago=100.0,
        current_eps_fy1=5.0, eps_fy1_30d_ago=5.0,
        target_std_dev=5.0, analyst_count=10
    )
    # High dispersion case (std_dev = 35.0 -> 35% dispersion)
    revs_high_disp = compute_analyst_revisions(
        current_target=100.0, target_30d_ago=100.0,
        current_eps_fy1=5.0, eps_fy1_30d_ago=5.0,
        target_std_dev=35.0, analyst_count=10
    )
    assert revs_high_disp.dispersion_ratio == 0.35
    assert revs_high_disp.reliability < revs_low_disp.reliability
    assert revs_high_disp.reliability == pytest.approx(revs_low_disp.reliability * 0.75, abs=0.05)
