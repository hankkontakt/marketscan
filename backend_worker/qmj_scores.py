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
    python -m backend_worker.qmj_scores --limit-tickers 0   # 0 = alla (standard)
"""
from __future__ import annotations

import argparse
import calendar
import json
import logging
import math
import os
import time
from datetime import date, datetime
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


def _fy_plus_months(d: date, add_months: int) -> date:
    """d + add_months kalendermånader (dag klamras till månadens sista dag).

    OBS: skiljer sig från as_of_strict:s dag-klampning till 28 — här används
    kalendermånadssemantik (fy_end + 5 mån = t.ex. 2026-03-31 → 2026-08-31),
    vilket är den semantik latest_valid_periods kontrakt kräver.
    """
    m, y = d.month, d.year
    for _ in range(add_months):
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def latest_valid_period(fy_dates: list[str], today: date,
                        add_months: int = AS_OF_ADD_MONTHS) -> Optional[str]:
    """Senaste period-ISO-datum där fy_end + add_months <= today. None om inget giltigt.

    "Latest published annual as-of scan date": blandad FY-vintage är korrekt när
    tvärsnittet rankas på vad som faktiskt var publikt (PIT-honesty).
    """
    best: Optional[str] = None
    for p in fy_dates:
        try:
            d = date.fromisoformat(p)
        except (TypeError, ValueError):
            continue
        if _fy_plus_months(d, add_months) <= today:
            if best is None or p > best:
                best = p
    return best


def bucket_mcap(mcap_local: float) -> int:
    """0=50-300M, 1=300M-1.5B, 2=1.5B-5B, 3=utanför/okänd."""
    if mcap_local is None or mcap_local <= 0 or not math.isfinite(mcap_local):
        return 3
    for i, (lo, hi) in enumerate(SIZE_GROUPS):
        if lo <= mcap_local < hi:
            return i
    return 3


def stratum_of(years_data: float | None, revenue: float | None,
               ocf: float | None, equity: float | None) -> str:
    """Jämförbarhetsskikt (ny vs gammal — 'olika ligor', samma mått):

    - turnaround: negativt eget kapital (distress)
    - new_small:  <3 års data eller omsättning < 250 Mkr
    - established: omsättning >= 250 Mkr och OCF > 0
    - growth_early: omsättning >= 250 Mkr, OCF <= 0 (växer innan lönsamhet)
    """
    if equity is not None and equity <= 0:
        return "turnaround"
    if (years_data is None or years_data < 3
            or revenue is None or revenue < 250e6):
        return "new_small"
    if ocf is not None and ocf > 0:
        return "established"
    return "growth_early"


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


def compute_sector_value(value_rows: list, min_n: int = 15) -> dict:
    """Sektorrelativ värdepercentil per ticker (ren, testbar; ingen DB).

    Input: lista av dict {ticker, sector, value_metric} — value_metric är samma
    värdekomposit som value_z (mean av ev_ebitda/fcf_yield-percentiler).
    Output: {ticker: percentil 0-100} — percentil av value_metric INOM sektorn
    (rank_pct, högt=bättre). Kräver sektor känd OCH ≥ min_n tickers med giltig
    value_metric i samma sektor; annars None. Ticker utan giltig value_metric
    (None/NaN) → None och räknas inte i grupp-n.
    """
    out: dict = {r.get("ticker"): None for r in value_rows if r.get("ticker") is not None}
    by_sector: dict[str, dict] = {}
    for r in value_rows:
        t = r.get("ticker")
        sector = r.get("sector")
        vm = r.get("value_metric")
        if t is None or not sector or vm is None or not math.isfinite(float(vm)):
            continue
        by_sector.setdefault(sector, {})[t] = float(vm)
    for sector, vals in by_sector.items():
        if len(vals) < min_n:
            continue
        for t, pct in rank_pct(vals).items():
            out[t] = pct
    return out


def composite(q=None, m=None, v=None, p=None, i=None) -> float:
    """Viktad komposit (percentiler 0-100, neutral=50).

    VIKTIGT: float()-cast — np.float64 (från np.mean/round) skickas av
    psycopg2 som generisk repr → SQL 'np.float64(...)' → schema-fel.
    """
    value = (
        WEIGHTS["quality"] * (q if q is not None else 50)
        + WEIGHTS["momentum"] * (m if m is not None else 50)
        + WEIGHTS["value"] * (v if v is not None else 50)
        + WEIGHTS["payout"] * (p if p is not None else 50)
        + WEIGHTS["insider"] * (i if i is not None else 50)
    )
    return round(float(value), 2)


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
                    price: Optional[float], hist_returns: list,
                    period: Optional[str] = None) -> dict:
    """Extrahera QMJ-metrik ur RÅA bokslut (yfinance-format: index=items, kolumner=perioder).

    Saknade värden → None (caller ger neutral 50). "data_quality": ok|partial.
    period: ISO-datum för en specifik periodkolumn (t.ex. senaste GILTIGA
    årsbokslut vid PIT-fallback). None → senaste FY (nuvarande beteende).
    """
    out: dict = {"data_quality": "partial"}
    if fin is None or bal is None or cash is None or fin.empty or bal.empty:
        return out
    try:
        # Volatilitet + momentum 12-1 (vol-skalad) ur prishistoriken — beräknas
        # INNAN annual-gaten: ny-listade bolag (<3 års bokslut, fy_last None) ska
        # ändå få momentum/vol när prishistorik finns (tidig return hoppade över).
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

        fy_dates = model_periods(fin)
        if len(fy_dates) != len(fin.columns):
            return out
        out["fy_periods"] = [str(p) for p in fy_dates]
        fy_last, suspect = fy_age_fit(fy_dates, date.today())
        if fy_last is None:
            out["fy_end"] = None
            return out
        # period given → använd den kolumnen (PIT-fallback); annars senaste FY.
        # Kolumner kan vara fallande — använd sorterat max som sanity.
        use_period = False
        if period is not None:
            p_date = _to_date(period)
            if p_date is not None and p_date in fy_dates:
                latest = period
                use_period = True
            else:
                latest = fy_last.isoformat()
        else:
            latest = fy_last.isoformat()

        def bval(*keys):
            return _row_val(bal, latest, *keys)

        def fval(*keys):
            return _row_val(fin, latest, *keys)

        def cval(*keys):
            return _row_val(cash, latest, *keys)

        ni = fval("Net Income")
        rev = fval("Total Revenue")
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
        # Interest Expense är NEGATIV hos yfinance → intcov = ebit / abs(interest),
        # annars blir intcov negativ och sign=1 (högre bättre) belönar de mest
        # skuldsatta. interest == 0 eller None → intcov None (faktorn skippas).
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
            "intcov": (ebit / abs(interest)) if (ebit is not None and interest and interest != 0) else None,
            "roe_vol": float(np.std(roe_series)) if len(roe_series) >= 2 else None,
            "issuance": issuance,
            "ev_ebitda": None,
            "fcf_yield": None,
            "mcap_local": mcap,
            "fy_end": latest,
            "suspect": suspect,
            # För stratum (jämförbarhet ny vs gammal):
            "revenue_latest": rev,
            "ocf_latest": ocf,
            "equity_latest": eq,
            "years_data": len(sorted(fy_dates)),
        })
        if mcap is not None and ndebt is not None and ebitda and ebitda != 0:
            ev = float((mcap + ndebt) / ebitda)
            out["ev_ebitda"] = ev if abs(ev) <= 500 else None   # absurd multipla → saknad
        if fcf is not None and mcap and mcap > 0:
            fy = float(fcf / mcap)
            out["fcf_yield"] = fy if abs(fy) <= 1.0 else None   # >100 % yield = datafel

        if use_period and period != fy_last.isoformat():
            # Fallback-period ≠ senaste FY → delvis data (äldre bokslut)
            out["data_quality"] = "partial"
        else:
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
    parser.add_argument("--limit-tickers", type=int, default=0,
                        help="Max antal tickers att bearbeta (0 = alla, standard)")
    parser.add_argument("--ticker", type=str, help="Endast en ticker (debug)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    start = time.time()
    conn = None
    if not args.dry_run:
        if not os.environ.get("DATABASE_URL"):
            logger.error("DATABASE_URL saknas")
            return
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])

    tickers = []
    limit = None  # --ticker-vägen använder ingen limit (UnboundLocalError-fix 2026-08-29)
    if args.ticker:
        tickers = [args.ticker]
    elif conn:
        cur = conn.cursor()
        # 0 = ALLA (ingen LIMIT); N > 0 = manuell begränsad körning.
        limit = args.limit_tickers if args.limit_tickers and args.limit_tickers > 0 else None
        if limit:
            cur.execute("""
                SELECT ticker FROM universe_registry
                WHERE ticker IS NOT NULL AND status = 'listed'
                  AND (ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s)
                ORDER BY ticker LIMIT %s
            """, ("%.ST", "%.OL", "%.HE", "%.CO", limit))
        else:
            cur.execute("""
                SELECT ticker FROM universe_registry
                WHERE ticker IS NOT NULL AND status = 'listed'
                  AND (ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s)
                ORDER BY ticker
            """, ("%.ST", "%.OL", "%.HE", "%.CO"))
        tickers = [r[0] for r in cur.fetchall()]
        if not tickers:
            if limit:
                cur.execute("""
                    SELECT DISTINCT ticker FROM scan_results
                    WHERE ticker IS NOT NULL
                      AND (ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s)
                    LIMIT %s
                """, ("%.ST", "%.OL", "%.HE", "%.CO", limit))
            else:
                cur.execute("""
                    SELECT DISTINCT ticker FROM scan_results
                    WHERE ticker IS NOT NULL
                      AND (ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s OR ticker LIKE %s)
                """, ("%.ST", "%.OL", "%.HE", "%.CO"))
            tickers = [r[0] for r in cur.fetchall()]
    logger.info("Universum: %d tickers att bearbeta (limit=%s)", len(tickers), limit if limit else "alla")

    metrics: dict[str, dict] = {}
    errors = 0
    today = date.today()
    for i, t in enumerate(tickers):
        raw = fetch_ticker_data(t, force=args.force_fetch)
        if not raw:
            errors += 1
            time.sleep(FETCH_SLEEP)
            continue
        fin, bal, cash = storage_to_frames(raw)
        price = raw.get("close_last")
        hist_returns = raw.get("returns_1y") or []
        m = extract_metrics(fin, bal, cash, price, hist_returns)
        # PIT-fallback: senaste GILTIGA årsbokslut (fy_end + 5 mån <= today) i
        # stället för alltid senaste FY — blandad FY-vintage är korrekt när
        # tvärsnittet rankas på vad som faktiskt var publikt.
        vp = latest_valid_period(m.get("fy_periods", []), today)
        if vp and vp != m.get("fy_end"):
            m = extract_metrics(fin, bal, cash, price, hist_returns, period=vp)
        elif not vp:
            # Inga giltiga perioder → PIT-block (aldrig ranka på ogiltig period)
            m["fy_end"] = None
        m["ticker"] = t
        metrics[t] = m
        time.sleep(FETCH_SLEEP)

    logger.info("Klart: %d/%d tickers med data (%d fel) på %.1f s",
                len(metrics), len(tickers), errors, time.time() - start)

    # Sektorkarta (universe_registry) för sektorrelativ värdepercentil.
    # Många rader saknar sektor idag (backfill pågår) → fallback global, ok.
    sector_map: dict = {}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT isin, ticker, sector FROM universe_registry")
            for _isin, ticker, sector in cur.fetchall():
                if ticker:
                    sector_map[ticker] = sector
        except Exception as e:
            logger.warning("Sektorläsning misslyckades: %s (kör global)", e)
            try:
                conn.rollback()
            except Exception:
                pass

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
    # Skikt (ny vs gammal — percentiler beräknas INOM skikt när n >= MIN_GROUP_SIZE)
    strata = {
        t: stratum_of(m.get("years_data"), m.get("revenue_latest"),
                      m.get("ocf_latest"), m.get("equity_latest"))
        for t, m in metrics.items()
    }
    strat_groups: dict[str, list] = {}
    for t, s in strata.items():
        strat_groups.setdefault(s, []).append(t)
    rank_modes = {
        t: ("within_stratum" if len(strat_groups[strata[t]]) >= MIN_GROUP_SIZE else "global")
        for t in metrics
    }

    z_final: dict[str, dict] = {t: {} for t in metrics}
    for key, sign in metric_keys:
        per_strat: dict[str, dict] = {}
        for s, members in strat_groups.items():
            if len(members) < MIN_GROUP_SIZE:
                continue
            vals = {t: (metrics[t].get(key) * sign if metrics[t].get(key) is not None else None)
                    for t in members}
            per_strat[s] = rank_pct(vals)
        global_vals = {t: (m.get(key) * sign if m.get(key) is not None else None)
                       for t, m in metrics.items()}
        global_ranks = rank_pct(global_vals)
        for t in metrics:
            local = (per_strat.get(strata[t]) or {}).get(t)
            z_final[t][key] = local if local is not None else global_ranks.get(t)

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
        # Ett misslyckat READ aborterar transaktionen → rulla tillbaka så att
        # efterföljande upserts inte dör med "current transaction is aborted".
        try:
            conn.rollback()
        except Exception:
            pass

    insider_z_raw = rank_pct({t: v for t, v in insider_score.items()})

    rows = []
    now = datetime.now()
    value_rows = []
    for t, m in metrics.items():
        fy_end = None
        if m.get("fy_end"):
            try:
                fy_end = date.fromisoformat(m["fy_end"])
            except Exception:
                fy_end = None
        # PIT-gate: annual-data giltig först från fy_end + 5 mån. Fallback till
        # senaste GILTIGA period sker redan i fetch-loopen (extract_metrics med
        # period=...); här är fy_end det valda giltiga perioddatumet, eller None
        # när inga giltiga perioder finns → block (ärligt, ingen rank).
        as_of = fy_end
        pit_blocked = not bool(fy_end)
        dq = m.get("data_quality", "partial")
        if pit_blocked:
            dq = "partial"

        if pit_blocked:
            q = mz = v = p = iz = None
        else:
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
        value_rows.append({"ticker": t, "sector": sector_map.get(t), "value_metric": v})

        short = short_map.get(t)
        ex = short_exclusion(short.get("pct") if short else None,
                             short.get("new") if short else False)
        if pit_blocked:
            ex = "PIT: senaste bokslut ej giltigt (fy_end+5mån)"
        flags = []
        if sell_flags.get(t):
            flags.append("sell_cluster")

        rank = None if ex else composite(q, mz, v, p, iz)
        if rank is not None:
            rank = float(rank)
            if not math.isfinite(rank):
                rank = None

        rows.append({
            "ticker": t, "scan_date": today.isoformat(),
            "as_of_date": as_of.isoformat() if as_of else None,
            "rebalance_flag": now.month == 4,
            "stratum": strata.get(t),
            "rank_mode": rank_modes.get(t, "global"),
            "quality_z": round(float(q), 2) if q is not None else None,
            "momentum_z": round(float(mz), 2) if mz is not None else None,
            "value_z": round(float(v), 2) if v is not None else None,
            "payout_z": round(float(p), 2) if p is not None else None,
            "insider_z": round(float(iz), 2) if iz is not None else None,
            "alpha_rank": rank,
            "exclusion_reason": ex,
            "warning_flags": json.dumps(flags),
            "data_quality": dq,
            "metrics_json": json.dumps({
                k: m.get(k) for k in ("roe", "roa", "gmar", "cfoa", "leverage",
                                      "ndebt_ebitda", "ev_ebitda", "fcf_yield",
                                      "momentum_raw", "mcap_local") if m.get(k) is not None
            } | ({"as_of": m["fy_end"]} if m.get("fy_end") else {}), default=str),
        })

    # Sektorrelativ värdepercentil (visningsfält; kompositen behåller global value_z)
    sector_value = compute_sector_value(value_rows)
    for r in rows:
        sv = sector_value.get(r["ticker"])
        r["sector_value_z"] = round(float(sv), 2) if sv is not None else None
        r["value_mode"] = "sector" if sv is not None else "global"

    cur = conn.cursor()
    written = 0
    for r in rows:
        try:
            cur.execute("SAVEPOINT qmj_row")
            cur.execute("""
                INSERT INTO qmj_scores (
                    ticker, scan_date, as_of_date, rebalance_flag, stratum, rank_mode,
                    quality_z, momentum_z, value_z, payout_z, insider_z,
                    alpha_rank, exclusion_reason, warning_flags, data_quality, metrics_json,
                    sector_value_z, value_mode
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
                ON CONFLICT (ticker, scan_date) DO UPDATE SET
                    as_of_date = EXCLUDED.as_of_date,
                    rebalance_flag = EXCLUDED.rebalance_flag,
                    stratum = EXCLUDED.stratum,
                    rank_mode = EXCLUDED.rank_mode,
                    quality_z = EXCLUDED.quality_z,
                    momentum_z = EXCLUDED.momentum_z,
                    value_z = EXCLUDED.value_z,
                    payout_z = EXCLUDED.payout_z,
                    insider_z = EXCLUDED.insider_z,
                    alpha_rank = EXCLUDED.alpha_rank,
                    exclusion_reason = EXCLUDED.exclusion_reason,
                    warning_flags = EXCLUDED.warning_flags,
                    data_quality = EXCLUDED.data_quality,
                    metrics_json = EXCLUDED.metrics_json,
                    sector_value_z = EXCLUDED.sector_value_z,
                    value_mode = EXCLUDED.value_mode
            """, (r["ticker"], r["scan_date"], r["as_of_date"], r["rebalance_flag"],
                  r.get("stratum"), r.get("rank_mode"),
                  r["quality_z"], r["momentum_z"], r["value_z"], r["payout_z"], r["insider_z"],
                  r["alpha_rank"], r["exclusion_reason"], r["warning_flags"], r["data_quality"],
                  r["metrics_json"], r["sector_value_z"], r["value_mode"]))
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
