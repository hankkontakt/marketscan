"""Tests for the V3 decision-transition alert rule types.

Covers the five new rule types (thesis/setup/risk/data_grade/tradability
_transition) that evaluate against ``decision_transitions`` rows, the
``decision_id`` linkage into ``triggered_alerts``, and that legacy rule types
(e.g. ``price_cross``) keep working unchanged.
"""
from unittest import mock

from backend_worker.smart_alert_engine import (
    _TRANSITION_TYPE_MAP,
    _check_transition,
    run_alert_engine,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


def _transition(**overrides):
    """A decision_transitions row as returned by the engine's SELECT *."""
    row = {
        "snapshot_from": "snapshot-old",
        "snapshot_to": "snapshot-new",
        "listing_id": "listing-1",
        "ticker": "MSFT",
        "decision_id": "decision-1",
        "transition_type": "thesis",
        "from_state": "CONSTRUCTIVE",
        "to_state": "BULLISH",
        "reason_code": "thesis:CONSTRUCTIVE->BULLISH",
        "rank_delta": None,
    }
    row.update(overrides)
    return row


def _rule(**overrides):
    """An alert_rules row as returned by the engine's rules query."""
    rule = {
        "id": "rule-1",
        "user_id": "user-1",
        "name": "Thesis larm",
        "rule_type": "thesis_transition",
        "ticker": None,
        "conditions": [],
        "trigger_once": False,
        "trigger_count": 0,
        "active": True,
    }
    rule.update(overrides)
    return rule


def _scan_row(ticker="MSFT", price=100.0, score_total=80.0):
    """A scan_results row (only the fields the engine reads are needed)."""
    return {
        "ticker": ticker, "name": "Microsoft", "price": price,
        "score_total": score_total, "score_value": None, "score_quality": None,
        "score_momentum": None, "score_growth": None, "score_risk": None,
        "score_dividend": None, "entry_signal": None, "trend_signal": None,
        "piotroski_f": None, "vol_20d": None, "pe_trailing": None,
        "roe": None, "dividend_yield": None, "beta": None,
    }


# ─── _check_transition unit tests (pure, no DB) ─────────────────────────────


def test_check_transition_triggers_on_matching_type():
    triggered, detail, decision_id = _check_transition(
        _rule(), [_transition()], "thesis"
    )
    assert triggered is True
    assert "MSFT: thesis ändrades CONSTRUCTIVE→BULLISH (thesis:CONSTRUCTIVE->BULLISH)" in detail
    assert decision_id == "decision-1"


def test_check_transition_all_five_types():
    for rule_type, trans_type in _TRANSITION_TYPE_MAP.items():
        row = _transition(transition_type=trans_type)
        triggered, detail, decision_id = _check_transition(
            _rule(rule_type=rule_type), [row], trans_type
        )
        assert triggered is True, rule_type
        assert decision_id == "decision-1"
        assert f"{trans_type} ändrades" in detail


def test_check_transition_ticker_filter():
    rows = [
        _transition(ticker="AAPL", decision_id="decision-a"),
        _transition(ticker="MSFT", decision_id="decision-m"),
    ]
    triggered, detail, decision_id = _check_transition(
        _rule(ticker="AAPL"), rows, "thesis"
    )
    assert triggered is True
    assert "AAPL" in detail
    assert "MSFT" not in detail
    assert decision_id == "decision-a"


def test_check_transition_conditions_on_to_state():
    rule = _rule(conditions=[{"field": "to_state", "op": "=", "value": "BULLISH"}])
    triggered, _, decision_id = _check_transition(rule, [_transition()], "thesis")
    assert triggered is True
    assert decision_id == "decision-1"

    rule_no = _rule(conditions=[{"field": "to_state", "op": "=", "value": "BEARISH"}])
    triggered_no, detail_no, decision_id_no = _check_transition(
        rule_no, [_transition()], "thesis"
    )
    assert triggered_no is False
    assert detail_no == ""
    assert decision_id_no is None


def test_check_transition_rank_delta_in_detail():
    row = _transition(
        transition_type="rank",
        from_state="75.0",
        to_state="82.0",
        reason_code="rank_delta:+7.0",
        rank_delta=7.0,
    )
    triggered, detail, decision_id = _check_transition(_rule(), [row], "rank")
    assert triggered is True
    assert "rank_delta +7.0" in detail
    assert decision_id == "decision-1"


def test_check_transition_no_match_returns_false():
    triggered, detail, decision_id = _check_transition(
        _rule(), [_transition(transition_type="setup")], "thesis"
    )
    assert triggered is False
    assert detail == ""
    assert decision_id is None


# ─── run_alert_engine integration tests (mocked psycopg2) ───────────────────


def _run_engine(scan_rows, history_rows, signal_rows, insider_rows,
                prev_vol_rows, decision_rows, rules):
    """Run run_alert_engine with a mocked connection.

    fetchall is called in the engine's fixed query order: scan_results,
    score_history (7d), signal_transitions, insider_trades, score_history (vol),
    decision_transitions, alert_rules. execute_batch is mocked so the batch
    inserts are recorded instead of executed against a fake cursor.
    """
    conn = mock.MagicMock()
    conn.__enter__.return_value = conn  # `with psycopg2.connect(...) as conn:`
    cursor = conn.cursor.return_value
    cursor.fetchall.side_effect = [
        scan_rows,
        history_rows,
        signal_rows,
        insider_rows,
        prev_vol_rows,
        decision_rows,
        rules,
    ]
    with mock.patch(
        "backend_worker.smart_alert_engine.psycopg2.connect", return_value=conn
    ), mock.patch(
        "backend_worker.smart_alert_engine.psycopg2.extras.execute_batch"
    ) as exec_batch:
        stats = run_alert_engine("postgres://fake")
    return stats, conn, cursor, exec_batch


def _triggered_insert_rows(exec_batch):
    """Return the rows passed to the triggered_alerts execute_batch."""
    calls = [
        c for c in exec_batch.call_args_list
        if "INSERT INTO triggered_alerts" in str(c.args[1])
    ]
    assert len(calls) == 1, "expected exactly one triggered_alerts insert"
    return list(calls[0].args[2])  # execute_batch(cur, sql, argslist, ...)


def test_run_engine_thesis_transition_triggers_with_decision_id():
    scan_rows = [_scan_row()]
    decision_rows = [_transition()]
    rules = [_rule()]
    stats, conn, cursor, exec_batch = _run_engine(
        scan_rows, [], [], [], [], decision_rows, rules
    )
    assert stats["triggered"] == 1
    rows = _triggered_insert_rows(exec_batch)
    assert rows[0]["rule_type"] == "thesis_transition"
    assert rows[0]["decision_id"] == "decision-1"
    assert "MSFT: thesis ändrades CONSTRUCTIVE→BULLISH" in rows[0]["detail"]


def test_run_engine_tradability_transition_triggers():
    decision_rows = [_transition(
        transition_type="tradability",
        from_state="ACTIVE",
        to_state="HALTED",
        reason_code="tradability:ACTIVE->HALTED",
    )]
    rules = [_rule(rule_type="tradability_transition")]
    stats, conn, cursor, exec_batch = _run_engine(
        [_scan_row()], [], [], [], [], decision_rows, rules
    )
    assert stats["triggered"] == 1
    rows = _triggered_insert_rows(exec_batch)
    assert rows[0]["rule_type"] == "tradability_transition"
    assert "tradability ändrades ACTIVE→HALTED" in rows[0]["detail"]
    assert rows[0]["decision_id"] == "decision-1"


def test_run_engine_legacy_price_cross_unaffected():
    scan_rows = [_scan_row(price=100.0)]
    rules = [_rule(
        id="rule-legacy",
        name="Price larm",
        rule_type="price_cross",
        ticker="MSFT",
        conditions=[{"field": "price", "op": ">=", "value": 90}],
    )]
    stats, conn, cursor, exec_batch = _run_engine(scan_rows, [], [], [], [], [], rules)
    assert stats["triggered"] == 1
    rows = _triggered_insert_rows(exec_batch)
    assert rows[0]["rule_type"] == "price_cross"
    assert rows[0]["decision_id"] is None
    assert "MSFT kurs 100.00" in rows[0]["detail"]


def test_run_engine_transition_no_match_does_not_trigger():
    decision_rows = [_transition(transition_type="setup")]
    rules = [_rule(rule_type="thesis_transition")]
    stats, conn, cursor, exec_batch = _run_engine(
        [_scan_row()], [], [], [], [], decision_rows, rules
    )
    assert stats["triggered"] == 0
    assert exec_batch.call_args_list == []
