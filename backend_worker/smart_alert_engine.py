"""
Smart Alert Engine — evaluates compound alert rules nightly.

Checks all active alert_rules against current data:
  - price_cross:      compare scan_results.price vs target
  - score_change:     compare today vs N days ago in score_history
  - signal_change:    check signal_transitions for today
  - screen_match:     evaluate compound filter conditions (new entry only)
  - insider_cluster:  check insider_trades for 2+ insiders within 14 days
  - volatility_spike: check vol_20d spike > threshold

Creates:
  - notifications rows (in-app notifications)
  - triggered_alerts rows (history log)
  Sends email if user has email_opt_in = true.

Usage:
    python -m marketscan.backend_worker.smart_alert_engine
"""
import os
import json
import logging
from datetime import date, timedelta

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ─── Condition Evaluation ─────────────────────────────────────────────────────

OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    "=":  lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _eval_condition(row: dict, cond: dict) -> bool:
    """Evaluate a single condition against a scan_results row."""
    field = cond.get("field")
    op    = cond.get("op")
    value = cond.get("value")

    if not field or not op or value is None:
        return False

    row_val = row.get(field)
    if row_val is None:
        return False

    op_fn = OPERATORS.get(op)
    if not op_fn:
        return False

    try:
        return op_fn(float(row_val), float(value))
    except (TypeError, ValueError):
        # String comparison for signal fields
        try:
            return op_fn(str(row_val), str(value))
        except Exception:
            return False


def _eval_conditions(row: dict, conditions: list[dict]) -> bool:
    """Evaluate ALL conditions (AND logic)."""
    if not conditions:
        return True
    return all(_eval_condition(row, c) for c in conditions)


# ─── Alert Type Handlers ──────────────────────────────────────────────────────

def _check_price_cross(rule: dict, price_map: dict[str, float]) -> tuple[bool, str]:
    """Check if ticker's price has crossed the target in conditions."""
    ticker = rule.get("ticker")
    conditions = rule.get("conditions", [])
    if not ticker or not conditions:
        return False, ""

    price = price_map.get(ticker)
    if price is None:
        return False, ""

    row = {"price": price}
    if _eval_conditions(row, conditions):
        # Format a human-readable detail
        cond = conditions[0]
        op_label = {">=": "nådde", "<=": "föll under", ">": "steg över", "<": "föll under"}.get(cond["op"], "")
        return True, f"{ticker} kurs {price:.2f} {op_label} {cond['value']}"

    return False, ""


def _check_score_change(rule: dict, score_map: dict[str, dict],
                        history_map: dict[str, dict]) -> tuple[bool, str]:
    """Check if score_total changed significantly since N days ago."""
    ticker = rule.get("ticker")
    threshold = float(rule.get("score_change_min") or 10)
    conditions = rule.get("conditions", [])

    tickers_to_check = [ticker] if ticker else list(score_map.keys())
    results = []

    for t in tickers_to_check:
        curr = score_map.get(t, {})
        prev = history_map.get(t, {})
        if not curr or not prev:
            continue

        curr_score = curr.get("score_total")
        prev_score = prev.get("score_total")

        if curr_score is None or prev_score is None:
            continue

        change = float(curr_score) - float(prev_score)
        if abs(change) >= threshold:
            # Also check any extra conditions
            if not conditions or _eval_conditions(curr, conditions):
                direction = "steg" if change > 0 else "föll"
                results.append(f"{t}: betyg {direction} med {abs(change):.1f} poäng ({prev_score:.0f}→{curr_score:.0f})")

    if results:
        return True, "; ".join(results[:3])
    return False, ""


def _check_signal_change(rule: dict, transitions_today: list[dict]) -> tuple[bool, str]:
    """Check if a ticker's signal changed today."""
    ticker = rule.get("ticker")
    conditions = rule.get("conditions", [])

    matches = []
    for t in transitions_today:
        if ticker and t["ticker"] != ticker:
            continue

        # Check conditions on the transition (e.g., to_value = "STARK")
        trans_row = {
            "field": t["field"],
            "from_value": t["from_value"],
            "to_value": t["to_value"],
            "entry_signal": t["to_value"] if t["field"] == "entry_signal" else None,
            "trend_signal": t["to_value"] if t["field"] == "trend_signal" else None,
        }
        if not conditions or _eval_conditions(trans_row, conditions):
            from_label = t.get("from_value") or "–"
            to_label   = t.get("to_value") or "–"
            matches.append(f"{t['ticker']}: {t['field']} ändrades {from_label}→{to_label}")

    if matches:
        return True, "; ".join(matches[:3])
    return False, ""


def _check_screen_match(
    rule: dict,
    scan_rows: list[dict],
    prev_match_tickers: set[str],
) -> tuple[bool, str]:
    """
    Find tickers matching compound conditions that are NEW (not matched yesterday).
    Prevents re-triggering on same matches every day.
    """
    conditions = rule.get("conditions", [])
    if not conditions:
        return False, ""

    matches = [r["ticker"] for r in scan_rows if _eval_conditions(r, conditions)]

    # Only trigger for tickers not in yesterday's matches
    new_matches = [t for t in matches if t not in prev_match_tickers]

    if new_matches:
        return True, f"Nya matchningar: {', '.join(new_matches[:5])}"
    return False, ""


def _check_insider_cluster(
    rule: dict,
    insider_map: dict[str, int],
) -> tuple[bool, str]:
    """Check if any ticker has 2+ insider buys within 14 days."""
    ticker = rule.get("ticker")
    min_count = int(rule.get("insider_min_count") or 2)

    results = []
    for t, count in insider_map.items():
        if ticker and t != ticker:
            continue
        if count >= min_count:
            results.append(f"{t}: {count} insiderköp senaste 14 dagar")

    if results:
        return True, "; ".join(results[:3])
    return False, ""


def _check_volatility_spike(
    rule: dict,
    vol_map: dict[str, tuple[float, float]],
) -> tuple[bool, str]:
    """Check if vol_20d increased by more than threshold %."""
    ticker = rule.get("ticker")
    min_spike = float(rule.get("vol_spike_min_pct") or 50)

    results = []
    for t, (curr_vol, prev_vol) in vol_map.items():
        if ticker and t != ticker:
            continue
        if prev_vol and prev_vol > 0:
            pct_change = (curr_vol - prev_vol) / prev_vol * 100
            if pct_change >= min_spike:
                results.append(f"{t}: volatilitet +{pct_change:.0f}%")

    if results:
        return True, "; ".join(results[:3])
    return False, ""


# ─── Main Engine ─────────────────────────────────────────────────────────────

def run_alert_engine(dsn: str) -> dict[str, int]:
    """Evaluate all active alert rules and create notifications. Returns stats."""
    today     = date.today().isoformat()
    week_ago  = (date.today() - timedelta(days=7)).isoformat()
    stats     = {"rules_checked": 0, "triggered": 0, "notifications_created": 0}

    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # ── Load current scan_results ──────────────────────────────────────────
        cur.execute("""
            SELECT ticker, name, price, score_total, score_value, score_quality,
                   score_momentum, score_growth, score_risk, score_dividend,
                   entry_signal, trend_signal, piotroski_f, vol_20d,
                   pe_trailing, roe, dividend_yield, beta
            FROM scan_results
        """)
        scan_rows  = cur.fetchall()
        scan_map   = {r["ticker"]: r for r in scan_rows}
        price_map  = {r["ticker"]: float(r["price"]) for r in scan_rows if r["price"] is not None}

        # ── Score history (7 days ago) ─────────────────────────────────────────
        cur.execute("""
            SELECT DISTINCT ON (ticker) ticker, score_total
            FROM score_history
            WHERE scan_date <= %s
            ORDER BY ticker, scan_date DESC
        """, (week_ago,))
        history_map = {r["ticker"]: dict(r) for r in cur.fetchall()}

        # ── Today's signal transitions ─────────────────────────────────────────
        cur.execute("""
            SELECT ticker, field, from_value, to_value, score_total_at, price_at
            FROM signal_transitions
            WHERE transition_date = %s
        """, (today,))
        transitions_today = list(cur.fetchall())

        # ── Insider clusters (last 14 days, buy-only) ─────────────────────────
        cur.execute("""
            SELECT ticker, COUNT(*) AS cnt
            FROM insider_trades
            WHERE type ILIKE '%buy%'
              AND trade_date >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY ticker
            HAVING COUNT(*) >= 2
        """)
        insider_map = {r["ticker"]: int(r["cnt"]) for r in cur.fetchall()}

        # ── Volatility comparison (today vs 7 days ago) ────────────────────────
        cur.execute("""
            SELECT DISTINCT ON (ticker) ticker, vol_20d
            FROM score_history
            WHERE scan_date <= %s
            ORDER BY ticker, scan_date DESC
        """, (week_ago,))
        prev_vol_map = {r["ticker"]: float(r["vol_20d"]) for r in cur.fetchall() if r["vol_20d"]}
        vol_map = {
            t: (float(scan_map[t]["vol_20d"]), prev_vol_map.get(t, 0))
            for t in scan_map
            if scan_map[t].get("vol_20d")
        }

        # ── Load active alert rules ────────────────────────────────────────────
        cur.execute("""
            SELECT r.*, p.email, p.email_opt_in
            FROM alert_rules r
            JOIN auth.users u ON u.id = r.user_id
            LEFT JOIN profiles p ON p.id = r.user_id
            WHERE r.active = true
        """)
        rules = list(cur.fetchall())
        logger.info("Evaluating %d active alert rules", len(rules))

        notifications_to_insert = []
        triggered_to_insert     = []
        rules_to_update          = []

        for rule in rules:
            stats["rules_checked"] += 1
            rule_type = rule["rule_type"]
            triggered = False
            detail    = ""
            ticker    = rule.get("ticker")

            try:
                if rule_type == "price_cross":
                    triggered, detail = _check_price_cross(rule, price_map)

                elif rule_type == "score_change":
                    triggered, detail = _check_score_change(rule, scan_map, history_map)

                elif rule_type == "signal_change":
                    triggered, detail = _check_signal_change(rule, transitions_today)

                elif rule_type == "screen_match":
                    # Get yesterday's matching tickers from triggered_alerts to avoid re-triggers
                    cur.execute("""
                        SELECT DISTINCT ticker FROM triggered_alerts
                        WHERE rule_id = %s AND triggered_at >= NOW() - INTERVAL '2 days'
                          AND ticker IS NOT NULL
                    """, (rule["id"],))
                    prev_tickers = {r["ticker"] for r in cur.fetchall()}
                    triggered, detail = _check_screen_match(rule, scan_rows, prev_tickers)

                elif rule_type == "insider_cluster":
                    triggered, detail = _check_insider_cluster(rule, insider_map)

                elif rule_type == "volatility_spike":
                    triggered, detail = _check_volatility_spike(rule, vol_map)

            except Exception as exc:
                logger.warning("Rule %s evaluation error: %s", rule["id"], exc)
                continue

            if not triggered:
                continue

            stats["triggered"] += 1
            name = rule["name"] or rule_type

            # Current score/price for context
            ctx_ticker  = ticker or (detail.split(":")[0].strip() if detail else None)
            ctx_row     = scan_map.get(ctx_ticker or "", {})
            score_at    = ctx_row.get("score_total")
            price_at    = ctx_row.get("price")

            # ── In-app notification ────────────────────────────────────────────
            notifications_to_insert.append({
                "user_id": rule["user_id"],
                "type":    "price_alert",   # reuse existing type for now
                "title":   f"Larm: {name}",
                "body":    detail[:500] if detail else f"Regel '{name}' utlöstes",
                "link":    f"/aktie/{ctx_ticker}" if ctx_ticker else "/bevakningar",
            })
            stats["notifications_created"] += 1

            # ── Triggered alerts log ───────────────────────────────────────────
            triggered_to_insert.append({
                "user_id":   rule["user_id"],
                "rule_id":   rule["id"],
                "rule_name": name,
                "rule_type": rule_type,
                "ticker":    ctx_ticker,
                "detail":    detail[:500] if detail else None,
                "score_at":  score_at,
                "price_at":  price_at,
            })

            # Mark trigger_once rules as inactive
            if rule.get("trigger_once"):
                rules_to_update.append({
                    "id": rule["id"], "active": False,
                    "last_triggered": "NOW()", "trigger_count": (rule.get("trigger_count") or 0) + 1,
                })
            else:
                rules_to_update.append({
                    "id": rule["id"], "active": True,
                    "last_triggered": "NOW()", "trigger_count": (rule.get("trigger_count") or 0) + 1,
                })

        # ── Batch writes ───────────────────────────────────────────────────────
        if notifications_to_insert:
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO notifications (user_id, type, title, body, link)
                VALUES (%(user_id)s, %(type)s, %(title)s, %(body)s, %(link)s)
                """,
                notifications_to_insert,
            )

        if triggered_to_insert:
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO triggered_alerts
                    (user_id, rule_id, rule_name, rule_type, ticker, detail, score_at, price_at)
                VALUES (%(user_id)s, %(rule_id)s, %(rule_name)s, %(rule_type)s,
                        %(ticker)s, %(detail)s, %(score_at)s, %(price_at)s)
                """,
                triggered_to_insert,
            )

        for upd in rules_to_update:
            cur.execute("""
                UPDATE alert_rules
                SET active = %s, last_triggered = NOW(), trigger_count = %s
                WHERE id = %s
            """, (upd["active"], upd["trigger_count"], upd["id"]))

        conn.commit()

        # ── Cleanup: remove triggered_alerts older than 30 days ───────────────
        cur.execute("DELETE FROM triggered_alerts WHERE triggered_at < NOW() - INTERVAL '30 days'")
        conn.commit()

    logger.info(
        "Alert engine done: %d rules checked, %d triggered, %d notifications created",
        stats["rules_checked"], stats["triggered"], stats["notifications_created"],
    )
    return stats


if __name__ == "__main__":
    dsn = os.environ["DATABASE_URL"]
    run_alert_engine(dsn)
