"""
watchlist_alerts.py — Personliga notiser på din watchlist/portfölj (Spec 09 + #20).
=================================================================================

För varje användare: snitta watchlist + portföljinnehav mot dagens triggers och skapa
in-app-notiser (+ e-post för viktiga). Triggers:
  - Ny STARK-signal (signal_transitions)
  - Score-rörelse över tröskel (score_history)
  - Nytt insiderkluster (insider_cluster_signals, diff vs föregående = Insider Flash)
  - Ny MEWS-flagga (scan_results.mews_flag, diff vs föregående)
  - Nytt earnings-memo (earnings_memos)

Dedup via triggered_alerts (samma user+ticker+typ inte på nytt inom 3 dagar).
Diff-state för insider/MEWS lagras i worker_state.

Körs nattligt (GitHub Actions), efter pipeline + fi_insider.
Anrop:
    python -m backend_worker.watchlist_alerts
    python -m backend_worker.watchlist_alerts --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Default-inställningar om en user saknar rad i notification_prefs
_DEFAULT_PREFS = {
    "on_new_stark": True, "on_score_move": True, "on_insider_cluster": True,
    "on_mews_flag": True, "on_earnings_memo": True,
    "score_move_threshold": 15, "email_enabled": False,
}

# Vilka triggers är "viktiga" nog för e-post
_EMAIL_TRIGGERS = {"insider_cluster", "new_stark"}

# Notistyp (notifications.type CHECK-värden) per trigger
_NOTIF_TYPE = {
    "new_stark": "system", "score_move": "score_change",
    "insider_cluster": "insider", "mews_flag": "system", "earnings_memo": "earnings",
}


def _load_worker_state(cur, key: str) -> set[str]:
    cur.execute("SELECT value FROM worker_state WHERE key = %s", (key,))
    row = cur.fetchone()
    if row and isinstance(row[0], dict):
        return set(row[0].get("tickers", []))
    return set()


def _save_worker_state(cur, key: str, tickers: set[str]):
    cur.execute(
        """INSERT INTO worker_state (key, value, updated_at)
           VALUES (%s, %s, NOW())
           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()""",
        (key, json.dumps({"tickers": sorted(tickers)})),
    )


def run_watchlist_alerts(dsn: str, dry_run: bool = False) -> dict:
    stats = {"users": 0, "notifications": 0, "emails": 0, "errors": 0}
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            # ── 1. user → tickers (watchlist ∪ holdings) ─────────────────────
            cur.execute("""
                SELECT user_id, ticker FROM watchlist
                UNION
                SELECT p.user_id, h.ticker
                FROM holdings h JOIN portfolios p ON p.id = h.portfolio_id
            """)
            user_tickers: dict[str, set[str]] = {}
            for uid, tk in cur.fetchall():
                user_tickers.setdefault(str(uid), set()).add(tk)
            if not user_tickers:
                logger.info("Inga users med watchlist/portfölj — klart.")
                return stats

            # ── 2. prefs per user ────────────────────────────────────────────
            cur.execute("SELECT * FROM notification_prefs")
            cols = [d[0] for d in cur.description]
            prefs: dict[str, dict] = {}
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                prefs[str(d["user_id"])] = d

            # ── 3. dagens trigger-set (cross-user) ───────────────────────────
            triggers: dict[str, dict] = {}  # trigger_type -> {ticker: detail}

            def _safe(label, fn):
                try:
                    triggers[label] = fn()
                except Exception as e:  # noqa: BLE001
                    logger.warning("Trigger %s misslyckades: %s", label, e)
                    triggers[label] = {}

            # new_stark
            def _new_stark():
                cur.execute("""SELECT ticker FROM signal_transitions
                               WHERE transition_date = CURRENT_DATE
                                 AND field = 'entry_signal' AND to_value = 'STARK'""")
                return {t[0]: "Ny STARK-signal" for t in cur.fetchall()}
            _safe("new_stark", _new_stark)

            # score_move (delta mellan senaste två scan_date per ticker)
            def _score_move():
                cur.execute("""SELECT ticker, score_total, scan_date FROM score_history
                               WHERE scan_date >= CURRENT_DATE - INTERVAL '10 days'
                                 AND score_total IS NOT NULL
                               ORDER BY ticker, scan_date DESC""")
                latest: dict[str, list] = {}
                for tk, sc, _d in cur.fetchall():
                    latest.setdefault(tk, []).append(float(sc))
                out = {}
                for tk, vals in latest.items():
                    if len(vals) >= 2:
                        delta = vals[0] - vals[1]
                        if abs(delta) >= 1:
                            out[tk] = round(delta, 1)
                return out  # ticker -> delta (filtreras per user-tröskel senare)
            _safe("score_move", _score_move)

            # insider_cluster (diff vs föregående = flash)
            def _insider():
                cur.execute("SELECT ticker, unique_buyers_30d FROM insider_cluster_signals WHERE is_cluster = TRUE")
                cur_set = {t[0]: f"Insiderkluster ({t[1]} köpare)" for t in cur.fetchall()}
                prev = _load_worker_state(cur, "seen_insider_clusters")
                if not dry_run:
                    _save_worker_state(cur, "seen_insider_clusters", set(cur_set.keys()))
                return {tk: d for tk, d in cur_set.items() if tk not in prev}  # bara NYA
            _safe("insider_cluster", _insider)

            # mews_flag (diff vs föregående)
            def _mews():
                cur.execute("SELECT ticker FROM scan_results WHERE mews_flag = TRUE")
                cur_set = {t[0] for t in cur.fetchall()}
                prev = _load_worker_state(cur, "seen_mews_flags")
                if not dry_run:
                    _save_worker_state(cur, "seen_mews_flags", cur_set)
                return {tk: "Ny mångdubblar-flagga" for tk in cur_set if tk not in prev}
            _safe("mews_flag", _mews)

            # earnings_memo (dagens)
            def _memo():
                cur.execute("SELECT ticker FROM earnings_memos WHERE created_at::date = CURRENT_DATE")
                return {t[0]: "Ny rapportanalys" for t in cur.fetchall()}
            _safe("earnings_memo", _memo)

            # ── 4. redan triggat (dedup, 3 dagar) ────────────────────────────
            cur.execute("""SELECT user_id, ticker, rule_type FROM triggered_alerts
                           WHERE triggered_at >= CURRENT_DATE - INTERVAL '3 days'""")
            seen = {(str(u), tk, rt) for u, tk, rt in cur.fetchall()}

            # ── 5. matcha per user ───────────────────────────────────────────
            notif_rows = []          # (user_id, type, title, body, link)
            trig_rows = []           # (user_id, rule_name, rule_type, ticker, detail)
            email_jobs = []          # (user_id, ticker, reason)

            for uid, tickers in user_tickers.items():
                p = prefs.get(uid, _DEFAULT_PREFS)
                threshold = p.get("score_move_threshold", 15) or 15
                stats["users"] += 1

                for ttype, tickmap in triggers.items():
                    pref_key = f"on_{ttype}"
                    if not p.get(pref_key, True):
                        continue
                    for tk, detail in tickmap.items():
                        if tk not in tickers:
                            continue
                        if ttype == "score_move" and abs(detail) < threshold:
                            continue
                        if (uid, tk, ttype) in seen:
                            continue
                        seen.add((uid, tk, ttype))
                        detail_str = (f"{tk}: betyg {'+' if detail >= 0 else ''}{detail} p"
                                      if ttype == "score_move" else f"{tk}: {detail}")
                        title = {
                            "new_stark": f"{tk} fick STARK-signal",
                            "score_move": f"{tk} betygsrörelse",
                            "insider_cluster": f"Insiderkluster i {tk}",
                            "mews_flag": f"{tk} flaggad som mångdubblar-kandidat",
                            "earnings_memo": f"Ny rapportanalys för {tk}",
                        }[ttype]
                        notif_rows.append((uid, _NOTIF_TYPE[ttype], title, detail_str, f"/aktie/{tk}"))
                        trig_rows.append((uid, f"Watchlist: {ttype}", ttype, tk, detail_str))
                        if ttype in _EMAIL_TRIGGERS and p.get("email_enabled"):
                            email_jobs.append((uid, tk, title))

            # ── 6. skriv ─────────────────────────────────────────────────────
            if dry_run:
                logger.info("[DRY-RUN] %d notiser, %d e-post (skriver inte)", len(notif_rows), len(email_jobs))
            else:
                if notif_rows:
                    execute_values(cur,
                        "INSERT INTO notifications (user_id, type, title, body, link) VALUES %s",
                        notif_rows)
                if trig_rows:
                    execute_values(cur,
                        "INSERT INTO triggered_alerts (user_id, rule_name, rule_type, ticker, detail) VALUES %s",
                        trig_rows)
                conn.commit()
            stats["notifications"] = len(notif_rows)

            # ── 7. e-post (efter commit) ─────────────────────────────────────
            if email_jobs and not dry_run:
                stats["emails"] = _send_emails(cur, email_jobs)
                conn.commit()

    except Exception as e:  # noqa: BLE001
        logger.error("watchlist_alerts misslyckades: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        stats["errors"] += 1
    finally:
        conn.close()
    return stats


def _send_emails(cur, jobs: list[tuple]) -> int:
    """Skicka e-post för viktiga triggers (om mall + Resend finns)."""
    try:
        from backend_worker.email.sender import send_notification
    except Exception:
        return 0
    sent = 0
    # Hämta e-post per user via auth.users (service_role)
    uids = list({j[0] for j in jobs})
    cur.execute("SELECT id, email FROM auth.users WHERE id = ANY(%s)", (uids,))
    emails = {str(u): e for u, e in cur.fetchall()}
    for uid, tk, reason in jobs:
        to = emails.get(uid)
        if not to:
            continue
        try:
            if send_notification(to, "watchlist_alert", ticker=tk, reason=reason):
                sent += 1
        except Exception as e:  # noqa: BLE001
            logger.debug("E-post misslyckades för %s: %s", tk, e)
    return sent


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL saknas")
        sys.exit(1)
    result = run_watchlist_alerts(dsn, dry_run=args.dry_run)
    print(json.dumps(result))
    logger.info("Klart: %s", result)
