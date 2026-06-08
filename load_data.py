# DEPRECATED — 2026-06-08
# load_data.py — Manuell engångsladdning av aktiedata från stock-scanner-fix till Supabase.
#
# Ersatt av: backend_worker/pipeline/entrypoint.py (kör via GitHub Actions)
# och backend_worker/db_loader.py (COPY-baserad bulk-laddning, 4× snabbare).
#
# Kvar enbart som referens. Kör INTE i produktion — använder gammal hårdkodad sökväg
# och Supabase-upsert (långsamt) istället för psycopg2 COPY.
# Kör från: marketscan-mappen med: python load_data.py

import os
import sys
import glob
import math
from datetime import date
from dotenv import load_dotenv

load_dotenv()

import pandas as pd

# ── Hitta senaste parquet-filer i gamla repot ─────────────────────────────────

OLD_REPO = r"C:\Users\hthur\OneDrive\Desktop\stock-scanner-fix"

def find_latest(pattern):
    files = sorted(glob.glob(os.path.join(OLD_REPO, "reports", pattern)), reverse=True)
    return files[0] if files else None

large_file    = find_latest("scored_universe_*.parquet")
smallcap_file = find_latest("smallcap_scored_*.parquet")

if not large_file:
    print("ERROR: Hittade ingen scored_universe_*.parquet i reports/")
    sys.exit(1)

print(f"Laddar: {os.path.basename(large_file)}")
df_large = pd.read_parquet(large_file)

if smallcap_file:
    print(f"Laddar: {os.path.basename(smallcap_file)}")
    df_small = pd.read_parquet(smallcap_file)
    df = pd.concat([df_large, df_small], ignore_index=True)
    df = df.drop_duplicates(subset="ticker", keep="last")
else:
    df = df_large

print(f"Totalt: {len(df)} aktier")

# ── Segment baserat på börsvärde (USD) ────────────────────────────────────────

def market_cap_to_segment(mc):
    if pd.isna(mc):
        return "mid_cap"
    if mc >= 10_000_000_000:
        return "large_cap"
    if mc >= 2_000_000_000:
        return "mid_cap"
    if mc >= 300_000_000:
        return "small_cap"
    return "micro_cap"

df["segment"] = df["market_cap"].apply(market_cap_to_segment)

# ── Kolumnmappning: gamla namn → scan_results-schema ─────────────────────────

df = df.rename(columns={
    "current_price": "price",
    "volatility":    "vol_20d",
})

df["change_pct"] = None
df["scan_date"]  = date.today().isoformat()

# ── Normalisera till exakt vad DB-constraints kräver ─────────────────────────
# Allowed: entry_signal IN ('STARK','OK','VÄNTA','EJ_AKTUELL')
# Allowed: confidence_label IN ('Hög','Medel','Låg')
# Allowed: trend_signal IN ('Upptrend','Sidled','Nedtrend')
# Okända värden → None (NULL) så constraint ej bryts

ENTRY_MAP = {
    "STARK": "STARK", "OK": "OK", "VÄNTA": "VÄNTA",
    "EJ AKTUELL": "EJ_AKTUELL", "EJ_AKTUELL": "EJ_AKTUELL",
}
CONFIDENCE_MAP = {
    "HÖG": "Hög", "Hög": "Hög",
    "MEDEL": "Medel", "Medel": "Medel",
    "LÅG": "Låg", "Låg": "Låg",
}
TREND_MAP = {
    "UPPTREND": "Upptrend", "Upptrend": "Upptrend",
    "SIDLED": "Sidled",    "Sidled": "Sidled",
    "NEDTREND": "Nedtrend", "Nedtrend": "Nedtrend",
    # VARNING finns ej i DB → None
}

def norm(v, mapping):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return mapping.get(str(v).strip(), None)  # okänt värde → None

if "entry_signal"    in df.columns: df["entry_signal"]    = df["entry_signal"].apply(lambda v: norm(v, ENTRY_MAP))
if "confidence_label" in df.columns: df["confidence_label"] = df["confidence_label"].apply(lambda v: norm(v, CONFIDENCE_MAP))
if "trend_signal"    in df.columns: df["trend_signal"]    = df["trend_signal"].apply(lambda v: norm(v, TREND_MAP))

# Välj de kolumner som finns i scan_results
KEEP = [
    "ticker", "name", "segment", "sector", "country",
    "score_total", "score_value", "score_quality", "score_momentum",
    "score_growth", "score_risk", "score_size", "score_dividend", "score_sentiment",
    "entry_signal", "confidence_label", "trend_signal",
    "predicted_return", "ml_rank", "piotroski_f",
    "price", "change_pct", "market_cap",
    "pe_trailing", "pe_forward", "roe", "roa",
    "gross_margin", "operating_margin",
    "revenue_growth", "earnings_growth",
    "dividend_yield", "debt_to_equity", "beta",
    "low_liquidity", "scan_date",
]

existing = [c for c in KEEP if c in df.columns]
df = df[existing].copy()

# Ersätt NaN / inf / -inf med None (JSON tillåter inte dessa värden)
import numpy as np
df = df.replace([np.inf, -np.inf], np.nan)
df = df.where(pd.notna(df), None)


if "low_liquidity" in df.columns:
    df["low_liquidity"] = df["low_liquidity"].fillna(False).astype(bool)

# Fyll saknat namn med ticker som fallback
if "name" in df.columns:
    df["name"] = df["name"].fillna(df["ticker"])

# Ta bort rader utan score_total (oanvändbara)
before = len(df)
if "score_total" in df.columns:
    df = df[df["score_total"].notna()].copy()
print(f"Filtrerade bort {before - len(df)} rader utan score_total. Kvar: {len(df)}")

print(f"Kolumner: {len(existing)}")
print(df[["ticker", "name", "segment", "score_total", "entry_signal"]].head())

# ── Ladda till Supabase via upsert ────────────────────────────────────────────

from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL eller SUPABASE_SERVICE_KEY saknas i .env")
    sys.exit(1)

sb = create_client(url, key)

BATCH = 200
# Kolumner som måste vara heltal i Postgres
INT_COLS = {"ml_rank", "piotroski_f"}

def clean_record(r):
    result = {}
    for k, v in r.items():
        if v is None:
            result[k] = None
        elif isinstance(v, float) and math.isnan(v):
            result[k] = None
        elif k in INT_COLS:
            result[k] = int(round(float(v)))
        else:
            result[k] = v
    return result

records = [clean_record(r) for r in df.to_dict("records")]
loaded = 0

for i in range(0, len(records), BATCH):
    batch = records[i:i + BATCH]
    sb.table("scan_results").upsert(batch, on_conflict="ticker").execute()
    loaded += len(batch)
    print(f"  {loaded}/{len(records)} laddade...")

print(f"\nKlart! {loaded} aktier laddade till Supabase.")
print("Gå till http://localhost:3000/screener för att se dem.")
