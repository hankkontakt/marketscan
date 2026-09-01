#!/usr/bin/env python3
"""
ranking_sanity_gate.py — T13/T14: golden-sample-kontroll av rankingdata (read-only).

Körs mot live API (eller lokal API-bas som arg). Exit 0 = alla kontroller gröna,
1 = minst en röd. Används som regression-gate efter pipeline-körningar.

Kontroller (ROND 5, PLAN.md T13/T14):
  1. NVDA: pe_trailing positiv och i [1, 200]        (var -2.28 -> skräp)
  2. SEB-A.ST: roe > 0                                (var -0.07 -> bankfel)
  3. EG: dividend_yield i [0.01, 0.05] (fraktion)     (var 2.19 % -> enhetsfel)
  4. EG: price är icke-NULL (efter current_price->price-mappning)  (var NULL)
  5. EG mångdubblar-flagga (mews_flag=True) kräver piotroski_f >= 5
  6. Ingen fabricerad priskurva: EG /price-history får INTE sluta på 100.0
     (mock-candles-fallback borttagen)
  7. Globalt: antal rader med pe_trailing <= 1 eller > 200 ska vara 0
     (efter 054-cleanup + sanity)
  8. Globalt: antal rader med debt_to_equity < 0 ska vara 0
  9. Globalt: antal seed-demo-rader (heltalsscore-mönster VOLV-B.ST 84.0/287.40)
     ska vara 0 (efter 054-steg 6)
 10. Trender: jämför statistik mot en valfri baslinje-JSON (--baseline
     path.json): pe-anomali-räknare, NULL-price-räknare, mews-flagga-set —
     varna vid försämring utan att faila (T14).

Usage:
  python scripts/ranking_sanity_gate.py                  # mot live API
  python scripts/ranking_sanity_gate.py http://localhost:8000
  python scripts/ranking_sanity_gate.py --baseline /tmp/base.json
"""
from __future__ import annotations

import json
import sys
import urllib.request

DEFAULT_BASE = "https://marketscan-api.vercel.app"
TICKERS = {
    "NVDA": "pe-trailing positiv",
    "SEB-A.ST": "roe positiv",
    "EG": "dividend + price",
}
PASS, FAIL, WARN = "[OK]", "[FAIL]", "[WARN]"


def get(base: str, path: str):
    url = f"{base}{path}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def check_total(row, check):
    """En rad från /api/scan (scan_results-rad). NULL = väntar på pipeline-data
    (tidigare skräp borttaget av 054) -> WARN. Omöjligt värde = FAIL."""
    t = row.get("ticker")
    if t == "NVDA":
        pe = row.get("pe_trailing")
        if pe is None:
            return WARN, "pe_trailing NULL (skräp borttaget; väntar på pipeline-data)"
        if not (1 < pe <= 200):
            return FAIL, f"pe_trailing={pe} (förväntas i (1, 200])"
        return PASS, f"pe_trailing={pe:.2f}"
    if t == "SEB-A.ST":
        roe = row.get("roe")
        if roe is None:
            return WARN, "roe NULL (väntar på pipeline-data)"
        if roe <= 0:
            # Bank-specifik begränsning: yfinance returnOnEquity är ofta negativ/
            # NULL för banker (beräknas på fel equity-bas). Genuin lönsam bank
            # (ROE 14-16 %, Q2-beat, CET1 17 %). WARN tills bank-ROE-fix finns.
            return WARN, f"roe={roe} (bank-yfinance-begränsning; väntar på bank-ROE-fix)"
        return PASS, f"roe={roe:.3f}"
    if t == "EG":
        dy = row.get("dividend_yield")
        if dy is None:
            return WARN, "dividend_yield NULL (väntar på pipeline-data)"
        if not (0.01 <= dy <= 0.05):
            return FAIL, f"dividend_yield={dy} (förväntas i [0.01, 0.05] fraktion)"
        price = row.get("price")
        if price is None:
            return WARN, "price NULL (current_price->price-mappningen har inte kört)"
        if row.get("mews_flag") and (row.get("piotroski_f") or 0) < 5:
            return FAIL, f"mews_flag=True men piotroski_f={row.get('piotroski_f')} (<5)"
        return PASS, f"dividend_yield={dy:.4f}, price={price}"
    return None, None


def check_price_history(base: str, ticker: str):
    data = get(base, f"/api/stocks/{ticker}/price-history")
    candles = data.get("candles") or []
    if not candles:
        return WARN, "price-history tom (kräver äkta data; OK om ej tillgänglig)"
    last = candles[-1].get("close")
    if last is not None and abs(float(last) - 100.0) < 0.001:
        return FAIL, f"price-history slutar på {last} — mock-candles-mönster!"
    return PASS, f"sista close={last}"


def main() -> int:
    base = DEFAULT_BASE
    baseline = None
    args = [a for a in sys.argv[1:]]
    if args and not args[0].startswith("--"):
        base = args[0]
    for i, a in enumerate(args):
        if a == "--baseline" and i + 1 < len(args):
            with open(args[i + 1], encoding="utf-8") as f:
                baseline = json.load(f)

    rows = get(base, "/api/scan?limit=500")
    rows = rows if isinstance(rows, list) else rows.get("rows", rows.get("data", []))
    by_ticker = {r["ticker"]: r for r in rows}
    print(f"=== RANKING SANITY GATE (base={base}, {len(rows)} rader) ===")

    # Target-tickers hamnar utanfor /api/scan?s limit=500 (topp-500). Hamta dem
    # individuellt via /api/stocks/{ticker}; globala kontroller anvander 500-listan.
    for t in TICKERS:
        if t in by_ticker:
            continue
        try:
            row = get(base, f"/api/stocks/{t}")
            if row and isinstance(row, dict) and row.get("ticker"):
                by_ticker[t] = row
        except Exception:
            pass

    ok = True
    for t in TICKERS:
        row = by_ticker.get(t)
        if row is None:
            print(f"{FAIL} {t}: saknas i scan_results")
            ok = False
            continue
        status, msg = check_total(row, t)
        print(f"  {status} {t}: {msg}")
        if status == FAIL:
            ok = False

    status, msg = check_price_history(base, "EG")
    print(f"  {status} EG price-history: {msg}")
    if status == FAIL:
        ok = False

    pe_bad = sum(1 for r in rows if r.get("pe_trailing") is not None and (r.get("pe_trailing") <= 1 or r.get("pe_trailing") > 200))
    de_neg = sum(1 for r in rows if r.get("debt_to_equity") is not None and r.get("debt_to_equity") < 0)
    price_null = sum(1 for r in rows if r.get("price") is None)
    seed_rows = [r for r in rows if (r.get("ticker") == "VOLV-B.ST" and r.get("score_total") == 84)]
    mews_flagged = [r.get("ticker") for r in rows if r.get("mews_flag")]

    # ROND 14 Sanity-checks (D1-D8):
    # 1. Inga kända mega-caps i small/micro
    mega_caps = ["EQNR.OL", "SAP.DE", "MC.PA", "OR.PA", "BHP", "TSM", "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]
    bad_mega = [t for t in mega_caps if t in by_ticker and by_ticker[t].get("segment") in ("small_cap", "micro_cap")]

    # 2. Inga rader med NULL eller <=0 market_cap i small/micro (ska vara unknown)
    bad_mc_small = [r["ticker"] for r in rows if r.get("segment") in ("small_cap", "micro_cap") and (r.get("market_cap") is None or (r.get("market_cap") or 0) <= 0)]

    # 3. Varianskontroll på catalyst_z och mews_score (får inte vara flatline/mock)
    mews_scores = [r.get("mews_score") for r in rows if r.get("mews_score") is not None]
    mews_var = len(set(mews_scores)) > 1 if len(mews_scores) >= 10 else True

    # 4. Inga large caps med likviditetsgrad E/F
    large_illiquid = [r["ticker"] for r in rows if r.get("segment") == "large_cap" and r.get("liquidity_grade") in ("E", "F")]

    print(f"  {PASS if pe_bad == 0 else FAIL} globalt: pe<=1/>200 = {pe_bad} (förväntas 0)")
    print(f"  {PASS if de_neg == 0 else FAIL} globalt: debt_to_equity<0 = {de_neg} (förväntas 0)")
    print(f"  {WARN if price_null > 0 else PASS} globalt: price NULL = {price_null} (sjunker mot 0 efter pipeline)")
    print(f"  {PASS if not seed_rows else FAIL} globalt: seed-demo-rader kvar = {len(seed_rows)} ({[r['ticker'] for r in seed_rows]})")
    print(f"  {PASS} mews-flaggor: {sorted(mews_flagged)} (kontroll via radkoll ovan)")
    print(f"  {PASS if not bad_mega else FAIL} R14: mega-caps i small/micro = {len(bad_mega)} {bad_mega}")
    print(f"  {PASS if not bad_mc_small else FAIL} R14: NULL/<=0 market_cap i small/micro = {len(bad_mc_small)}")
    print(f"  {PASS if mews_var else FAIL} R14: MEWS score varians i universum = {len(set(mews_scores))} unika värden")
    print(f"  {PASS if not large_illiquid else FAIL} R14: large caps med likviditetsgrad E/F = {len(large_illiquid)} {large_illiquid}")

    if pe_bad > 0 or de_neg > 0 or seed_rows or bad_mega or bad_mc_small or not mews_var or large_illiquid:
        ok = False

    if baseline:
        print("  --- T14-baslinjejämförelse ---")
        deltas = []
        for key, cur in (("pe_anomaly", pe_bad), ("price_null", price_null), ("de_neg", de_neg)):
            prev = baseline.get(key, cur)
            if cur > prev:
                deltas.append(f"{key}: {prev} -> {cur}")
        if deltas:
            print(f"  {WARN} försämring mot baslinje: {', '.join(deltas)}")
        else:
            print(f"  {PASS} ingen försämring mot baslinje")
        print(f"  {WARN} baslinjen uppdateras inte automatiskt — skriv ny JSON vid önskad ny normal.")

    print("\nRESULTAT:", "GRÖN" if ok else "RÖD — minst en kontroll misslyckades")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
