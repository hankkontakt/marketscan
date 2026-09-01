"""
liquidity.py — Likviditetsmotor för segmentrelaterad handelsvolym och gradering (A–F).

Institutionell praxis (Research-underlag 2, D5):
  - Likviditet är en gate och badge, ALDRIG en poängfaktor i MasterRank.
  - Golv per segment baseras på 20-dagars MEDIAN-omsättning omräknad till SEK:
      * micro_cap:  500 000 SEK/dag
      * small_cap:  2 000 000 SEK/dag
      * mid_cap:   10 000 000 SEK/dag
      * large_cap: 20 000 000 SEK/dag
      * unknown:   20 000 000 SEK/dag (konservativ storbolagsstandard)

Gradering:
  - F: pris < 1 (nativ quote-valuta) ELLER < 10 aktiva handelsdagar av 20 ELLER medianomsättning < 10 % av golv
  - E: omsättning < 50 % av golv
  - D: omsättning < 100 % av golv
  - C: omsättning >= golv (godkänd baslikviditet)
  - B: omsättning >= 5x golv (god institutionell likviditet)
  - A: omsättning >= 20x golv (utmärkt likviditet)
  - unknown: saknar volymdata -> ingen straffavgift, badge "—"

Flagga low_liquidity omdefinieras till: grade in ("D", "E", "F").

FX (Phase 4): omräkning sker ALDRIG via statisk karta. Kursen skickas in
explicit (hämtad från public.fx_rates via backend_worker/fx.py med as-of-datum).
Saknad kurs = karantän, aldrig gissning.
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

SEGMENT_FLOORS_SEK: dict[str, float] = {
    "micro_cap": 500_000.0,
    "small_cap": 2_000_000.0,
    "mid_cap": 10_000_000.0,
    "large_cap": 20_000_000.0,
    "unknown": 20_000_000.0,
}


def turnover_to_sek(turnover_native: Optional[float], fx_rate: float) -> Optional[float]:
    """Convert native-currency turnover to SEK with an explicit FX rate.

    ``fx_rate`` is SEK per 1 unit of the native currency, resolved from
    ``public.fx_rates`` (see ``backend_worker/fx.py``). ``None`` turnover is
    ``None``; a missing rate must quarantine the observation upstream.
    """
    if turnover_native is None or not np.isfinite(turnover_native):
        return None
    return float(turnover_native * fx_rate)


def compute_turnover_20d(
    closes: list[float],
    volumes: list[float],
    fx_rate: float,
) -> tuple[Optional[float], int]:
    """Beräkna 20-dagars medianomsättning i SEK samt antal aktiva handelsdagar.

    Returnerar: (median_turnover_sek, active_days)
    """
    if not closes or not volumes:
        return None, 0

    n = min(len(closes), len(volumes), 20)
    c_20 = closes[-n:]
    v_20 = volumes[-n:]

    daily_turnover_native: list[float] = []
    active_days = 0
    for c, v in zip(c_20, v_20):
        if c is not None and v is not None and c > 0 and v > 0:
            daily_turnover_native.append(float(c * v))
            active_days += 1
        elif c is not None and c > 0:
            daily_turnover_native.append(0.0)

    if not daily_turnover_native or active_days == 0:
        return None, 0

    med_native = float(np.median(daily_turnover_native))
    med_sek = turnover_to_sek(med_native, fx_rate)
    return med_sek, active_days


def compute_liquidity_grade(
    median_turnover_sek: Optional[float],
    segment: Optional[str],
    active_days: int = 20,
    price: Optional[float] = None,
) -> str:
    """Bestäm likviditetsgrad A–F eller 'unknown' från omsättning och segment.

    Regler:
      - Om medianomsättning saknas (None/NaN) -> 'unknown'
      - F: pris < 1.0 (penny stock) ELLER active_days < 10 (illikvid handel) ELLER turnover < 10% av golv
      - E: turnover < 50% av golv
      - D: turnover < 100% av golv
      - C: turnover >= golv
      - B: turnover >= 5x golv
      - A: turnover >= 20x golv
    """
    if median_turnover_sek is None or not np.isfinite(median_turnover_sek) or median_turnover_sek < 0:
        return "unknown"

    seg = segment or "unknown"
    floor = SEGMENT_FLOORS_SEK.get(seg, SEGMENT_FLOORS_SEK["unknown"])

    # Penny stock guard eller extremt få handelsdagar
    if (price is not None and price < 1.0) or active_days < 10 or median_turnover_sek < (floor * 0.10):
        return "F"

    if median_turnover_sek < (floor * 0.50):
        return "E"

    if median_turnover_sek < floor:
        return "D"

    if median_turnover_sek >= (floor * 20.0):
        return "A"

    if median_turnover_sek >= (floor * 5.0):
        return "B"

    return "C"


def is_low_liquidity(grade: Optional[str]) -> bool:
    """Omdefinierad low_liquidity: sant endast om grade in ('D', 'E', 'F')."""
    return grade in ("D", "E", "F")


# ═════════════════════════ DB & HÄMTNING ══════════════════════════════════════

def fetch_ticker_liquidity(ticker: str, segment: Optional[str], currency: Optional[str] = None, fx_rate: Optional[float] = None) -> dict:
    """Hämta 20d-historik och beräkna likviditet för en enskild ticker.

    ``fx_rate`` (SEK per native enhet) MÅSTE komma från ``backend_worker/fx.py``
    med as-of-datum. Utan kurs → ingen SEK-omsättning → grade 'unknown'.
    """
    try:
        import yfinance as yf
        y = yf.Ticker(ticker)
        hist = y.history(period="1mo", interval="1d", auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist or "Volume" not in hist:
            return {"ticker": ticker, "liquidity_grade": "unknown", "turnover_20d_median": None, "low_liquidity": False}
        if fx_rate is None or fx_rate <= 0:
            return {"ticker": ticker, "liquidity_grade": "unknown", "turnover_20d_median": None, "low_liquidity": False}

        closes = list(hist["Close"].astype(float))
        volumes = list(hist["Volume"].astype(float))
        last_price = closes[-1] if closes else None

        med_sek, active = compute_turnover_20d(closes, volumes, fx_rate)
        grade = compute_liquidity_grade(med_sek, segment, active_days=active, price=last_price)
        return {
            "ticker": ticker,
            "liquidity_grade": grade,
            "turnover_20d_median": round(med_sek, 2) if med_sek is not None else None,
            "low_liquidity": is_low_liquidity(grade),
        }
    except Exception as e:
        logger.debug("%s: fel vid likviditetsberäkning: %s", ticker, e)
        return {"ticker": ticker, "liquidity_grade": "unknown", "turnover_20d_median": None, "low_liquidity": False}


def main():
    parser = argparse.ArgumentParser(description="Likviditetsmotor (grader A–F)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-tickers", type=int, default=0)
    _args = parser.parse_args()

    # Explicit dated rates (SEK per unit) — same contract as public.fx_rates.
    demo_cases = [
        ("SAP.DE", "large_cap", 500_000_000.0, 11.1145, 150.0),   # EUR
        ("EQNR.OL", "large_cap", 250_000_000.0, 1.02736, 300.0),  # NOK
        ("SMALL1.ST", "small_cap", 5_000_000.0, 1.0, 25.0),       # SEK
        ("MICRO_ILLIQUID.ST", "micro_cap", 30_000.0, 1.0, 5.0),
        ("PENNY.ST", "micro_cap", 1_000_000.0, 1.0, 0.5),
    ]

    print("=== Liquidity Demo ===")
    for tk, seg, turn, fx, pr in demo_cases:
        t_sek = turnover_to_sek(turn, fx)
        grade = compute_liquidity_grade(t_sek, seg, active_days=20, price=pr)
        print(f"{tk:18} seg={seg:10} turnover={t_sek:12,.0f} SEK -> grade={grade} low_liquidity={is_low_liquidity(grade)}")


if __name__ == "__main__":
    main()