"""
insider_cluster.py — Klusterscoring för insider-signaler.

Beräknar per ticker (rullande 30 dagar) ur insider_trades:
  cluster_score = unique_buyers_30d × log1p(buy_amount/market_cap) × exec_weight

Akademisk grund: kluster av samtidiga insiderköp är den persistenta signalen,
enskilda trades har bara 2-5 dagars fönster.

Användning:
    python -m backend_worker.insider_cluster
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Exec-roller som ger högre vikt
_EXEC_TITLES = [
    "vd", "verkställande direktör", "ceo", "chief executive officer",
    "cfo", "chief financial officer",
    "ordförande", "styrelseordförande", "chairman",
    "styrelseledamot", "board member",
]


def calculate_clusters(conn, lookback_days: int = 30) -> pd.DataFrame:
    """Beräkna klustersignaler för alla tickers med insider-trades.

    Routine-trades (samma person, samma månad, samma belopp) filtreras bort
    eftersom de inte ger signalvärde — cluster-signalen kommer från ovanliga/opportunistiska köp.

    Returns:
        DataFrame med kolumner: ticker, unique_buyers_30d, total_buy_amount_30d,
        cluster_score, is_cluster, exec_buy_90d
    """
    cutoff_30d = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    cutoff_90d = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    # Alla köp senaste 90 dagar (för routine-filter + exec-detektion)
    query_90d = f"""
        SELECT ticker, name, role, shares, price, amount, trade_date
        FROM insider_trades
        WHERE type = 'buy'
          AND trade_date >= '{cutoff_90d}'
        ORDER BY ticker, trade_date
    """
    all_buys_90d = pd.read_sql(query_90d, conn)

    if all_buys_90d.empty:
        logger.info("Inga insiderköp senaste %d dagar", lookback_days)
        return pd.DataFrame()

    # Hämta historik för routine-detektion (alla buys)
    query_all = """
        SELECT ticker, name, trade_date, shares, price
        FROM insider_trades
        WHERE type = 'buy'
        ORDER BY ticker, name, trade_date
    """
    history_df = pd.read_sql(query_all, conn)

    # Filtrera routine-traders: samma person+ticker som handlar samma månad varje år
    # eller alltid samma belopp (±20%)
    def _is_routine(ticker: str, name: str, trade_date: str, shares: float, price: float) -> bool:
        """Kontrollera om en trade är routine (samma person, samma mönster)."""
        if not name:
            return False
        person_hist = history_df[
            (history_df["ticker"] == ticker) &
            (history_df["name"].str.lower().fillna("").str.strip() == name.lower().strip())
        ]
        if len(person_hist) < 3:
            return False

        current_month = str(trade_date)[:7] if pd.notna(trade_date) else ""

        # 1. Samma månad varje år?
        prev_months = [str(d)[:7] for d in person_hist["trade_date"].iloc[:-1] if pd.notna(d)]
        if prev_months:
            unique_prev = set(prev_months[-4:])
            if len(unique_prev) == 1 and current_month and list(unique_prev)[0] == current_month:
                return True

        # 2. Samma belopp ±20%?
        current_val = float(shares or 0) * float(price or 1)
        if current_val <= 0:
            return False
        prev_vals = []
        for _, row in person_hist.iterrows():
            s = float(row.get("shares", 0) or 0)
            p = float(row.get("price", 0) or 1)
            if s > 0 and p > 0:
                prev_vals.append(s * p)
        if len(prev_vals) >= 3:
            avg_val = sum(prev_vals[:-1]) / len(prev_vals[:-1]) if len(prev_vals) > 1 else prev_vals[0]
            if avg_val > 0 and 0.8 <= (current_val / avg_val) <= 1.2:
                return True
        return False

    # Apply routine filter
    routine_mask = all_buys_90d.apply(
        lambda r: _is_routine(
            r["ticker"], r.get("name", ""),
            r.get("trade_date", ""),
            r.get("shares", 0), r.get("price", 0),
        ),
        axis=1,
    )
    opportunistic_buys = all_buys_90d[~routine_mask].copy()
    n_routine = routine_mask.sum()
    if n_routine > 0:
        logger.info("Filtrerade bort %d routine-trades", n_routine)

    # Separera 30d och 90d efter filtrering
    buys_30d = opportunistic_buys[opportunistic_buys["trade_date"] >= cutoff_30d].copy()
    buys_90d_filtered = opportunistic_buys.copy()

    # Market cap från scan_results
    try:
        mcap_query = "SELECT ticker, market_cap FROM scan_results WHERE market_cap > 0"
        mcap_data = pd.read_sql(mcap_query, conn)
        mcap_map = dict(zip(mcap_data["ticker"], mcap_data["market_cap"]))
    except Exception:
        mcap_map = {}

    if buys_30d.empty:
        logger.info("Inga insiderköp senaste %d dagar", lookback_days)
        return pd.DataFrame()

    # Räkna unika köpare per ticker
    ticker_buyers = (
        buys_30d.groupby("ticker")["name"]
        .nunique()
        .reset_index()
        .rename(columns={"name": "unique_buyers_30d"})
    )

    # Totalt köpbelopp per ticker
    ticker_amount = (
        buys_30d.groupby("ticker")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total_buy_amount_30d"})
    )

    # Exec-vikt: 1.5 om VD/CFO/ordförande bland köparna senaste 30d
    def _has_exec(trades_for_ticker):
        roles = trades_for_ticker["role"].str.lower().fillna("")
        return any(
            any(title in role for title in _EXEC_TITLES)
            for role in roles
        )

    exec_buyers_30d = buys_30d.groupby("ticker").apply(_has_exec).reset_index()
    exec_buyers_30d.columns = ["ticker", "has_exec_30d"]

    # Exec-flagga 90d (använd filtered data)
    if not buys_90d_filtered.empty:
        exec_buyers_90d = buys_90d_filtered.groupby("ticker").apply(_has_exec).reset_index()
        exec_buyers_90d.columns = ["ticker", "has_exec_90d"]
    else:
        exec_buyers_90d = pd.DataFrame({"ticker": [], "has_exec_90d": []})

    # Slå ihop
    clusters = ticker_buyers.merge(ticker_amount, on="ticker", how="left")
    clusters = clusters.merge(exec_buyers_30d, on="ticker", how="left")
    clusters = clusters.merge(exec_buyers_90d, on="ticker", how="left")
    clusters["has_exec_30d"] = clusters["has_exec_30d"].fillna(False)
    clusters["has_exec_90d"] = clusters["has_exec_90d"].fillna(False)

    # Beräkna cluster_score
    def _score(row):
        n_buyers = row["unique_buyers_30d"]
        amount = row["total_buy_amount_30d"]
        ticker = row["ticker"]

        mc = mcap_map.get(ticker, 1)
        if mc <= 0:
            mc = 1

        amount_ratio = amount / mc
        log_amount = np.log1p(max(amount_ratio, 0))

        exec_weight = 1.5 if row["has_exec_30d"] else 1.0

        return n_buyers * log_amount * exec_weight

    clusters["cluster_score"] = clusters.apply(_score, axis=1).round(4)
    clusters["is_cluster"] = clusters["unique_buyers_30d"] >= 3
    clusters["exec_buy_90d"] = clusters["has_exec_90d"]

    # Sortera
    clusters = clusters.sort_values("cluster_score", ascending=False).reset_index(drop=True)

    logger.info("Klusteranalys: %d tickers, %d med kluster (≥3 köpare)",
                len(clusters), clusters["is_cluster"].sum())
    return clusters


def upsert_clusters(clusters: pd.DataFrame, conn):
    """Upsert cluster-signaler till insider_cluster_signals-tabellen."""
    if clusters.empty:
        logger.info("Inga kluster att upsert")
        return

    cur = conn.cursor()

    for _, row in clusters.iterrows():
        try:
            cur.execute("""
                INSERT INTO insider_cluster_signals
                    (ticker, unique_buyers_30d, total_buy_amount_30d,
                     cluster_score, is_cluster, exec_buy_90d, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ticker) DO UPDATE SET
                    unique_buyers_30d = EXCLUDED.unique_buyers_30d,
                    total_buy_amount_30d = EXCLUDED.total_buy_amount_30d,
                    cluster_score = EXCLUDED.cluster_score,
                    is_cluster = EXCLUDED.is_cluster,
                    exec_buy_90d = EXCLUDED.exec_buy_90d,
                    updated_at = NOW()
            """, (
                row["ticker"],
                int(row["unique_buyers_30d"]),
                float(row.get("total_buy_amount_30d", 0)),
                float(row.get("cluster_score", 0)),
                bool(row.get("is_cluster", False)),
                bool(row.get("exec_buy_90d", False)),
            ))
        except Exception as e:
            logger.warning("Upsert failed for %s: %s", row.get("ticker"), e)

    conn.commit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable required")
        sys.exit(1)

    import psycopg2
    conn = psycopg2.connect(database_url)

    clusters = calculate_clusters(conn)

    if not clusters.empty:
        # Visa topp-10
        print("\nTopp-10 insiderkluster:")
        for _, r in clusters.head(10).iterrows():
            print(f"  {r['ticker']:<10} {int(r['unique_buyers_30d'])} köpare, "
                  f"score={r['cluster_score']:.2f}, "
                  f"kluster={'✅' if r['is_cluster'] else '—'}, "
                  f"exec={'✅' if r['exec_buy_90d'] else '—'}")

    upsert_clusters(clusters, conn)
    conn.close()

    result = {
        "status": "ok",
        "tickers_analyzed": len(clusters),
        "clusters_found": int(clusters["is_cluster"].sum()) if not clusters.empty else 0,
    }
    print(json.dumps(result))
    logger.info("Insider cluster scoring klar")


if __name__ == "__main__":
    main()
