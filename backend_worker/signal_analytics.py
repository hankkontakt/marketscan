"""
Signal Analytics — analyses signal persistence and forward returns.

For each type of signal transition (e.g., VÄNTA→STARK, Sidled→Upptrend):
  - Counts how many times it occurred
  - Measures how long the new signal lasted before changing again (median, avg, 75th pct)
  - Measures forward returns: avg price change 5/10/20/60 days after transition
  - Computes win rate at 20-day horizon
  - Breakdowns by sector

Stores results in signal_persistence_cache for API consumption.

Schedule: weekly (Sundays) after score_tracker has run.

Usage:
    python -m marketscan.backend_worker.signal_analytics
"""
import os
import json
import logging
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _forward_return(
    cur,
    ticker: str,
    from_date: date,
    days: int,
) -> float | None:
    """Price return N days after from_date using score_history.price."""
    target_date = from_date + timedelta(days=days)

    # Find closest available date at or after target
    cur.execute("""
        SELECT price FROM score_history
        WHERE ticker = %s AND scan_date BETWEEN %s AND %s AND price IS NOT NULL
        ORDER BY scan_date ASC LIMIT 1
    """, (ticker, target_date.isoformat(), (target_date + timedelta(days=14)).isoformat()))
    after = cur.fetchone()

    # Price at transition date
    cur.execute("""
        SELECT price FROM score_history
        WHERE ticker = %s AND scan_date = %s AND price IS NOT NULL
    """, (ticker, from_date.isoformat()))
    at_date = cur.fetchone()

    if not after or not at_date or not at_date[0] or not after[0]:
        return None

    try:
        return (float(after[0]) - float(at_date[0])) / float(at_date[0])
    except (ZeroDivisionError, TypeError):
        return None


def _signal_duration(
    cur,
    ticker: str,
    field: str,
    signal_value: str,
    from_date: date,
    max_days: int = 365,
) -> int | None:
    """Days until signal changes again after from_date."""
    end_date = from_date + timedelta(days=max_days)

    cur.execute("""
        SELECT scan_date FROM score_history
        WHERE ticker = %s
          AND scan_date > %s AND scan_date <= %s
          AND %s != %s
        ORDER BY scan_date ASC LIMIT 1
    """, (ticker, from_date.isoformat(), end_date.isoformat(), field, signal_value))
    # Note: PostgreSQL can't use Python identifier substitution for column names
    # We need to build the query differently

    # Retry with dynamic column reference
    if field == "entry_signal":
        cur.execute("""
            SELECT scan_date FROM score_history
            WHERE ticker = %s
              AND scan_date > %s AND scan_date <= %s
              AND (entry_signal IS DISTINCT FROM %s OR entry_signal IS NULL)
            ORDER BY scan_date ASC LIMIT 1
        """, (ticker, from_date.isoformat(), end_date.isoformat(), signal_value))
    else:
        cur.execute("""
            SELECT scan_date FROM score_history
            WHERE ticker = %s
              AND scan_date > %s AND scan_date <= %s
              AND (trend_signal IS DISTINCT FROM %s OR trend_signal IS NULL)
            ORDER BY scan_date ASC LIMIT 1
        """, (ticker, from_date.isoformat(), end_date.isoformat(), signal_value))

    row = cur.fetchone()
    if not row:
        return None  # Still holding (censored)

    change_date = row[0]
    if isinstance(change_date, str):
        from datetime import date as dt
        change_date = dt.fromisoformat(change_date)

    return (change_date - from_date).days


def compute_signal_analytics(dsn: str) -> int:
    """Compute and cache signal persistence analytics. Returns number of combinations processed."""
    processed = 0

    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Load all signal transitions
        cur.execute("""
            SELECT t.ticker, t.transition_date, t.field,
                   t.from_value, t.to_value, t.price_at,
                   sr.sector
            FROM signal_transitions t
            LEFT JOIN scan_results sr ON sr.ticker = t.ticker
            ORDER BY t.field, t.from_value, t.to_value, t.transition_date
        """)
        all_transitions = cur.fetchall()

    if not all_transitions:
        logger.warning("No signal transitions found — run score_tracker first")
        return 0

    logger.info("Analysing %d signal transitions", len(all_transitions))

    # Group by (field, from_value, to_value)
    groups: dict[tuple, list] = {}
    for t in all_transitions:
        key = (t["field"], t["from_value"], t["to_value"])
        if key not in groups:
            groups[key] = []
        groups[key].append(t)

    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        for (field, from_v, to_v), transitions in groups.items():
            if len(transitions) < 3:
                continue  # Not enough samples for meaningful statistics

            durations   = []
            ret_5d      = []
            ret_10d     = []
            ret_20d     = []
            ret_60d     = []
            sector_rets: dict[str, list[float]] = {}

            for t in transitions:
                ticker   = t["ticker"]
                t_date   = t["transition_date"]
                if isinstance(t_date, str):
                    from datetime import date as dt
                    t_date = dt.fromisoformat(t_date)
                sector = t.get("sector") or "Övrigt"

                # Duration until signal changes again
                dur = _signal_duration(cur, ticker, field, to_v, t_date)
                if dur is not None:
                    durations.append(dur)

                # Forward returns
                for days_ahead, ret_list in [
                    (5, ret_5d), (10, ret_10d), (20, ret_20d), (60, ret_60d)
                ]:
                    r = _forward_return(cur, ticker, t_date, days_ahead)
                    if r is not None:
                        ret_list.append(r)
                        if days_ahead == 20:
                            if sector not in sector_rets:
                                sector_rets[sector] = []
                            sector_rets[sector].append(r)

            # Compute stats
            dur_arr = np.array(durations) if durations else np.array([])
            median_dur = float(np.median(dur_arr)) if len(dur_arr) > 0 else None
            avg_dur    = float(np.mean(dur_arr))   if len(dur_arr) > 0 else None
            pct75_dur  = float(np.percentile(dur_arr, 75)) if len(dur_arr) > 0 else None

            avg_r5  = float(np.mean(ret_5d))  if ret_5d  else None
            avg_r10 = float(np.mean(ret_10d)) if ret_10d else None
            avg_r20 = float(np.mean(ret_20d)) if ret_20d else None
            avg_r60 = float(np.mean(ret_60d)) if ret_60d else None

            win_rate_20 = (
                round(float(np.mean([r > 0 for r in ret_20d]) * 100), 2)
                if ret_20d else None
            )

            sector_breakdown = {
                s: round(float(np.mean(rets)) * 100, 2)
                for s, rets in sector_rets.items()
                if rets
            }

            # Upsert into cache
            cur_plain = conn.cursor()
            cur_plain.execute("""
                INSERT INTO signal_persistence_cache (
                    field, from_signal, to_signal, sample_count,
                    median_hold_days, avg_hold_days, pct75_hold_days,
                    avg_return_5d, avg_return_10d, avg_return_20d, avg_return_60d,
                    win_rate_20d, sector_breakdown, computed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (field, from_signal, to_signal) DO UPDATE SET
                    sample_count = EXCLUDED.sample_count,
                    median_hold_days = EXCLUDED.median_hold_days,
                    avg_hold_days = EXCLUDED.avg_hold_days,
                    pct75_hold_days = EXCLUDED.pct75_hold_days,
                    avg_return_5d = EXCLUDED.avg_return_5d,
                    avg_return_10d = EXCLUDED.avg_return_10d,
                    avg_return_20d = EXCLUDED.avg_return_20d,
                    avg_return_60d = EXCLUDED.avg_return_60d,
                    win_rate_20d = EXCLUDED.win_rate_20d,
                    sector_breakdown = EXCLUDED.sector_breakdown,
                    computed_at = NOW()
            """, (
                field, str(from_v or ""), str(to_v or ""),
                len(transitions),
                round(median_dur, 1) if median_dur else None,
                round(avg_dur, 1)    if avg_dur else None,
                round(pct75_dur, 1)  if pct75_dur else None,
                round(avg_r5  * 100, 4) if avg_r5  is not None else None,
                round(avg_r10 * 100, 4) if avg_r10 is not None else None,
                round(avg_r20 * 100, 4) if avg_r20 is not None else None,
                round(avg_r60 * 100, 4) if avg_r60 is not None else None,
                win_rate_20,
                json.dumps(sector_breakdown),
            ))
            conn.commit()

            processed += 1
            logger.info(
                "  %s: %s→%s: n=%d, avg_dur=%.0f days, avg_ret_20d=%.2f%%",
                field, from_v, to_v, len(transitions),
                avg_dur or 0, (avg_r20 or 0) * 100,
            )

    logger.info("Signal analytics complete: %d transition combinations processed", processed)
    return processed


if __name__ == "__main__":
    dsn = os.environ["DATABASE_URL"]
    compute_signal_analytics(dsn)
