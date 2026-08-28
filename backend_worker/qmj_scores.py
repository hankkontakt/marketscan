"""
qmj_scores.py — QMJ-komposit (evidensbaserad kvalitetsscreening) för Norden.

Evidensgrund:
  - Heggli & Haugland (NTNU 2025, vinnare NTNU:s masteruppsatspris): kvalitet ger
    persistent premie som VÄXER när storleken minskar (80-90 bps/mån, mikro/small).
  - Asness, Frazzini, Pedersen (2019, Review of Accounting Studies): QMJ i 23/24 länder.
  - Arcada 2020: ROIC-top-10 % ger signifikant alpha med ÅRLIG rebalansering.
  - OBS: akademiska siffror är GROSS; förvänta +1-3 %/år netto i praktiken.

Data-regler (per granskning):
  - ALDRIG .info-derivativa nyckeltal (Tokmanni-fallet: d2e=404 i .info).
  - Punkt-i-tid: annual data giltig från (fy_end + 5 mån) — as_of_date lagras.
  - Saknad data → neutral 50, ALDRIG 0. Grupp n<20 → hela-universum-rank.
  - Hårda filter: short ≥8 % eller ny-disclosure <90 d → alpha_rank NULL.
  - Årlig ledviktning (april) — spredd ~1 %/sida gör annan frekvens ohållbar.

Användning:
    python -m backend_worker.qmj_scores --dry-run --limit-tickers 5
    python -m backend_worker.qmj_scores --limit-tickers 120
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "qmj_raw"
CACHE_MAX_AGE_DAYS = 7
FETCH_SLEEP = 1.2

WEIGHTS = {"quality": 0.40, "momentum": 0.25, "insider": 0.15, "value": 0.10, "payout": 0.10}
SHORT_EXCLUDE_PCT = 8.0
NEW_DISCLOSURE_DAYS = 90
LIQUIDITY_WARN_LOCAL = 1_000_000.0    # ≈1 Mkr daglig omsättning (lokala valutor, grov)
AS_OF_ADD_MONTHS = 5
MIN_GROUP_SIZE = 20
SIZE_GROUPS = [(50e6, 300e6), (300e6, 1.5e9), (1.5e9, 5e9)]   # lokala valutor, grov SEK-ekvivalens


# ═════════════════════════ PURE CORE (testbar; ingen nätverk/DB) ══════════════

def pick(row: dict, *keys):
    for k in keys:
        v = row.get(k)
        if v is not None and (not isinstance(v, float) or not math.isnan(v)):
            return v
    return None


def fy_age_fit(fy_dates: list, today: date) -> tuple[Optional[date], bool]:
    """Validera annual-kolumner (≥3 st, avstånd 365±40 d). (senaste fy, suspect).

    Kolumnordning kan vara fallande (yfinance) — sortera internt.
    """
    if len(fy_dates) < 3:
        return None, True
    ds = sorted(fy_dates)
    spans = [(b - a).days for a, b in zip(ds, ds[1:])]
    if any(abs(s - 365) > 40 for s in spans):
        return None, True
    return ds[-1], False


def as_of_strict(fy_end: date, today: date) -> bool:
    """Annual data giltig först från fy_end + 5 månader (rapporteringsrealitet)."""
    d = date(fy_end.year, fy_end.month, fy_end.day)
    for _ in range(AS_OF_ADD_MONTHS):
        m, y = d.month + 1, d.year
        if m > 12:
            m, y = 1, y + 1
        d = date(y, m, min(d.day, 28))
    return d <= today


def bucket_mcap(mcap_local: float) -> int:
    """0=50-300M, 1=300M-1.5B, 2=1.5B-5B, 3=utanför/okänd."""
    if mcap_local is None or mcap_local <= 0 or not math.isfinite(mcap_local):
        return 3
    for i, (lo, hi) in enumerate(SIZE_GROUPS):
        if lo <= mcap_local < hi:
            return i
    return 3


def rank_pct(values: dict) -> dict:
    """Rank-percentil 0-100 (högt = bättre). N<3 → 50.0-neutralitet."""
    if not values:
        return {}
    items = {k: v for k, v in values.items() if v is not None and math.isfinite(float(v))}
    if len(items) < 3:
        return {k: 50.0 for k in values}
    sv = sorted(items.values())
    n = len(sv)

    def pct(v: float) -> float:
        lo = sum(1 for s in sv if s < v)
        eq = sum(1 for s in sv if s == v)
        return round(100.0 * (lo + 0.5 * eq) / n, 2)

    return {k: pct(v) for k, v in items.items()}


def composite(q=None, m=None, v=None, p=None, i=None) -> float:
    """Viktad komposit (percentiler 0-100, neutral=50)."""
    return round(
        WEIGHTS["quality"] * (q if q is not None else 50)
        + WEIGHTS["momentum"] * (m if m is not None else 50)
        + WEIGHTS["value"] * (v if v is not None else 50)
        + WEIGHTS["payout"] * (p if p is not None else 50)
        + WEIGHTS["insider"] * (i if i is not None else 50),
        2,
    )


def short_exclusion(total_short_pct: Optional[float], new_disc_within_90d: bool) -> Optional[str]:
    if total_short_pct is None:
        return None
    if total_short_pct >= SHORT_EXCLUDE_PCT:
        return f"short_high({total_short_pct:.1f}%)"
    if new_disc_within_90d:
        return "short_new_disclosure"
    return None


def _row_val(df: pd.DataFrame, latest_col, *keys) -> Optional[float]:
    for k in keys:
        if k in df.index:
            try:
                v = df.loc[k, latest_col]
                if pd.notna(v):
                    return float(v)
            except Exception:
                continue
    return None


def model_periods(df: pd.DataFrame) -> list:
    """Kolumnnamn → datum, sorterade. [] om ej tolkbara."""
    out = []
    for c in df.columns:
        try:
            out.append(pd.to_datetime(c).date())
        except Exception:
            continue
    return out


def extract_metrics(fin: pd.DataFrame, bal: pd.DataFrame, cash: pd.DataFrame,
                    price: Optional[float], hist_returns: list) -> dict:
    """Extrahera QMJ-metrik ur RÅA bokslut (yfinance-format: index=items, kolumner=perioder).

    Saknade värden → None (caller ger neutral 50). "data_quality": ok|partial.
    """
    out: dict = {"data_quality": "partial"}
    if fin is None or bal is None or cash is None or fin.empty or bal.empty:
        return out
    try:
        fy_dates = model_periods(fin)
        if len(fy_dates) != len(fin.columns):
            return out
        fy_last, suspect = fy_age_fit(fy_dates, date.today())
        if fy_last is None:
            out["fy_end"] = None
            return out
        latest = fy_last.isoformat()   # kolumner kan vara fallande — använd sorterat max

        def bval(*keys):
            return _row_val(bal, latest, *keys)

        def fval(*keys):
            return _row_val(fin, latest, *keys)

        def cval(*keys):
            return _row_val(cash, latest, *keys)

        ni = fval("Net Income")
        ebit = fval("Operating Income", "EBIT")
        gp = fval("Gross Profit")
        ocf = cval("Operating Cash Flow", "Net Cash Provided By Operating Activities", "Net Cash Provided by Operating Activities")
        capex = cval("Capital Expenditure", "CapEx", "Capital Expenditures")
        d_a = cval("Depreciation And Amortization", "Depreciation And Amortisation", "Depreciation Amortization And Other")
        ta = bval("Total Assets")
        tl = bval("Total Liabilities Net Minority Interest", "Total Liabilities")
        eq = bval("Stockholders Equity", "Common Stock Equity", "Total Stockholder Equity")
        debt = bval("Total Debt")
        cash_bal = bval("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
        interest = fval("Interest Expense")

        # Aktieantal: tidig vs sen (≥3 års data, sorterat på period) → netto-utgivning
        shares_series = []
        if "Ordinary Shares Number" in bal.index:
            for c in sorted(bal.columns, key=lambda x: str(x)):
                try:
                    if _to_date(c):
                        v = bal.loc["Ordinary Shares Number", c]
                        if pd.notna(v):
                            shares_series.append(float(v))
                except Exception:
                    continue
        shares_latest = shares_series[-1] if shares_series else None
        shares_prev = shares_series[0] if len(shares_series) >= 3 else None
        issuance = None
        if shares_latest and shares_prev and shares_prev > 0 and shares_latest > 0:
            yrs = max(len(shares_series) - 1, 1)
            issuance = float((shares_latest / shares_prev) ** (1 / yrs) - 1)

        # ROE-statistik över perioderna (min 2 obs)
        roe_series = []
        eq_row = None
        if "Stockholders Equity" in bal.index:
            eq_row = "Stockholders Equity"
        elif "Common Stock Equity" in bal.index:
            eq_row = "Common Stock Equity"
        if eq_row and "Net Income" in fin.index:
            for c in fin.columns:
                try:
                    n = fin.loc["Net Income", c]
                    e = bal.loc[eq_row, c] if eq_row in bal.index else None
                    if pd.notna(n) and e and pd.notna(e) and float(e) != 0:
                        roe_series.append(float(n) / float(e))
                except Exception:
                    continue

        mcap = (price * shares_latest) if (price and shares_latest) else None
        # OBS: yfinance-rapporterar i ABSOLUTA enheter (t.ex. -11388000 = -11,4 Mkr)
        # och mcap = pris × aktieantal är också absolut → alla ratioer utan omvandling.
        ebitda = (ebit + d_a) if (ebit is not None and d_a is not None) else ebit
        ndebt = (debt - cash_bal) if (debt is not None and cash_bal is not None) else debt
        fcf = (ocf + capex) if (ocf is not None and capex is not None) else ocf

        out.update({
            "roe": (ni / eq) if (ni is not None and eq and eq != 0) else None,
            "roa": (ebit / ta) if (ebit is not None and ta and ta != 0) else None,
            "gmar": (gp / ta) if (gp is not None and ta and ta != 0) else None,
            "cfoa": (ocf / ta) if (ocf is not None and ta and ta != 0) else None,
            "accruals": ((ni - ocf) / ta) if (ni is not None and ocf is not None and ta and ta != 0) else None,
            "leverage": (tl / eq) if (tl is not None and eq and eq != 0) else None,
            "ndebt_ebitda": (ndebt / ebitda) if (ndebt is not None and ebitda and ebitda != 0) else None,
            "intcov": (ebit / interest) if (ebit is not None and interest and interest != 0) else None,
            "roe_vol": float(np.std(roe_series)) if len(roe_series) >= 2 else None,
            "issuance": issuance,
            "ev_ebitda": None,
            "fcf_yield": None,
            "mcap_local": mcap,
            "fy_end": fy_last.isoformat(),
            "suspect": suspect,
        })
        if mcap is not None and ndebt is not None and ebitda and ebitda != 0:
            ev = float((mcap + ndebt) / ebitda)
            out["ev_ebitda"] = ev if abs(ev) <= 500 else None   # absurd multipla → saknad
        if fcf is not None and mcap and mcap > 0:
            fy = float(fcf / mcap)
            out["fcf_yield"] = fy if abs(fy) <= 1.0 else None   # >100 % yield = datafel

        # Volatilitet + momentum 12-1 (vol-skalad) ur prishistoriken
        vr = np.array(hist_returns) if hist_returns else np.array([])
        out["vol_ann"] = float(np.std(vr) * math.sqrt(252)) if (len(vr) >= 20 and float(np.std(vr)) > 0) else None
        mom, mom_scaled = None, None
        if len(vr) >= 240:   # ~12 månader minus senaste månad (tillåter 1–2 saknade sessioner)
            cum = (1 + pd.Series(np.array(vr))).cumprod()
            try:
                p1, p2 = cum.iloc[-22], cum.iloc[-240]
                if p1 and p2 and p2 > 0:
                    mom = float(p1 / p2 - 1)
                    if out.get("vol_ann"):
                        mom_scaled = float(mom / out["vol_ann"])
            except Exception:
                pass
        out["momentum_raw"] = mom
        out["momentum_vol_scaled"] = mom_scaled

        present = [k for k in ("roe", "roa", "gmar", "cfoa", "leverage", "ndebt_ebitda") if out.get(k) is not None]
        out["data_quality"] = "ok" if len(present) >= 4 else "partial"
        return out
    except Exception as e:
        logger.debug("extract_metrics failed: %s", e)
        return {"data_quality": "partial"}


# ═════════════════════════ FETCH (yfinance + disk-cache) ══════════════════════

def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("/", "_")
    return CACHE_DIR / f"{safe}.json"


def _cache_fresh(ticker: str) -> Optional[dict]:
    p = _cache_path(ticker)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        fetched = date.fromisoformat(raw.get("fetched_at", "2000-01-01"))
        if (date.today() - fetched).days <= CACHE_MAX_AGE_DAYS:
            return raw
    except Exception:
        pass
    return None


def fetch_ticker_data(ticker: str, force: bool = False) -> Optional[dict]:
    """Råbokslut + prishistorik (cachad 7 d). None vid fel/tillfällighet."""
    if not force:
        cached = _cache_fresh(ticker)
        if cached:
            return cached
    try:
        import yfinance as yf
        y = yf.Ticker(ticker)
        frames = {"financials": y.financials, "balance_sheet": y.balance_sheet, "cashflow": y.cashflow}
        hist = y.history(period="1y", interval="1d", auto_adjust=True)
        s = {
            "ticker": ticker,
            "fetched_at": date.today().isoformat(),
            "frame_fin": {}, "frame_bal": {}, "frame_cash": {},
            "close_last": None, "returns_1y": None,
        }
        s.update(_frames_to_storage(frames, hist))
        _cache_path(ticker).parent.mkdir(parents=True, exist_ok=True)
        _cache_path(ticker).write_text(json.dumps(s, default=str), encoding="utf-8")
        return s
    except Exception as e:
        logger.warning("fetch %s misslyckades: %s", ticker, e)
        return None


def _frames_to_storage(frames: dict, hist) -> dict:
    """Kompakt JSON-lagring: dict[period] → dict[item] → värde."""
    out: dict = {"frame_fin": {}, "frame_bal": {}, "frame_cash": {}}
    for key, target in (("financials", "frame_fin"), ("balance_sheet", "frame_bal"), ("cashflow", "frame_cash")):
        df = frames.get(key)
        if df is None or df.empty:
            continue
        for c in df.columns:
            period = str(pd.to_datetime(c).date()) if _to_date(c) else str(c)
            col = {}
            for item in df.index:
                try:
                    v = df.loc[item, c]
                    col[str(item)] = float(v) if pd.notna(v) else None
                except Exception:
                    continue
            out[target][period] = col
    # Prishistorik → returns
    out["close_last"] = float(hist["Close"].iloc[-1]) if hist is not None and not hist.empty and len(hist["Close"]) else None
    rets = hist["Close"].pct_change().dropna().tolist() if hist is not None and not hist.empty else []
    out["returns_1y"] = rets
    return out


def _to_date(v) -> Optional[date]:
    try:
        d = pd.to_datetime(v)
        if not pd.isna(d):
            return d.date()
    except Exception:
        pass
    return None


def storage_to_frames(s: dict):
    """Omvänt: JSON-lagring → DataFrames (yfinance-format: index=items, columns=periods)."""
    def _df(d: dict):
        if not d:
            return None
        # d = {period: {item: value}} → DataFrame ger index=items, kolumner=perioder
        return pd.DataFrame(d)

    return (
        _df(s.get("frame_fin") or {}),
        _df(s.get("frame_bal") or {}),
        _df(s.get("frame_cash") or {}),
    )


# ═════════════════════════ Z-BYGGARE + DB ═════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="QMJ composite scores")
    parser.add_argument("--limit-tickers", type=int, default=120)
    parser.add_argument("--ticker", type=str, help="Endast en ticker (debug)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    conn = None
    if not args.dry_run:
        if not os.environ.get("DATABASE_URL"):
            logger.error("DATABASE_URL saknas")
            return
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])

    tickers = []
    if args.ticker:
        tickers = [args.ticker]
    elif conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ticker FROM universe_registry
            WHERE ticker IS NOT NULL AND status IN ('listed', 'verify')
              AND (ticker LIKE '%.ST' OR ticker LIKE '%.OL' OR ticker LIKE '%.HE' OR ticker LIKE '%.CO')
            ORDER BY ticker LIMIT %s
        """, (args.limit_tickers,))
        tickers = [r[0] for r in cur.fetchall()]
        if not tickers:
            cur.execute("""
                SELECT DISTINCT ticker FROM scan_results
                WHERE ticker IS NOT NULL
                  AND (ticker LIKE '%.ST' OR ticker LIKE '%.OL' OR ticker LIKE '%.HE' OR ticker LIKE '%.CO')
                LIMIT %s
            """, (args.limit_tickers,))
            tickers = [r[0] for r in cur.fetchall()]

    metrics: dict[str, dict] = {}
    errors = 0
    for i, t in enumerate(tickers):
        raw = fetch_ticker_data(t, force=args.force_fetch)
        if not raw:
            errors += 1
            time.sleep(FETCH_SLEEP)
            continue
        fin, bal, cash = storage_to_frames(raw)
        metrics[t] = extract_metrics(fin, bal, cash, raw.get("close_last"), raw.get("returns_1y") or [])
        metrics[t]["ticker"] = t
        time.sleep(FETCH_SLEEP)

    logger.info("Klart: %d/%d tickers med data (%d fel)", len(metrics), len(tickers), errors)

    if args.dry_run:
        preview = sorted(metrics.items(), key=lambda kv: (kv[1].get("data_quality", "") != "ok",))[:3]
        print(json.dumps({t: {k: v for k, v in m.items() if k != "ticker"} for t, m in dict(preview).items()},
                         default=str, indent=1))
        return

    # Kedja: per-metrik percentil över alla med VÄRDE (hela universum; grupp-nedbrytning
    # för kvalitet-malseri kräver ≥20 per grupp — vi kör enkelt universum-rank nu +
    # lagrar grupp så framtida skärpning kan göras).
    metric_keys = [
        ("roe", 1), ("roa", 1), ("gmar", 1), ("cfoa", 1), ("leverage", -1),
        ("ndebt_ebitda", -1), ("intcov", 1), ("roe_vol", -1), ("vol_ann", -1),
        ("issuance", -1), ("ev_ebitda", -1), ("fcf_yield", 1),
        ("momentum_vol_scaled", 1),
    ]
    z_final: dict[str, dict] = {t: {} for t in metrics}
    for key, sign in metric_keys:
        vals = {t: (m.get(key) * sign if m.get(key) is not None else None) for t, m in metrics.items()}
        ranks = rank_pct(vals)
        for t in metrics:
            z_final[t][key] = ranks.get(t)

    # Insider (köpkluster) + shorts-filter + säljkluster-varning
    insider_score, sell_flags, short_map = {}, {}, {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT ticker, cluster_score, unique_sellers_30d FROM insider_cluster_signals")
        for ticker, cs, sellers in cur.fetchall():
            if cs:
                insider_score[ticker] = float(cs)
            if int(sellers or 0) >= 3:
                sell_flags[ticker] = True
        cur.execute("""
            SELECT ticker, total_short_pct, is_new_discovery, scan_date FROM short_positions
            WHERE scan_date >= CURRENT_DATE - 7
        """)
        for ticker, pct, is_new, sd in cur.fetchall():
            if ticker is None:
                continue
            s = short_map.setdefault(ticker, {"pct": None, "new": False})
            s["pct"] = float(pct) if pct is not None else s["pct"]
            if is_new:
                s["new"] = True
    except Exception as e:
        logger.warning("Insider/short-läsning misslyckades: %s (kör utan)", e)

    insider_z_raw = rank_pct({t: v for t, v in insider_score.items()})

    today = date.today()
    rows = []
    now = datetime.now()
    for t, m in metrics.items():
        fy_end = None
        if m.get("fy_end"):
            try:
                fy_end = date.fromisoformat(m["fy_end"])
            except Exception:
                fy_end = None
        as_of = None
        if fy_end and as_of_strict(fy_end, today):
            as_of = fy_end
        # Data äldre än as-of-regel → behandla som ej giltig (data_quality partial)
        dq = m.get("data_quality", "partial")
        if fy_end and not as_of:
            dq = "partial"

        q = np.mean([z_final[t].get(k) for k in
                     ("roe", "roa", "gmar", "cfoa", "leverage", "ndebt_ebitda", "intcov", "roe_vol", "vol_ann")
                     if z_final[t].get(k) is not None]) if any(
            z_final[t].get(k) is not None for k in
            ("roe", "roa", "gmar", "cfoa", "leverage", "ndebt_ebitda", "intcov", "roe_vol", "vol_ann")
        ) else None
        mz = z_final[t].get("momentum_vol_scaled")
        v = np.mean([z_final[t].get(k) for k in ("ev_ebitda", "fcf_yield") if z_final[t].get(k) is not None]) if any(
            z_final[t].get(k) is not None for k in ("ev_ebitda", "fcf_yield")) else None
        p = np.mean([z_final[t].get(k) for k in ("issuance",) if z_final[t].get(k) is not None]) if z_final[t].get("issuance") is not None else None
        iz = insider_z_raw.get(t, 50.0)

        short = short_map.get(t)
        ex = short_exclusion(short.get("pct") if short else None,
                             short.get("new") if short else False)
        flags = []
        if sell_flags.get(t):
            flags.append("sell_cluster")

        rank = None if ex else composite(q, mz, v, p, iz)
        if rank is not None and isinstance(rank, float) and not math.isfinite(rank):
            rank = None

        rows.append({
            "ticker": t, "scan_date": today.isoformat(),
            "as_of_date": as_of.isoformat() if as_of else None,
            "rebalance_flag": now.month == 4,
            "quality_z": round(float(q), 2) if q is not None else None,
            "momentum_z": round(float(mz), 2) if mz is not None else None,
            "value_z": round(float(v), 2) if v is not None else None,
            "payout_z": round(float(p), 2) if p is not None else None,
            "insider_z": round(float(iz), 2),
            "alpha_rank": rank,
            "exclusion_reason": ex,
            "warning_flags": json.dumps(flags),
            "data_quality": dq,
            "metrics_json": json.dumps({
                k: m.get(k) for k in ("roe", "roa", "gmar", "cfoa", "leverage",
                                      "ndebt_ebitda", "ev_ebitda", "fcf_yield",
                                      "momentum_raw", "mcap_local") if m.get(k) is not None
            }, default=str),
        })

    cur = conn.cursor()
    written = 0
    for r in rows:
        try:
            cur.execute("SAVEPOINT qmj_row")
            cur.execute("""
                INSERT INTO qmj_scores (
                    ticker, scan_date, as_of_date, rebalance_flag,
                    quality_z, momentum_z, value_z, payout_z, insider_z,
                    alpha_rank, exclusion_reason, warning_flags, data_quality, metrics_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                ON CONFLICT (ticker, scan_date) DO UPDATE SET
                    as_of_date = EXCLUDED.as_of_date,
                    rebalance_flag = EXCLUDED.rebalance_flag,
                    quality_z = EXCLUDED.quality_z,
                    momentum_z = EXCLUDED.momentum_z,
                    value_z = EXCLUDED.value_z,
                    payout_z = EXCLUDED.payout_z,
                    insider_z = EXCLUDED.insider_z,
                    alpha_rank = EXCLUDED.alpha_rank,
                    exclusion_reason = EXCLUDED.exclusion_reason,
                    warning_flags = EXCLUDED.warning_flags,
                    data_quality = EXCLUDED.data_quality,
                    metrics_json = EXCLUDED.metrics_json
            """, (r["ticker"], r["scan_date"], r["as_of_date"], r["rebalance_flag"],
                  r["quality_z"], r["momentum_z"], r["value_z"], r["payout_z"], r["insider_z"],
                  r["alpha_rank"], r["exclusion_reason"], r["warning_flags"], r["data_quality"],
                  r["metrics_json"]))
            cur.execute("RELEASE SAVEPOINT qmj_row")
            written += 1
        except Exception as e:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT qmj_row")
            except Exception:
                pass
            logger.warning("Upsert failed %s: %s", r["ticker"], e)
    conn.commit()
    conn.close()

    top = sorted([r for r in rows if r["alpha_rank"] is not None],
                 key=lambda r: r["alpha_rank"], reverse=True)[:5]
    print(json.dumps({
        "status": "ok", "written": written, "excluded": len(rows) - len(top) - (len(rows) - sum(1 for r in rows if r['alpha_rank'] is not None)),
        "top5": [{"ticker": r["ticker"], "rank": r["alpha_rank"]} for r in top],
    }))
    logger.info("QMJ klar: %d rader skrivna", written)


if __name__ == "__main__":
    main()
