"""
factor_regime.py — QMJ-faktorregim ur AQR QMJ Monthly (nordisk komposit).

Källa: AQR "Quality Minus Junk: Factors, Monthly" (fri, ingen inloggning)
    https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Quality-Minus-Junk-Factors-Monthly.xlsx
    Sheet 'QMJ Factors', landskolumner för Norden (SWE/DNK/FIN/NOR) + aggregaten
    Europe/Global. Layout live-verifierad 2026-08-28: 31 kolumner
    ['DATE','AUS','AUT','BEL','CAN','CHE','DEU','DNK','ESP','FIN','FRA','GBR',
     'GRC','HKG','IRL','ISR','ITA','JPN','NLD','NOR','NZL','PRT','SGP','SWE',
     'USA','Global','Global Ex USA','Europe','North America','Pacific','None'],
    datum i kol A som M/D/YYYY, nordiska serier startar 07/31/1995.
    Header-raden hittas DYNAMISKT (rad där kol A == 'DATE') — matcha på namn,
    aldrig position (audit: aqrr läser A19:AD810, header ovanför rad 19).

Formel (audit qmj-regim-norden-2026-08-28.md):
    1. Nordisk komposit r_t = medel(SWE,DNK,FIN,NOR) — kräv ≥3 icke-NaN annars NaN.
    2. R12(t) = Π(1+r_s)−1 över de 12 senaste giltiga kompositmånaderna (kräv 12).
    3. pct(t) = (# R12_1..R12_t ≤ R12_t) / t — OOS-expanderande percentil (tie: ≤).
    4. Klass: n_obs < 240 → 'otillracklig'; pct ≥ 0.80 → 'stark'; pct ≤ 0.20 → 'svag';
       annars 'normal'. Europe/Global R12 beräknas också (rapport-only-hederlighet).

Hederlighet / varningsetiketter:
    - USD, ej valutahedgad; long-short, ej direkt investerbar (papperskonstrukt).
    - ~2 månaders uppdateringslag; AQR reviderar historik → ladda om hela filen varje körning.
    - Predikterbarhet är svag (Asness m.fl. 2017; Ilmanen m.fl. 2021) → detta är
      HISTORISK KONTEXT, aldrig en prognos/signal.

Sanity (WARNING, inte crash): 6 namngivna kolumner finns; ≥3 nordiska serier med
något icke-NaN; datumspann > 15 år. Vid fail skrivs INTE till DB, utan senast
kända värde rapporteras ur worker_state-nyckel 'factor_regime_last_ok'.

Användning:
    python -m backend_worker.factor_regime --dry-run
    python -m backend_worker.factor_regime
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import urllib.request
from datetime import date, datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

AQR_QMJ_URL = ("https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
               "Quality-Minus-Junk-Factors-Monthly.xlsx")
AQR_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SHEET_NAME = "QMJ Factors"

NORDIC_COUNTRIES = ["SWE", "DNK", "FIN", "NOR"]
REQUIRED_COLUMNS = NORDIC_COUNTRIES + ["Europe", "Global"]   # de 6 namngivna kolumnerna

WORKER_STATE_KEY = "factor_regime_last_ok"

MIN_N_OBS = 240             # 20 år av R12-observationer innan klassificering
STRONG_PCT = 0.80
WEAK_PCT = 0.20
MIN_NORDIC_VALID = 3        # ≥3 nordiska serier med något icke-NaN
MIN_DATE_SPAN_YEARS = 15.0

# Kolumnnamn i filen som är tomma/junk (den live-verifierade filen har en
# tom sista kolumn 'None') — tas bort vid läsning.
_JUNK_HEADERS = {"", "nan", "None", "Unnamed", "NaT"}


# ─── Hämtning ─────────────────────────────────────────────────────────────────

def _download_xlsx(url: str = AQR_QMJ_URL) -> bytes:
    """Ladda ner AQR QMJ Monthly-xlsx (hela filen varje gång — historik revideras)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": AQR_USER_AGENT,
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parsa datum-kolumnen. AQR skriver M/D/YYYY som text; hanterar även
    Excel-datetime-objekt. Fallback till generisk parsing om inget alls matchar."""
    parsed = []
    for v in series:
        if isinstance(v, (datetime, pd.Timestamp)):
            parsed.append(pd.Timestamp(v))
        else:
            txt = str(v).strip()
            if not txt or txt.lower() in ("nan", "nat", "none"):
                parsed.append(pd.NaT)
            else:
                parsed.append(pd.to_datetime(txt, format="%m/%d/%Y", errors="coerce"))
    out = pd.Series(parsed, index=series.index)
    if out.notna().sum() == 0:
        try:
            out = pd.to_datetime(series, errors="coerce")
        except Exception:
            pass
    return out


def read_aqr_frame(data: bytes) -> pd.DataFrame:
    """Läs AQR-xlsx → DataFrame med datum + de 6 behövda kolumnerna.

    Header-raden hittas dynamiskt: den rad där kolumn A == 'DATE'. Junk-kolumnen
    ('None'/namnlös) tas bort. Datum parsas och sorteras; numeriska kolumner
    koerceras med errors='coerce'.
    """
    raw = pd.read_excel(io.BytesIO(data), engine="openpyxl",
                        sheet_name=SHEET_NAME, header=None)

    header_idx = None
    for i in range(len(raw)):
        val = raw.iloc[i, 0]
        if isinstance(val, str) and val.strip().upper() == "DATE":
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Header-rad med 'DATE' hittades inte i sheet 'QMJ Factors'")

    frame = raw.iloc[header_idx + 1:].copy()
    frame.columns = [c.strip() if isinstance(c, str) else str(c).strip()
                     for c in raw.iloc[header_idx]]
    frame = frame[[c for c in frame.columns if c not in _JUNK_HEADERS]]

    have = ["DATE"] + [c for c in REQUIRED_COLUMNS if c in frame.columns]
    frame = frame[have]
    frame["DATE"] = _parse_dates(frame["DATE"])
    for c in REQUIRED_COLUMNS:
        if c in frame.columns:
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame = frame.dropna(subset=["DATE"]).sort_values("DATE").reset_index(drop=True)
    return frame


# ─── Regim-beräkning (rena funktioner, testbara utan DB) ──────────────────────

def compute_nordic_composite(frame: pd.DataFrame,
                             countries: list[str] | None = None) -> pd.Series:
    """Komposit r_t = rad-vis medel av (SWE,DNK,FIN,NOR); kräv ≥3 icke-NaN."""
    cols = [c for c in (countries or NORDIC_COUNTRIES) if c in frame.columns]
    valid = frame[cols].apply(pd.to_numeric, errors="coerce")
    n_valid = valid.notna().sum(axis=1)
    return valid.mean(axis=1).where(n_valid >= 3)


def rolling_12m(series: pd.Series) -> pd.Series:
    """R12(t) = Π(1+r_s)−1 över de 12 senaste GILTIGA månaderna; kräv 12 giltiga.

    NaN-gap hoppas över (senaste giltiga observationer bakåt från t).
    Positioner utan 12 giltiga → NaN.
    """
    vals = series.to_numpy(dtype="float64")
    out = pd.Series(np.nan, index=series.index, dtype="float64")
    for t in range(len(vals)):
        collected: list[float] = []
        i = t
        while i >= 0 and len(collected) < 12:
            v = vals[i]
            if not np.isnan(v):
                collected.append(float(v))
            i -= 1
        if len(collected) == 12:
            prod = 1.0
            for v in collected:
                prod *= (1.0 + v)
            out.iloc[t] = prod - 1.0
    return out


def oos_percentile(series: pd.Series) -> pd.Series:
    """OOS-expanderande percentil: pct(t) = (# R12_1..R12_t ≤ R12_t) / t.

    Expanderande fönster från första giltiga observation (Asness m.fl. 2017
    använder expanderande fönster för att undvika look-ahead). Ties räknas ≤.
    """
    out = pd.Series(np.nan, index=series.index, dtype="float64")
    hist: list[float] = []
    for t, v in enumerate(series):
        if pd.isna(v):
            continue
        hist.append(float(v))
        le = sum(1.0 for x in hist if x <= float(v))
        out.iloc[t] = le / len(hist)
    return out


def classify_regime(pct: float | None, n_obs: int) -> tuple[str, str]:
    """Klassificera regim + reason. Gränser: n<240 → otillracklig; pct≥0.80 →
    stark; pct≤0.20 → svag; annars normal."""
    if n_obs < MIN_N_OBS:
        return "otillracklig", f"otillracklig historik (n={n_obs})"
    if pct is None:
        return "otillracklig", "otillracklig historik (ingen percentil)"
    if pct >= STRONG_PCT:
        return "stark", f"12m-premie i {pct:.0%}-percentilen av historien (n={n_obs})"
    if pct <= WEAK_PCT:
        return "svag", f"12m-premie i {pct:.0%}-percentilen av historien (n={n_obs})"
    return "normal", f"12m-premie i {pct:.0%}-percentilen av historien (n={n_obs})"


def _at(vals: pd.Series, idx) -> float | None:
    """Värde vid index idx (eller None om NaN/saknas) — för europe_12m/global_12m."""
    if idx is None:
        return None
    v = vals.iloc[idx]
    if pd.isna(v):
        return None
    return round(float(v), 6)


def compute_regime(frame: pd.DataFrame) -> dict:
    """Full regim-beräkning ur en läst frame → resultat-dict (inget nätverk, ingen DB)."""
    comp = compute_nordic_composite(frame)
    r12 = rolling_12m(comp)
    pct = oos_percentile(r12)
    eu_r12 = rolling_12m(pd.to_numeric(frame.get("Europe", pd.Series(dtype=float)),
                                       errors="coerce"))
    gl_r12 = rolling_12m(pd.to_numeric(frame.get("Global", pd.Series(dtype=float)),
                                       errors="coerce"))

    last_idx = r12.last_valid_index()
    n_obs = int(r12.notna().sum())

    if last_idx is None:
        regime, reason = classify_regime(None, 0)
        premium = percentile = data_through = None
        last_dt: date | None = None
    else:
        premium = round(float(r12.iloc[last_idx]), 6)
        percentile = round(float(pct.iloc[last_idx]), 4)
        data_through_ts = frame["DATE"].iloc[last_idx]
        last_dt = data_through_ts.date()
        data_through = last_dt
        regime, reason = classify_regime(percentile, n_obs)

    return {
        "computed_date": date.today(),
        "data_through": data_through,
        "premium_12m": premium,
        "percentile": percentile,
        "n_obs": n_obs,
        "regime": regime,
        "reason": reason,
        "countries": list(NORDIC_COUNTRIES),
        "europe_12m": _at(eu_r12, last_idx),
        "global_12m": _at(gl_r12, last_idx),
        "last_index": last_idx,
        "last_date": last_dt,
    }


# ─── Sanity (WARNING, inte crash) ─────────────────────────────────────────────

def sanity_checks(frame: pd.DataFrame) -> list[str]:
    """Varningar (ej crash): 6 namngivna kolumner; ≥3 nordiska serier med data;
    datumspann > 15 år. Tom lista = allt OK."""
    warnings: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        warnings.append(f"saknade kolumner: {missing}")

    nordic_with_data = 0
    for c in NORDIC_COUNTRIES:
        if c in frame.columns and int(frame[c].notna().sum()) > 0:
            nordic_with_data += 1
    if nordic_with_data < MIN_NORDIC_VALID:
        warnings.append(f"för få nordiska serier med data ({nordic_with_data} av "
                        f"{len(NORDIC_COUNTRIES)} i {NORDIC_COUNTRIES})")

    if len(frame) >= 2 and frame["DATE"].notna().sum() >= 2:
        span_years = (frame["DATE"].max() - frame["DATE"].min()).days / 365.25
        if span_years <= MIN_DATE_SPAN_YEARS:
            warnings.append(f"datumspann för kort ({span_years:.1f} år ≤ "
                            f"{MIN_DATE_SPAN_YEARS:.0f} år)")
    elif len(frame) < 2:
        warnings.append(f"för få datarader ({len(frame)})")

    return warnings


# ─── DB ───────────────────────────────────────────────────────────────────────

def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def store_regime(result: dict) -> None:
    """Upsert av regim-rad + worker_state-markör 'factor_regime_last_ok'."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO factor_regime (
            computed_date, data_through, premium_12m, percentile, n_obs,
            regime, reason, countries, europe_12m, global_12m
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (computed_date) DO UPDATE SET
            data_through  = EXCLUDED.data_through,
            premium_12m   = EXCLUDED.premium_12m,
            percentile    = EXCLUDED.percentile,
            n_obs         = EXCLUDED.n_obs,
            regime        = EXCLUDED.regime,
            reason        = EXCLUDED.reason,
            countries     = EXCLUDED.countries,
            europe_12m    = EXCLUDED.europe_12m,
            global_12m    = EXCLUDED.global_12m,
            updated_at    = now()
    """, (
        result["computed_date"].isoformat(),
        result["data_through"].isoformat() if result["data_through"] else None,
        result["premium_12m"],
        result["percentile"],
        result["n_obs"],
        result["regime"],
        result["reason"],
        result["countries"],
        result["europe_12m"],
        result["global_12m"],
    ))
    cur.execute("""
        INSERT INTO worker_state (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """, (WORKER_STATE_KEY, json.dumps({
        "computed_date": result["computed_date"].isoformat(),
        "data_through": result["data_through"].isoformat() if result["data_through"] else None,
        "premium_12m": result["premium_12m"],
        "percentile": result["percentile"],
        "n_obs": result["n_obs"],
        "regime": result["regime"],
        "reason": result["reason"],
    }, default=str)))
    conn.commit()
    conn.close()


def read_last_known() -> dict | None:
    """Senast kända värde ur worker_state ('factor_regime_last_ok'); None om saknas."""
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT value FROM worker_state WHERE key = %s", (WORKER_STATE_KEY,))
        row = cur.fetchone()
        conn.close()
        if not row or not row[0]:
            return None
        return json.loads(row[0])
    except Exception:
        return None


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _summary(result: dict) -> dict:
    """JSON-print-version av resultatet (kort: inga DB-only fält)."""
    return {
        "status": "ok",
        "premium_12m": result["premium_12m"],
        "percentile": result["percentile"],
        "n_obs": result["n_obs"],
        "regime": result["regime"],
        "data_through": result["data_through"].isoformat() if result["data_through"] else None,
        "europe_12m": result["europe_12m"],
        "global_12m": result["global_12m"],
        "reason": result["reason"],
        "countries": result["countries"],
    }


def main():
    parser = argparse.ArgumentParser(description="QMJ-faktorregim (AQR, nordisk komposit)")
    parser.add_argument("--dry-run", action="store_true",
                        help="beräkna men skriv inte till DB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        data = _download_xlsx()
        frame = read_aqr_frame(data)
    except Exception as e:
        logger.error("Hämtning/parsing av AQR-xlsx misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

    warnings = sanity_checks(frame)
    if warnings:
        reason = "; ".join(warnings)
        logger.warning("Sanity-fail — skriver INTE till DB: %s", reason)
        out: dict = {"status": "warning", "reason": reason}
        if not args.dry_run and os.environ.get("DATABASE_URL"):
            last_known = read_last_known()
            if last_known is not None:
                out["last_known"] = last_known
        print(json.dumps(out, default=str))
        return

    result = compute_regime(frame)
    logger.info("Regim: %s (premium_12m=%s, pct=%s, n_obs=%s, data_tom=%s)",
                result["regime"], result["premium_12m"], result["percentile"],
                result["n_obs"], result["data_through"])

    if args.dry_run:
        print(json.dumps(_summary(result), default=str))
        return

    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL saknas — hoppar över DB-steg")
        print(json.dumps({**_summary(result), "status": "ok-no-db"}, default=str))
        return

    try:
        store_regime(result)
        print(json.dumps(_summary(result), default=str))
    except Exception as e:
        logger.error("DB-steg misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
