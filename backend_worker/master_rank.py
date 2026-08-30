"""
master_rank.py — ROND 8: Den auktoritativa rankningsmotorn (MasterRank).

Fuserar de två befintliga motorerna (score_total från externt repo + QMJ
alpha_rank) med fyra nya block:
  A) Värderingsgrind   — P/E vs egen 5-års historik + sektor-peers + PEG/absolut
  B) Analytikeruppsida — analyst_estimates (yfinance .info, target vs spot)
  C) Teknisk position  — RSI14/MA50/MA200/52v-hög (beräknas nu, lagras aldrig)
  D) Katalysatorfönster — catalyst_events (nästa rapport ≤45d → boost)

+ Anti-bubbla-grind: EXTREME_OVERVAL + OVERBOUGHT → rank capad till 60
  (BUBBLE_TRIAGE) — "bra bolag, priset har sprungit ikapp nyheterna".
+ PIT soft-block: QMJ:s allt-eller-inget ersätts med READY/PENDING/STALE;
  PENDING-rankas på tech/analyst istället för att försvinna.

Vikter i resources/weights.json (läsbar/editerbar; refresh via --reweight).

Användning:
    python -m backend_worker.master_rank --dry-run
    python -m backend_worker.master_rank --limit-tickers 5
    python -m backend_worker.master_rank --reweight   # skriver om vikter från factor_metrics
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WEIGHTS_PATH = Path(__file__).resolve().parent / "resources" / "weights.json"

# ── Tiers ─────────────────────────────────────────────────────────────────────
TIER_T1 = 75.0
TIER_T2 = 65.0
TIER_T3 = 50.0

# ── Anti-bubbla-grind ─────────────────────────────────────────────────────────
BUBBLE_CAP = 60.0           # max rank när EXTREME_OVERVAL + OVERBOUGHT
PEG_EXTREME = 2.5           # pe_forward / revenue_growth > 2.5 → EXTREME_OVERVAL
VAL_HIST_PCTL_EXTREME = 90.0  # P/E > 90:e percentil mot egen historik
RSI_OVERBOUGHT = 75.0
RSI_OVERSOLD = 30.0
PULLBACK_MIN, PULLBACK_MAX = -18.0, -5.0     # % från 52v-hög
ANALYST_MAX_SHARE = 0.15     # analyst_z capad: aldrig > 15 % av master_rank
RENORM_CAP = 1.5             # renormalisering (Rond 5-beslut: 1.5, ej 3.0)
IC_UP = 0.03
IC_DOWN = -0.02


# ═════════════════════════ PURE CORE (testbar; ingen nätverk/DB) ══════════════

def load_weights(path: Path = WEIGHTS_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"weights.json saknas: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _clip100(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return float(np.clip(x, 0.0, 100.0))


def _fmt_f(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)  # Decimal (psycopg2 NUMERIC) → float
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ── Block A: Värderingsgrind ──────────────────────────────────────────────────

def val_hist_z(pe_trailing: Optional[float], pe_history: Optional[list[float]]) -> Optional[float]:
    """P/E vs egen 5-års historik: percentil. Låg percentil = billig (hög z)."""
    if pe_trailing is None or not pe_history or len(pe_history) < 8:
        return None
    valid = [float(x) for x in pe_history if x is not None and x > 0]
    if not valid:
        return None
    pct = float(np.mean([1.0 if pe_trailing >= x else 0.0 for x in valid]) * 100.0)
    # percentil 0 = billigast → z = 100 - pct (vi vill att billig → hög z)
    return _clip100(float(100.0 - pct))


def val_peers_z(pe_trailing: Optional[float], peers: list[float]) -> Optional[float]:
    """P/E vs sektor-peers (≥15). Låg percentil = billig → hög z."""
    if pe_trailing is None or len(peers) < 15:
        return None
    valid = [float(x) for x in peers if x is not None and x > 0]
    if not valid:
        return None
    pct = float(np.mean([1.0 if pe_trailing >= x else 0.0 for x in valid]) * 100.0)
    return _clip100(float(100.0 - pct))


def val_abs_z(pe_forward: Optional[float], revenue_growth: Optional[float],
              ev_ebitda: Optional[float], value_z_qmj: Optional[float]) -> Optional[float]:
    """PEG/EV-justerad absolutvärdering (0-100). Högt PEG → låg z."""
    comps: list[float] = []
    if pe_forward and revenue_growth and revenue_growth > 0:
        peg = pe_forward / revenue_growth
        if peg <= PEG_EXTREME:
            comps.append(float(np.clip(100.0 - 40.0 * peg, 0.0, 100.0)))
        else:
            comps.append(0.0)
    if ev_ebitda is not None and ev_ebitda > 0:
        # EV/EBITDA 20x → 0; 5x → 100 (linjär, klämd)
        comps.append(float(np.clip(100.0 - (ev_ebitda - 5.0) / 15.0 * 100.0, 0.0, 100.0)))
    if value_z_qmj is not None:
        comps.append(float(value_z_qmj))
    if not comps:
        return None
    return _clip100(float(np.mean(comps)))


def val_flags(val_hist: Optional[float], val_peers: Optional[float],
              val_abs: Optional[float], peg: Optional[float], pe_hist_pctl: Optional[float]) -> list[str]:
    flags: list[str] = []
    if peg is not None and peg > PEG_EXTREME:
        flags.append("EXTREME_OVERVAL")
    if pe_hist_pctl is not None and pe_hist_pctl > VAL_HIST_PCTL_EXTREME:
        flags.append("EXTREME_OVERVAL")
    if val_hist is not None and val_hist >= 80 and val_peers is not None and val_peers >= 80:
        flags.append("CHEAP")
    return flags


# ── Block C: Teknisk position ────────────────────────────────────────────────

def tech_z(rsi: Optional[float], dist_high: Optional[float], ma200_dist: Optional[float],
           momentum_z: Optional[float]) -> Optional[float]:
    """Teknisk delscore 0-100. Kombinerar RSI-läge, avstånd från hög och MA200."""
    parts: list[float] = []
    if rsi is not None:
        # RSI 50 = neutral, 70+ = het (nära toppen), 30 = kall
        parts.append(float(np.clip(rsi, 0.0, 100.0)))
    if dist_high is not None:
        # -50 % från hög = 0, 0 % (på hög) = 100; straffa >0 (över hög = hävert)
        if dist_high > 0:
            parts.append(50.0)
        else:
            parts.append(float(np.clip(100.0 + dist_high * 2.0, 0.0, 100.0)))
    if ma200_dist is not None:
        parts.append(float(np.clip(50.0 + ma200_dist * 3.0, 0.0, 100.0)))
    if momentum_z is not None:
        parts.append(float(momentum_z))
    if not parts:
        return None
    return _clip100(float(np.mean(parts)))


# ── Block D: Katalysator ─────────────────────────────────────────────────────

def pit_status(fy_end: Optional[date], today: date) -> tuple[str, str]:
    """READY | PENDING (fy_end+5mån inte passerat) | STALE (data saknas).

    QMJ:s allt-eller-inget PIT-block ersätts med soft-block: PENDING ger inga
    QMJ-poäng men tech/analyst/catalyst räknas ändå.
    """
    if fy_end is None:
        return "STALE", "senaste årsbokslut ej giltigt (fy_end+5mån ej känd)"
    from calendar import month
    y, m = fy_end.year, fy_end.month
    due = date(y + (m + 5 - 1) // 12, ((m + 5 - 1) % 12) + 1, 1)
    if due > today:
        return "PENDING", f"fy_end+5mån ({due}) ej passerat"
    return "READY", ""


# ── Fusion ───────────────────────────────────────────────────────────────────

def tier_of(rank: Optional[float], excluded: bool, pit: str) -> str:
    if rank is None or excluded:
        return "EXCLUDED"
    if pit == "PENDING" and rank >= TIER_T1:
        return "T2"          # PENDING kan aldrig nå T1 (kvalitetsdata saknas)
    if rank >= TIER_T1:
        return "T1"
    if rank >= TIER_T2:
        return "T2"
    if rank >= TIER_T3:
        return "T3"
    return "T4"


def fuse(row: dict, weights: dict) -> dict:
    """Huvudfusion: viktad master_rank 0-100.

    row: {quality_z, value_z, momentum_z, analyst_z, insider_z, catalyst_z,
          payout_z, growth_z, val_flags, tech_flags, pit_status, ...}

    Regler (ROND 8 + Rond 5-beslut):
    - Renormalisering cap 1.5: saknade block uppväger ALDRIG mer än 1.5×
      kvarvarande vikt (annars 2-block → 100 % — tunna data ger topprank).
    - T1 kräver ≥6/8 giltiga block OCH pit_status=READY (annars T3-max).
    """
    blocks = ["quality", "value", "momentum", "analyst", "insider",
              "catalyst", "payout", "growth"]
    total_w = 0.0
    acc = 0.0
    missing: list[str] = []
    w = weights.get("weights", {})
    full_w = sum(float(w.get(b, 0.0)) for b in blocks)
    for b in blocks:
        v = row.get(f"{b}_z")
        if v is None:
            missing.append(b)
            continue
        bw = float(w.get(b, 0.0))
        if bw <= 0:
            missing.append(b)
            continue
        acc += float(v) * bw
        total_w += bw
    if total_w == 0:
        return {"master_rank": None, "data_missing": missing}

    # Renormaliseringscap (Rond 5): aldrig mer än 1.5× uppviktning
    max_w = full_w * RENORM_CAP
    if total_w > max_w:
        # Skala ned ACC så att effektiv vikt = max_w (reducerar tunna data)
        scale = max_w / total_w
        acc *= scale
        total_w = max_w

    # Cap: analyst aldrig > 15 % (nordisk small-cap-täckning tunn)
    analyst_raw = row.get("analyst_z")
    if analyst_raw is not None:
        analyst_contrib = float(analyst_raw) * float(w.get("analyst", 0.0))
        max_contrib = 0.15 * acc
        if analyst_contrib > max_contrib:
            scale = (acc - analyst_contrib) / (acc - (analyst_contrib - max_contrib)) if acc > 0 else 1.0
            acc = (acc - analyst_contrib) * scale + max_contrib
            analyst_contrib = max_contrib

    rank = float(acc) / total_w if total_w > 0 else None
    rank = _clip100(rank)

    # Katalysator-boost: händelser (rapport) ≤45 dagar ger +5 master-poäng
    boost = row.get("catalyst_boost", 0.0) or 0.0
    if boost > 0.0 and rank is not None:
        rank = _clip100(rank + float(boost))

    # Anti-bubbla-grind
    if "EXTREME_OVERVAL" in row.get("val_flags", []) and "OVERBOUGHT" in row.get("tech_flags", []):
        rank = min(rank, BUBBLE_CAP)
        missing.append("bubble_triage")

    # Datatäthet: T1 kräver ≥6/8 block. STALE-pit (QMJ ej rankad t.ex. globala
    # tickers) är INTE thin_data — det betyder bara "saknar QMJ-pelare".
    # PENDING hämmas (kvalitetsdata väntar). Thin data → max T3.
    n_valid = len([b for b in blocks if row.get(f"{b}_z") is not None])
    pit = row.get("pit_status", "READY")
    if n_valid < 6 or (pit == "PENDING"):
        if rank is not None and rank >= TIER_T3:
            rank = min(rank, 64.999)  # under T2-tröskeln
            missing.append("thin_data")

    # PENDING: kvalitetsdel får 0 (inte 50); rank redan beräknad med det
    if row.get("pit_status") == "PENDING":
        missing.append("pit_pending")

    rank = _fmt_f(rank)
    tier = tier_of(rank, False, row.get("pit_status", "READY"))
    # ROND 9: entry_signal härleds DETERMINISTISKT från MasterRank-tier så att
    # etiketten aldrig motsäger rank-siffran (PETR4 71/T2 vs gammal "Avvakta").
    entry_signal = signal_from_tier(tier)
    return {"master_rank": rank, "tier": tier, "entry_signal": entry_signal,
            "data_missing": missing,
            "bubble_triage": "BUBBLE_TRIAGE" if "bubble_triage" in missing else None}


def signal_from_tier(tier: str | None) -> str:
    """MasterRank-tier → entry_signal (motsv. köplägesetikett).

    T1 (≥75) → STARK · T2 (65-74) → OK · T3 (50-64) → VÄNTA ·
    T4 (<50) / EXCLUDED → EJ_AKTUELL.
    """
    if tier == "T1":
        return "STARK"
    if tier == "T2":
        return "OK"
    if tier == "T3":
        return "VÄNTA"
    return "EJ_AKTUELL"


def compute_table(values: list[dict], weights: dict) -> list[dict]:
    """Hela master_rank-tabellen från per-ticker inputs. Ren, testbar."""
    rows: list[dict] = []
    for v in values:
        fused = fuse(v, weights)
        row = dict(v)
        row.update({
            "master_rank": fused["master_rank"],
            "tier": fused.get("tier"),
            "entry_signal": fused.get("entry_signal"),
            "data_missing": json.dumps(fused["data_missing"]),
            "bubble_triage": fused.get("bubble_triage"),
        })
        rows.append(row)
    return rows


# ═════════════════════════ REWEIGHT (data-driven vikter) ═════════════════════

def reweight_from_ic(ic_map: dict, current: dict) -> dict:
    """Skriv om weights baserat på Rank-IC per faktor (factor_metrics).

    Regler: IC > +0.03 → uppvikt; IC < -0.02 → nedvikt +1 steg; |IC| låg → 0.
    Renormaliseras till 1.0. Returnerar ny weights-dict.
    """
    w = dict(current.get("weights", {}))
    base = w.copy()
    for fac in w:
        ic = ic_map.get(fac)
        if ic is None:
            continue
        if ic > IC_UP:
            w[fac] = base[fac] * 1.25
        elif ic < IC_DOWN:
            w[fac] = base[fac] * 0.75
        else:
            w[fac] = base[fac] * 0.9
    total = sum(w.values())
    if total > 0:
        w = {k: round(v / total, 4) for k, v in w.items()}
    return {**current, "weights": w}


# ═════════════════════════ DB-BYGGARE ═════════════════════════════════════════

def load_inputs(cur, today: date) -> list[dict]:
    """Samla alla inputs per ticker: scan_results + qmj_scores + analyst + catalyst + tech."""
    cur.execute("""
        SELECT ticker, score_total, score_quality, score_momentum, score_growth,
               score_value, score_dividend, price, pe_trailing, pe_forward, revenue_growth,
               market_cap, sector, dividend_yield, piotroski_f
        FROM scan_results
    """)
    scan = {}
    for (ticker, st, sq, sm, sg, sv, sdiv, price, pe_t, pe_f, rev_g, mcap, sector, div_y, piot) in cur.fetchall():
        scan[ticker] = {"score_total": st, "score_quality": sq, "score_momentum": sm,
                        "score_growth": sg, "score_value": sv, "score_dividend": sdiv,
                        "price": price, "pe_trailing": pe_t, "pe_forward": pe_f,
                        "revenue_growth": rev_g, "market_cap": mcap, "sector": sector,
                        "dividend_yield": div_y, "piotroski_f": piot}

    cur.execute("""
        SELECT ticker, quality_z, momentum_z, value_z, payout_z, insider_z,
               alpha_rank, exclusion_reason, as_of_date
        FROM qmj_scores
        WHERE scan_date = (SELECT MAX(scan_date) FROM qmj_scores)
    """)
    qmj = {}
    for (ticker, qz, mz, vz, pz, iz, ar, ex, aod) in cur.fetchall():
        qmj[ticker] = {"quality_z": qz, "momentum_z": mz, "value_z": vz,
                       "payout_z": pz, "insider_z": iz, "alpha_rank": ar,
                       "exclusion_reason": ex, "as_of_date": aod}

    cur.execute("""
        SELECT ticker, target_median, target_count, upside_pct, recommendation_mean,
               analyst_flags, currency, target_dispersion
        FROM analyst_estimates
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM analyst_estimates)
    """)
    analyst = {}
    for (ticker, tm, tc, up, rm, afl, cur_cy, disp) in cur.fetchall():
        analyst[ticker] = {"target_median": tm, "target_count": tc,
                           "upside_pct": up, "recommendation_mean": rm,
                           "analyst_flags": afl or [],
                           "currency": cur_cy, "target_dispersion": disp}

    cur.execute("""
        SELECT ticker, event_type, event_date, days_until, confidence
        FROM catalyst_events
    """)
    cat_map: dict[str, list] = {}
    for r in cur.fetchall():
        cat_map.setdefault(r[0], []).append({
            "event_type": r[1], "event_date": r[2], "days_until": r[3], "confidence": r[4]})

    return scan, qmj, analyst, cat_map


def master_rank_run(cur, weights: dict, dry_run: bool = False) -> dict:
    today = date.today()
    scan, qmj, analyst, cat_map = load_inputs(cur, today)

    # Separat historia: val_hist_z behöver historisk P/E.
    # score_history har INGEN pe_trailing (migration 020) — bygg P/E-historia
    # approximerat: price (score_history) / eps_ttm (earnings_surprises, ttm =
    # summa av 4 senaste kvartalens eps_actual). Fallback: None = ingen historik.
    cur.execute("""
        SELECT ticker, scan_date, price
        FROM score_history
        WHERE price IS NOT NULL AND price > 0 AND scan_date > %s
        ORDER BY ticker, scan_date
    """, ((today - time_delta_years(5)).isoformat(),))
    price_hist: dict[str, list[tuple[str, float]]] = {}
    for r in cur.fetchall():
        price_hist.setdefault(r[0], []).append((r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1])[:10], float(r[2])))

    # Earnings (TTM) per ticker från earnings_surprises (publicerade kvartal)
    cur.execute("""
        SELECT ticker, announced_on, eps_actual
        FROM earnings_surprises
        WHERE eps_actual IS NOT NULL
        ORDER BY ticker, announced_on
    """)
    eps_hist: dict[str, list[tuple[str, float]]] = {}
    for r in cur.fetchall():
        eps_hist.setdefault(r[0], []).append((r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1])[:10], float(r[2])))

    # Bygg pe_hist: för varje pris-datum, ttm-eps = summa av 4 senaste kvartal ≥ datum - 365d
    pe_hist: dict[str, list[float]] = {}
    for t, prices in price_hist.items():
        eps_pts = eps_hist.get(t, [])
        if not eps_pts:
            continue
        for pd, price in prices:
            pd_date = date.fromisoformat(pd)
            year_before = pd_date - time_delta_years(1)
            qs = [e for ed, e in eps_pts if ed >= year_before.isoformat() and ed <= pd]
            if len(qs) >= 2:  # minst 2 kvartal för en meningsfull ttm
                ttm = float(sum(qs[-4:]))
                if ttm > 0:
                    pe_hist.setdefault(t, []).append(price / ttm)

    # Sektorpeers
    peers_by_sector: dict[str, list[float]] = {}
    for t, row in scan.items():
        sec = row["sector"]
        pe = row["pe_trailing"]
        if sec and pe and pe > 0:
            peers_by_sector.setdefault(sec, []).append(float(pe))

    from backend_worker.technical_snapshot import compute_technical, _read_history, fetch_price_history

    values: list[dict] = []
    # Förhämtning av prishistorik (yfinance) — QMJ-cachen finns sällan på servern,
    # så tech-blocken måste hämta kurserna själva (cachad 7 d i data/qmj_raw/).
    from concurrent.futures import ThreadPoolExecutor
    import threading
    tech_cache: dict[str, dict] = {}
    lock = threading.Lock()
    tickers_list = list(scan.keys())

    def _tech(tk: str):
        closes = _read_history(tk)
        if closes is None:
            closes = fetch_price_history(tk)   # hämtar + cachar
        if closes:
            with lock:
                tech_cache[tk] = compute_technical(closes)

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(_tech, tickers_list))

    for t, s in scan.items():
        q = qmj.get(t, {})
        a = analyst.get(t, {})
        evs = cat_map.get(t, [])
        tech = tech_cache.get(t, {})

        pe_t = s["pe_trailing"]
        pe_f = s["pe_forward"]
        rev_g = s["revenue_growth"]
        sector = s["sector"]

        val_h = val_hist_z(pe_t, pe_hist.get(t, []))
        val_p = val_peers_z(pe_t, peers_by_sector.get(sector, [])) if sector else None
        peg = (pe_f / rev_g) if (pe_f and rev_g and rev_g > 0) else None
        val_a = val_abs_z(pe_f, rev_g, None, q.get("value_z"))
        pe_hist_pctl = None
        if pe_hist.get(t) and pe_t:
            valid = [x for x in pe_hist[t] if x > 0]
            if valid:
                pe_hist_pctl = float(np.mean([1.0 if pe_t >= x else 0.0 for x in valid]) * 100.0)
        vflags = val_flags(val_h, val_p, val_a, peg, pe_hist_pctl)

        rsi = tech.get("rsi_14")
        dist_high = tech.get("dist_52w_high_pct")
        ma200_d = tech.get("ma200_dist_pct")
        tz = tech_z(rsi, dist_high, ma200_d, q.get("momentum_z"))

        fy_end = q.get("as_of_date")
        fy_date = None
        # Om QMJ inte har rankat tickern (globala tickers utan QMJ-rad) →
        # NO_QMJ (ingen data, inte stale). Endast när QMJ-rad finns men
        # as_of_date saknas → STALE (gammal/okänd bokslutsdata).
        if q:
            if fy_end:
                try:
                    fy_date = date.fromisoformat(str(fy_end)[:10])
                except Exception:
                    fy_date = None
            pit, pit_reason = pit_status(fy_date, today)
        else:
            pit, pit_reason = "NO_QMJ", "QMJ har inte utvärderat denna aktie (endast nordiska)"

        # Quality: QMJ quality_z (weight 0) om PENDING; annars medel med score_quality
        qu = q.get("quality_z")
        if pit == "PENDING":
            qu = None
        quality_z = _fmt_f(np.mean([float(x) for x in [qu, s["score_quality"]] if x is not None]) if (qu is not None or s["score_quality"] is not None) else None)

        # Value: QMJ value_z + val_blend + score_value-fallback
        vq = q.get("value_z")
        val_blocks = [float(x) for x in [vq, val_h, val_p, val_a, s["score_value"]] if x is not None]
        value_z = _fmt_f(np.mean(val_blocks)) if val_blocks else None

        # Momentum: QMJ momentum_z + score_momentum + tech_z
        mum = [float(x) for x in [q.get("momentum_z"), s["score_momentum"], tz] if x is not None]
        momentum_z = _fmt_f(np.mean(mum)) if mum else None
        tech_z_f = _fmt_f(tz)

        # Analyst: analyst_z från rec (från analyst_fetcher-analytik).
        # ROND 9: dispersion-penalty — bred riktkursspridning = osäkerhet →
        # dämpar analyst_z (PETR4-fallet: spann 37-63 BRL).
        from backend_worker.analyst_fetcher import analyst_z as _az
        az = _az({"upside_pct": a.get("upside_pct"), "recommendation_mean": a.get("recommendation_mean"),
                  "target_count": a.get("target_count")})
        disp = a.get("target_dispersion")
        if az is not None and disp is not None:
            disp = float(disp)
            # dispersion 0.0 → ingen straff; ≥2.0 → max 50 % straff
            penalty = max(0.0, min(0.5, disp / 4.0))
            az = _fmt_f(az * (1.0 - penalty))

        # Catalyst
        from backend_worker.catalyst_fetcher import catalyst_z as _cz, catalyst_boost as _cb
        cz = _cz(evs, today)
        cb = _cb(evs, today)
        next_ev = None
        for e in evs:
            if e.get("days_until") is not None and e["days_until"] >= 0:
                if next_ev is None or e["days_until"] < next_ev[1]:
                    next_ev = (e.get("event_date", "").isoformat() if hasattr(e.get("event_date"), "isoformat") else str(e.get("event_date", ""))[:10],
                               e["days_until"])
        catalyst_next = f"{next_ev[0]}:earnings" if next_ev else None
        catalyst_days = next_ev[1] if next_ev else None

        # Insider / payout / growth — QMJ-pelare med scan_results-fallback
        # (QMJ körs bara för nordiska; globala tickers får fallback från scan
        # så att blocken inte är tomma och thin_data inte händer i onödan).
        iz = q.get("insider_z")
        pz = q.get("payout_z")
        gz = s["score_growth"]
        scv = s["score_value"]     # fallback till värde-blocket
        if iz is None:
            iz = 50.0 + (s["piotroski_f"] - 4.5) * 8.0   # piotroski-proxy 0-100
            iz = float(np.clip(iz, 0.0, 100.0))
        if pz is None:
            pz = s["score_dividend"]   # utdelningsscore som payout-proxy

        values.append({
            "ticker": t,
            "quality_z": quality_z,
            "value_z": value_z,
            "momentum_z": momentum_z,
            "analyst_z": _fmt_f(az),
            "tech_z": tech_z_f,
            "insider_z": _fmt_f(iz),
            "catalyst_z": _fmt_f(cz),
            "catalyst_boost": cb,
            "payout_z": _fmt_f(pz),
            "growth_z": _fmt_f(gz),
            "val_hist_z": _fmt_f(val_h),
            "val_peers_z": _fmt_f(val_p),
            "val_abs_z": _fmt_f(val_a),
            "val_flags": vflags,
            "analyst_upside": a.get("upside_pct"),
            "analyst_count": a.get("target_count"),
            "analyst_flags": a.get("analyst_flags", []),
            "target_dispersion": disp,
            "rsi_14": rsi,
            "ma50_dist_pct": tech.get("ma50_dist_pct"),
            "ma200_dist_pct": tech.get("ma200_dist_pct"),
            "dist_52w_high_pct": tech.get("dist_52w_high_pct"),
            "trend_tech": tech.get("trend_tech"),
            "tech_flags": tech.get("tech_flags"),
            "catalyst_next": catalyst_next,
            "catalyst_days": catalyst_days,
            "pit_status": pit,
            "pit_reason": pit_reason,
            "currency": a.get("currency"),
            "exclusion_reason": q.get("exclusion_reason"),
        })

    table = compute_table(values, weights)
    return {"table": table, "scan": scan}


def time_delta_years(years: int):
    """Datum för N år sedan (forecast-säkert)."""
    from datetime import timedelta
    return timedelta(days=years * 365)


def upsert_master(cur, table: list[dict], today: date, scan: dict) -> int:
    written = 0
    for r in table:
        t = r["ticker"]
        s = scan.get(t, {})
        try:
            cur.execute("""
                INSERT INTO master_rank (
                    ticker, scan_date, master_rank, tier,
                    quality_z, value_z, momentum_z, analyst_z, tech_z, insider_z,
                    catalyst_z, payout_z, growth_z,
                    val_hist_z, val_peers_z, val_abs_z, val_flags,
                    analyst_upside, analyst_count, analyst_flags,
                    rsi_14, ma50_dist_pct, ma200_dist_pct, dist_52w_high_pct,
                    trend_tech, tech_flags,
                    catalyst_next, catalyst_days, pit_status, pit_reason,
                    exclusion_reason, warning_flags, data_missing, currency
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, scan_date) DO UPDATE SET
                    master_rank = EXCLUDED.master_rank,
                    tier = EXCLUDED.tier,
                    quality_z = EXCLUDED.quality_z,
                    value_z = EXCLUDED.value_z,
                    momentum_z = EXCLUDED.momentum_z,
                    analyst_z = EXCLUDED.analyst_z,
                    tech_z = EXCLUDED.tech_z,
                    insider_z = EXCLUDED.insider_z,
                    catalyst_z = EXCLUDED.catalyst_z,
                    payout_z = EXCLUDED.payout_z,
                    growth_z = EXCLUDED.growth_z,
                    val_hist_z = EXCLUDED.val_hist_z,
                    val_peers_z = EXCLUDED.val_peers_z,
                    val_abs_z = EXCLUDED.val_abs_z,
                    val_flags = EXCLUDED.val_flags,
                    analyst_upside = EXCLUDED.analyst_upside,
                    analyst_count = EXCLUDED.analyst_count,
                    analyst_flags = EXCLUDED.analyst_flags,
                    rsi_14 = EXCLUDED.rsi_14,
                    ma50_dist_pct = EXCLUDED.ma50_dist_pct,
                    ma200_dist_pct = EXCLUDED.ma200_dist_pct,
                    dist_52w_high_pct = EXCLUDED.dist_52w_high_pct,
                    trend_tech = EXCLUDED.trend_tech,
                    tech_flags = EXCLUDED.tech_flags,
                    catalyst_next = EXCLUDED.catalyst_next,
                    catalyst_days = EXCLUDED.catalyst_days,
                    pit_status = EXCLUDED.pit_status,
                    pit_reason = EXCLUDED.pit_reason,
                    exclusion_reason = EXCLUDED.exclusion_reason,
                    warning_flags = EXCLUDED.warning_flags,
                    data_missing = EXCLUDED.data_missing,
                    currency = EXCLUDED.currency
            """, (t, today.isoformat(),
                  r.get("master_rank"), r.get("tier"),
                  r.get("quality_z"), r.get("value_z"), r.get("momentum_z"),
                  r.get("analyst_z"), r.get("tech_z"), r.get("insider_z"), r.get("catalyst_z"),
                  r.get("payout_z"), r.get("growth_z"),
                  r.get("val_hist_z"), r.get("val_peers_z"), r.get("val_abs_z"),
                  json.dumps(r.get("val_flags", [])),
                  r.get("analyst_upside"), r.get("analyst_count"),
                  json.dumps(r.get("analyst_flags", [])),
                  r.get("rsi_14"), r.get("ma50_dist_pct"), r.get("ma200_dist_pct"),
                  r.get("dist_52w_high_pct"), r.get("trend_tech"),
                  json.dumps(r.get("tech_flags", [])),
                  r.get("catalyst_next"), r.get("catalyst_days"),
                  r.get("pit_status"), r.get("pit_reason"),
                  r.get("exclusion_reason"),
                  json.dumps([]),
                  r.get("data_missing", "[]"),
                  r.get("currency")))
            written += 1
            # ROND 9: skriv tillbaka entry_signal till scan_results så att
            # köplägesetiketten alltid speglar MasterRank-tier.
            try:
                cur.execute("""
                    UPDATE scan_results SET entry_signal = %s
                    WHERE ticker = %s
                """, (r.get("entry_signal", "EJ_AKTUELL"), t))
            except Exception as e:
                logger.warning("backfill entry_signal %s misslyckades: %s", t, e)
        except Exception as e:
            logger.warning("upsert master_rank %s misslyckades: %s", t, e)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="MasterRank-körning (ROND 8)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-tickers", type=int, default=0)
    parser.add_argument("--reweight", action="store_true", help="Uppdatera vikter från factor_metrics")
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        # Demo med mock-data (tester)
        today = date.today()
        from datetime import timedelta
        demo = [{
            "ticker": "DEMO-A", "quality_z": 88.0, "value_z": 20.0, "momentum_z": 95.0,
            "analyst_z": 70.0, "insider_z": 60.0, "catalyst_z": 80.0,
            "payout_z": 55.0, "growth_z": 75.0, "val_flags": ["EXTREME_OVERVAL"],
            "tech_flags": ["OVERBOUGHT"], "pit_status": "READY",
            "val_hist_z": 10.0, "val_peers_z": 5.0, "val_abs_z": 15.0,
            "analyst_upside": 3.0, "analyst_count": 5, "rsi_14": 78.0,
            "ma50_dist_pct": 5.0, "ma200_dist_pct": 15.0, "dist_52w_high_pct": 1.0,
            "trend_tech": "Upptrend", "catalyst_next": None, "catalyst_days": None,
        }]
        weights = load_weights()
        table = compute_table(demo, weights)
        for r in table:
            print(f"{r['ticker']}: rank={r['master_rank']} tier={r['tier']} "
                  f"flags={r['val_flags']} {r['tech_flags']} missing={r['data_missing']}")
        return

    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL saknas")
        return
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    if args.reweight:
        cur.execute("""
            SELECT factor, rank_ic FROM factor_metrics
            WHERE computed_date = (SELECT MAX(computed_date) FROM factor_metrics)
        """)
        ic_map = {r[0]: float(r[1]) for r in cur.fetchall() if r[1] is not None}
        weights = reweight_from_ic(ic_map, load_weights())
        WEIGHTS_PATH.write_text(json.dumps(weights, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Vikter uppdaterade: %s", weights["weights"])
        conn.close()
        return

    weights = load_weights()
    t0 = time.time()
    result = master_rank_run(cur, weights, args.dry_run)
    table = result["table"]
    if args.limit_tickers and args.limit_tickers > 0:
        table = table[:args.limit_tickers]
    logger.info("Beräknade %d master_rank-rader på %.1f s", len(table), time.time() - t0)

    if args.print:
        for r in sorted(table, key=lambda x: x["master_rank"] or -1, reverse=True)[:20]:
            print(f"{r['ticker']}: {r['master_rank']} {r['tier']} pit={r['pit_status']} "
                  f"val={r['val_flags']} tech={r['tech_flags']}")

    today = date.today()
    written = upsert_master(cur, table, today, result["scan"])
    conn.commit()
    conn.close()
    logger.info("Skrev %d master_rank-rader för %s", written, today)


if __name__ == "__main__":
    main()
