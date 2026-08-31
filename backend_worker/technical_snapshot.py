"""
technical_snapshot.py — Teknisk position (RSI14, MA50/MA200, 52v-hög) per ticker.

Idag beräknas RSI/MA/52v bara i LLM-prompter (stocks.py:s AI-kommitté) och
lagras ALDRIG. Denna modul beräknar dem deterministiskt ur yfinance-prishistorik
och skriver till qmj_raw-cachen (delad med qmj_scores.py — ingen dubbelhämtning)
så att master_rank.py kan läsa dem.

Användning:
    python -m backend_worker.technical_snapshot --limit-tickers 5
    python -m backend_worker.technical_snapshot --limit-tickers 0
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "qmj_raw"
CACHE_MAX_AGE_DAYS = 7
FETCH_SLEEP = 1.2
RSI_PERIOD = 14
MA_FAST = 50
MA_SLOW = 200


def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.json"


def _read_history(ticker: str) -> Optional[list[float]]:
    """Rekonstruera stängningskurser (1y) ur QMJ-cachen: returns_1y + close_last.

    QMJ-cachen lagrar dagliga pct-avkastningar (kronologisk ordning) och sista
    stängning — inte råkurser. Vi går bakåt från close_last: c[i-1] = c[i]/(1+r).
    """
    raw = _cache_path(ticker)
    if not raw.exists():
        return None
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
    except Exception:
        return None
    rets = data.get("returns_1y")
    last = data.get("close_last")
    if not isinstance(rets, list) or not rets or last is None:
        return None
    closes: list[float] = [float(last)]
    for r in reversed(rets):
        r = float(r)
        prev = closes[-1] / (1.0 + r) if (1.0 + r) != 0 else None
        if prev is None:
            return None
        closes.append(prev)
    closes.reverse()
    # Säkerställ minimumlängd för MA200 (1y dagliga ≈ 250 obsar; om kortare, ok)
    return closes


def fetch_price_history(ticker: str) -> Optional[list[float]]:
    """Hämta 1y-prishistorik från yfinance och cacha i qmj_raw-format.

    Om QMJ-cachen saknas (vanligt på GH/Vercel) hämtar master_rank kurserna
    själv. Cachar returns_1y + close_last (samma format som qmj_scores) så att
    efterföljande körningar inte behöver nätverket. Thread-säker (per-fil skriv).
    """
    try:
        import yfinance as yf
        y = yf.Ticker(ticker)
        hist = y.history(period="1y", interval="1d", auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            logger.debug("%s: ingen prishistorik från yfinance", ticker)
            return None
        rets = hist["Close"].pct_change().dropna().tolist()
        last = float(hist["Close"].iloc[-1])
        _cache_path(ticker).parent.mkdir(parents=True, exist_ok=True)
        payload = {"ticker": ticker, "fetched_at": date.today().isoformat(),
                   "returns_1y": rets, "close_last": last}
        _cache_path(ticker).write_text(json.dumps(payload, default=str), encoding="utf-8")
        return list(hist["Close"].astype(float))
    except Exception as e:
        logger.debug("%s: prishistorik-fetch misslyckades: %s", ticker, e)
        return None


# ═════════════════════════ PURE CORE (testbar; ingen nätverk/DB) ══════════════

def rsi_14(closes: list[float]) -> Optional[float]:
    """Wilder RSI, 14 perioder. Kräver ≥15 stängningskurser."""
    if closes is None or len(closes) < RSI_PERIOD + 1:
        return None
    diffs = np.diff(np.asarray(closes, dtype=float))
    if len(diffs) < RSI_PERIOD:
        return None
    # Wilder-smoothed avg gain/loss
    gains = np.clip(diffs, 0, None)
    losses = np.clip(-diffs, 0, None)
    avg_gain = float(np.mean(gains[:RSI_PERIOD]))
    avg_loss = float(np.mean(losses[:RSI_PERIOD]))
    for i in range(RSI_PERIOD, len(diffs)):
        avg_gain = (avg_gain * (RSI_PERIOD - 1) + gains[i]) / RSI_PERIOD
        avg_loss = (avg_loss * (RSI_PERIOD - 1) + losses[i]) / RSI_PERIOD
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))


def moving_average(closes: list[float], period: int) -> Optional[float]:
    """Enkel glidande medelvärde — kräver ≥period kurser."""
    if closes is None or len(closes) < period:
        return None
    return float(np.mean(np.asarray(closes, dtype=float)[-period:]))


def dist_from_52w_high(closes: list[float]) -> Optional[float]:
    """Avstånd (fraction) från 52-veckors hög. Positiv = över hög."""
    if closes is None or len(closes) < 2:
        return None
    high = float(np.max(np.asarray(closes, dtype=float)))
    last = float(closes[-1])
    if high <= 0:
        return None
    return (last - high) / high


def tech_flags(rsi: Optional[float], last: float | None, ma50: Optional[float],
               ma200: Optional[float], dist_high: Optional[float]) -> list[str]:
    """Flaggor: OVERBOUGHT/OVERSOLD/TREND_DOWN/PULLBACK."""
    flags: list[str] = []
    if rsi is not None:
        if rsi > 75:
            flags.append("OVERBOUGHT")
        elif rsi < 30:
            flags.append("OVERSOLD")
    if ma200 is not None and last is not None and last < ma200:
        flags.append("TREND_DOWN")
    if dist_high is not None and -0.18 <= dist_high <= -0.05:
        flags.append("PULLBACK")
    return flags


def trend_tech(last: float | None, ma50: Optional[float], ma200: Optional[float]) -> Optional[str]:
    """'Upptrend' | 'Sidled' | 'Nedtrend' — samma regelverk som filters.py."""
    if last is None or ma200 is None:
        return None
    if last < ma200:
        return "Nedtrend"
    if ma50 is not None and last < ma50:
        return "Sidled"
    return "Upptrend"


def compute_technical(closes: list[float]) -> dict:
    """All teknisk position ur en stängningslista."""
    if not closes:
        return {"rsi_14": None, "ma50_dist_pct": None, "ma200_dist_pct": None,
                "dist_52w_high_pct": None, "trend_tech": None, "tech_flags": []}
    last = float(closes[-1])
    rsi = rsi_14(closes)
    ma50 = moving_average(closes, MA_FAST)
    ma200 = moving_average(closes, MA_SLOW)
    dist_high = dist_from_52w_high(closes)
    dist_ma50 = (last - ma50) / ma50 if ma50 and ma50 > 0 else None
    dist_ma200 = (last - ma200) / ma200 if ma200 and ma200 > 0 else None
    return {
        "rsi_14": round(rsi, 2) if rsi is not None else None,
        "ma50_dist_pct": round(dist_ma50 * 100, 2) if dist_ma50 is not None else None,
        "ma200_dist_pct": round(dist_ma200 * 100, 2) if dist_ma200 is not None else None,
        "dist_52w_high_pct": round(dist_high * 100, 2) if dist_high is not None else None,
        "trend_tech": trend_tech(last, ma50, ma200),
        "tech_flags": tech_flags(rsi, last, ma50, ma200, dist_high),
    }


def snapshot_technicals(tickers: list[str]) -> dict[str, dict]:
    """Bygg tekniska snapshots för alla tickers ur QMJ-cachen."""
    out: dict[str, dict] = {}
    for t in tickers:
        closes = _read_history(t)
        out[t] = compute_technical(list(closes) if closes else [])
    return out


# ═════════════════════════ CLI ═══════════════════════════

def load_tickers(limit: int) -> list[str]:
    """Tickernamn ur QMJ-cachen (redan hämtade) — ingen egen fetch."""
    if not CACHE_DIR.exists():
        return []
    files = sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    tickers = [p.stem for p in files if p.suffix == ".json"]
    if limit and limit > 0:
        tickers = tickers[:limit]
    return tickers


def main() -> None:
    parser = argparse.ArgumentParser(description="Teknisk position (RSI/MA/52v) ur QMJ-cache")
    parser.add_argument("--limit-tickers", type=int, default=0, help="0 = alla")
    parser.add_argument("--json-out", type=str, default=None, help="Skriv JSON till fil")
    parser.add_argument("--print", action="store_true", help="Skriv ut till stdout")
    args = parser.parse_args()

    tickers = load_tickers(args.limit_tickers)
    logger.info("Beräknar teknisk position för %d tickers", len(tickers))
    if not tickers:
        logger.warning("Ingen cache — kör qmj_scores först (hämtar prishistorik)")
        return

    result = snapshot_technicals(tickers)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Skrev %d snapshots till %s", len(result), args.json_out)
    if args.print:
        for t, r in sorted(result.items()):
            print(f"{t}: RSI={r['rsi_14']} MA200={r['ma200_dist_pct']}% 52v={r['dist_52w_high_pct']}% {r['trend_tech']} {r['tech_flags']}")


if __name__ == "__main__":
    main()
