"""
Bulk-loads scored scan results into Supabase Postgres via COPY.
Uses copy_expert() (51s → 13s vs to_sql on 1200-row scans).
"""
import io
import os
import logging
import psycopg2
import pandas as pd
from datetime import date

logger = logging.getLogger(__name__)

SCAN_COLUMNS = [
    "ticker", "name", "segment", "sector", "country",
    "score_total", "score_value", "score_quality", "score_momentum",
    "score_growth", "score_risk", "score_size", "score_dividend", "score_sentiment",
    "entry_signal", "confidence_label", "trend_signal",
    "predicted_return", "ml_rank", "piotroski_f",
    "price", "change_pct", "market_cap", "pe_trailing", "pe_forward",
    "pe_trailing_raw", "pe_forward_raw",
    "roe", "roa", "revenue_growth", "earnings_growth",
    "roe_raw", "roa_raw", "revenue_growth_raw", "earnings_growth_raw",
    "debt_to_equity", "current_ratio", "gross_margin", "operating_margin",
    "dividend_yield", "beta", "vol_20d",
    "low_liquidity", "has_holding", "scan_date",
    # MEWS (#3)
    "mews_score", "mews_flag", "mews_candidate", "mews_fcf_yield", "mews_small_size",
    "mews_low_ps", "mews_operating_leverage", "mews_revenue_accel", "mews_clean_accruals",
    # Ensemble / uncertainty (#15)
    "ml_uncertainty", "ml_flag_uncertain", "regime_at_scan",
]

SEGMENT_THRESHOLDS = {
    "large_cap":  10_000_000_000,   # USD
    "mid_cap":    2_000_000_000,    # USD
    "small_cap":  300_000_000,      # USD
}

# Static FX rates → USD.  Updated 2026-08-28; refresh periodically.
# Used to normalise market_cap values before applying USD thresholds.
# NOTE 2026-08-28: 10 currencies were missing (BRL, GBp, HKD, INR, KRW, MXN,
# NZD, PLN, SGD, TWD) → fell back to 1:1 → ~97 rows classified ~10x too big
# (inflated large_cap). GBp = GBP per pence (0.01 × 1.27).
_FX_TO_USD: dict[str, float] = {
    "USD": 1.0,
    "SEK": 0.093,   # 1 SEK ≈ 0.093 USD
    "EUR": 1.08,
    "GBP": 1.27,
    "GBp": 0.0127,  # 1 pence ≈ 0.0127 USD
    "NOK": 0.092,
    "DKK": 0.145,
    "CHF": 1.12,
    "CAD": 0.74,
    "AUD": 0.65,
    "JPY": 0.0066,
    "INR": 0.0112,
    "HKD": 0.128,
    "KRW": 0.00073,
    "TWD": 0.031,
    "SGD": 0.765,
    "BRL": 0.175,
    "PLN": 0.255,
    "MXN": 0.053,
    "NZD": 0.60,
}


def _to_usd(market_cap: float | None, currency: str | None) -> float | None:
    """Return market_cap in USD. Falls back to 1:1 if currency is unknown."""
    if market_cap is None or market_cap <= 0:
        return market_cap
    rate = _FX_TO_USD.get((currency or "USD").upper(), 1.0)
    return market_cap * rate


def _apply_sanity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sista försvarslinje (ROND 5, 2026-08-30): sanera rådata INNAN COPY till DB.

    Bakgrund: nyare code (data_fetcher._sanity_check) normaliserar vid hämtning,
    men gamla/allvarliga parquet-filer (scored_universe_2026-08-29) innehåller
    råvärden (pe=-4.07, divY=0.44 i %, de=-34) som annars skrivs rakt in i
    scan_results via COALESCE/EXCLUDED. Reglerna speglar data_fetcher._sanity_check,
    utan sector/gm (görs ändå i stock-scanner — här skyddas bara omöjliga värden).

    Alla normaliseringar görs på DataFrame-nivå (vektoriserat) och loggas.
    """
    import numpy as np
    import pandas as pd

    def _is_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce")

    # 1. P/E: icke-finit/<=1/>200 → NA (fångar negativa yfinance-värden)
    #    dessutom pe < 6 → NA (yfinance .info ger ibland ~1-5 istället för 20-40:
    #    META 1.15, KO 2.41, APP 3.68, CME 3.66, LIN 5.18, LLY 5.59)
    #    ROND 10: *_raw-kolumner (råvärden före neutralisering) får INTE <6-regeln
    #    — de är sanna värden, inte residualer. Endast icke-finit/<=0/>1000 → NA.
    for col in ("pe_trailing", "pe_forward"):
        if col in df.columns:
            v = _is_num(df[col])
            if col.endswith("_raw"):
                df[col] = v.mask(~np.isfinite(v) | (v <= 0) | (v > 1000))
            else:
                df[col] = v.mask(~np.isfinite(v) | (v <= 1) | (v > 200) | (v < 6))

    # 2. dividend_yield: %-värden (0.44 = 0.44 %) → fraktion (0.0044);
    #    redan-fraktion (<=0.1) lämnas; >1 dubbel-saneras (redan /100).
    #    ROND 6: rate-baserad beräkning (enhetsfri) vinner om tillgänglig.
    if "dividend_yield" in df.columns:
        v = _is_num(df["dividend_yield"])
        frac = v.copy()
        if "dividend_rate" in df.columns and (
            "current_price" in df.columns or "price" in df.columns
        ):
            rate = _is_num(df["dividend_rate"])
            price_col = "current_price" if "current_price" in df.columns else "price"
            price = _is_num(df[price_col])
            computed = rate / price.where(price > 0)
            use_rate = rate.notna() & price.gt(0)
            frac = frac.where(~use_rate, computed)
        frac.loc[v > 1] = v.loc[v > 1] / 100
        no_rate = ~((df.get("dividend_rate", pd.Series(np.nan, index=df.index))).notna()) \
            if "dividend_rate" in df.columns else pd.Series(True, index=df.index)
        frac.loc[(v > 0.1) & (v <= 1) & no_rate] = (v.loc[(v > 0.1) & (v <= 1) & no_rate]) / 100
        df["dividend_yield"] = frac.mask(~np.isfinite(frac) | (frac < 0))

    # 3. debt_to_equity: negativt → 0 (nettokassa), >200 → NA
    if "debt_to_equity" in df.columns:
        v = _is_num(df["debt_to_equity"])
        df["debt_to_equity"] = v.mask(~np.isfinite(v), other=None).clip(lower=0.0)
        df["debt_to_equity"] = df["debt_to_equity"].mask(df["debt_to_equity"] > 200)

    # 4. current_ratio: negativt → 0, >20 → NA
    if "current_ratio" in df.columns:
        v = _is_num(df["current_ratio"])
        df["current_ratio"] = v.mask(~np.isfinite(v), other=None).clip(lower=0.0)
        df["current_ratio"] = df["current_ratio"].mask(df["current_ratio"] > 20)

    # 5. roe/roa/gm/operating_margin: |v| > 5 → NA
    #    dessutom: negativ gm för icke-finansiella → NA (yfinance-skrap:
    #    GE -0.13, ACN -0.18, 000270.KS -0.18 — alla positiva live)
    # ROND 9: ROE/ROA == 0 → NA (ett lönsamt bolag har aldrig exakt 0 % ROE;
    #    "0 %" i UI var en TTM/artefakt — t.ex. 2914.T med temporärt negativt kvartal).
    # ROND 10: *_raw får INTE |v|>5 → NA (råvärden kan vara >5, t.ex. stora P/E).
    for col in ("roe", "roa", "gross_margin", "operating_margin"):
        if col in df.columns:
            v = _is_num(df[col])
            if col.endswith("_raw"):
                df[col] = v.mask(~np.isfinite(v))
            else:
                df[col] = v.mask(~np.isfinite(v) | (v.abs() > 5) | (v == 0))
            if col == "gross_margin":
                sect = (
                    df["sector"].fillna("").astype(str)
                    if "sector" in df.columns
                    else pd.Series("", index=df.index)
                )
                non_fin = ~sect.isin(
                    ["Financial Services", "Real Estate", "Insurance"]
                )
                df[col] = df[col].mask((df[col] < 0) & non_fin)

    return df


def _derive_segment(market_cap_usd: float | None) -> str:
    """Map USD market cap to segment string."""
    if market_cap_usd is None or pd.isna(market_cap_usd) or market_cap_usd <= 0:
        return "unknown"
    mc = float(market_cap_usd)
    if 0 < mc < 1_000_000:
        logger.warning("market_cap %s scaled by 1e6 as probable million-unit -> %s", mc, mc * 1_000_000)
        mc *= 1_000_000
    if mc > 1e13:
        logger.warning("market_cap %s unusually large (>1e13 USD)", mc)
    if mc >= SEGMENT_THRESHOLDS["large_cap"]:
        return "large_cap"
    if mc >= SEGMENT_THRESHOLDS["mid_cap"]:
        return "mid_cap"
    if mc >= SEGMENT_THRESHOLDS["small_cap"]:
        return "small_cap"
    return "micro_cap"


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["scan_date"] = date.today().isoformat()

    if "segment" not in df.columns:
        # ROND 6 (2026-08-30): parquetens market_cap är REDAN USD (data_fetcher.
        # _sanity_check konverterar currency != USD via _FX_TO_USD). Att köra
        # _to_usd här dubbelkonverterar (6098.T 167.9B USD x 0.0066 = 1.1B USD
        # i DB). Använd mcap direkt; > 1e12 = nästan säkert nativ valuta -> som
        # storleksordning ändå "large_cap" via _derive_segment (ingen FX).
        df["segment"] = [
            _derive_segment(mc)
            for mc in df.get("market_cap", pd.Series(dtype=float))
        ]

    # ROND 5 (2026-08-30) — KORRIGERAD 2026-08-30 (ROND 6):
    # market_cap är redan USD-normaliserad av stock-scanner data_fetcher._sanity_check
    # (rad 7: currency != USD -> * FX-tabell). Att konvertera IGEN i db_loader
    # dubbelkonverterade: 6098.T 167.9B USD (parquet) x 0.0066 = 1.1B USD (fel!).
    # Denna lista-konvertering är därför BORTTAGEN. Segment-beräkningen ovan
    # använder _to_usd endast för KLASSIFICERING (konservativ).
    # Om en källa ändå levererar nativ valuta fångas det av den gamla
    # market_cap > 1e12-regeln vid nästa pipekörning (finns ej här).


    if "has_holding" not in df.columns:
        df["has_holding"] = False

    # Clamp scores to [0, 100]
    for col in [c for c in df.columns if c.startswith("score_")]:
        df[col] = df[col].clip(0, 100)

    # Cast integer columns — parquet stores these as float (e.g. 12.8 → 13)
    # Postgres INTEGER columns reject non-integer strings from COPY.
    for int_col in ("ml_rank", "piotroski_f"):
        if int_col in df.columns:
            df[int_col] = (
                pd.to_numeric(df[int_col], errors="coerce")
                .round()
                .astype("Int64")   # nullable int — NaN stays NULL, not "nan"
            )

    # Map legacy entry_signal strings — must match CHECK constraint values
    signal_map = {
        "STARK": "STARK", "OK": "OK",
        "VÄNTA": "VÄNTA", "EJ AKTUELL": "EJ_AKTUELL",
        "EJ_AKTUELL": "EJ_AKTUELL",
    }
    if "entry_signal" in df.columns:
        df["entry_signal"] = df["entry_signal"].map(signal_map).fillna("EJ_AKTUELL")

    # P1-2: Normalize confidence_label — raw pipeline uses caps Swedish ('HÖG', 'MEDEL', 'LÅG')
    # CHECK constraint requires title-case ('Hög', 'Medel', 'Låg')
    confidence_map = {
        "HÖG": "Hög", "MEDEL": "Medel", "LÅG": "Låg",
        "Hög": "Hög", "Medel": "Medel", "Låg": "Låg",
    }
    if "confidence_label" in df.columns:
        df["confidence_label"] = df["confidence_label"].map(confidence_map)
        # NULL is allowed — leave unknown values as None (NaN)

    # P1-2: Normalize trend_signal — raw pipeline uses 'UPPTREND', 'NEDTREND', 'VARNING', 'SIDLED'
    # CHECK constraint requires 'Upptrend', 'Nedtrend', 'Sidled'; VARNING has no valid mapping → NULL
    trend_map = {
        "UPPTREND": "Upptrend", "NEDTREND": "Nedtrend",
        "SIDLED": "Sidled",
        "Upptrend": "Upptrend", "Nedtrend": "Nedtrend", "Sidled": "Sidled",
        "VARNING": None,  # No valid CHECK value — store as NULL
    }
    if "trend_signal" in df.columns:
        df["trend_signal"] = df["trend_signal"].map(trend_map)
        # Values not in map become NaN → NULL in Postgres (allowed by schema)

    # P0-fix: källa producerar 'current_price' (stock-scanner data_fetcher), DB-kolumnen heter 'price'
    if "current_price" in df.columns and "price" not in df.columns:
        df["price"] = df["current_price"]
    elif "current_price" in df.columns:
        # Båda finns → behåll äkta price, fallback till current_price
        df["price"] = df["price"].fillna(df["current_price"])

    # ROND 5 (2026-08-30): sista försvarslinjen — sanera omöjliga/%-värden innan de
    # skrivs till DB. Skyddar mot gamla parquet-filer och yfinance-rådata.
    df = _apply_sanity(df)

    # Keep only known columns; add missing ones as NULL
    for col in SCAN_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Boolean columns: source parquet may hold NaN/None (e.g. a ticker that was
    # never MEWS-evaluated). na_rep="" in COPY would write an explicit NULL that
    # bypasses the column DEFAULT false and later breaks API schema validation
    # (ResponseValidationError on /api/scan) — coerce to False instead.
    for bool_col in ("low_liquidity", "has_holding", "mews_flag", "mews_candidate",
                     "ml_flag_uncertain"):
        df[bool_col] = df[bool_col].fillna(False).astype(bool)

    return df[SCAN_COLUMNS]


def load_scan(
    df: pd.DataFrame,
    dsn: str | None = None,
    *,
    replace: bool = True,
    min_keep_fraction: float = 0.7,
) -> int:
    """
    Ladda scored df till scan_results (via staging-tabell + UPSERT).

    replace=True   → FULL ombyggnad: upsertar alla rader OCH raderar tickers som
                     inte finns i denna scan. Endast för weekly (hela universumet).
                     EXCLUDED-värden är auktoritativa (skriver även över med NULL).
    replace=False  → PARTIELL: upsertar bara df:ens tickers och raderar ALDRIG övriga.
                     Använder COALESCE → en NULL i inkommande data skriver ALDRIG
                     över ett befintligt icke-NULL-värde (förstör inte priser/betyg).
                     För morning/evening/manual/smallcap (sub-scans som inte täcker
                     hela universumet).

    Skyddsnät: även med replace=True degraderas körningen till partiell UPSERT om
    den skulle krympa universumet till < min_keep_fraction av nuvarande storlek
    (en trasig/partiell parquet som råkar köras som 'full' får inte radera allt).

    Returnerar antal rader i scan_results efter laddning.
    """
    dsn = dsn or os.environ["DATABASE_URL"]
    prepared = _prepare_df(df)
    cols = SCAN_COLUMNS
    col_list = ",".join(cols)

    # ROND 5: logga antalet sanerade rader (kollar bara nyckelkolumner)
    problematic = int(
        prepared["dividend_yield"].gt(0.1).sum()
        + prepared["pe_trailing"].le(1).sum()
        + prepared["debt_to_equity"].lt(0).sum()
    )
    if problematic:
        logger.info("load_scan sanity: %d rader med skräpvärden sanerade (divY/pe/de)", problematic)

    buf = io.StringIO()
    prepared.to_csv(buf, index=False, header=False, na_rep="", encoding="utf-8")
    buf.seek(0)

    with psycopg2.connect(dsn, client_encoding="UTF8") as con:
        con.autocommit = False
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scan_results;")
            existing = cur.fetchone()[0]
            new_n = len(prepared)

            do_replace = replace
            if replace and existing > 0 and new_n < existing * min_keep_fraction:
                logger.warning(
                    "load_scan: full replace skulle krympa universumet %d→%d "
                    "(<%.0f%%) — degraderar till UPSERT för att skydda data",
                    existing, new_n, min_keep_fraction * 100,
                )
                do_replace = False

            # Auktoritativ (weekly): EXCLUDED vinner. Partiell: behåll icke-NULL.
            if do_replace:
                update_set = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "ticker")
            else:
                update_set = ", ".join(
                    f"{c}=COALESCE(EXCLUDED.{c}, scan_results.{c})"
                    for c in cols if c != "ticker"
                )

            # Staging-tabell (COPY kan inte upserta direkt)
            cur.execute(
                "CREATE TEMP TABLE _scan_in (LIKE scan_results INCLUDING DEFAULTS) "
                "ON COMMIT DROP;"
            )
            cur.copy_expert(
                f"COPY _scan_in ({col_list}) FROM STDIN WITH (FORMAT csv, NULL '')",
                buf,
            )
            # Dedup inom inkommande data (annars 'cannot affect row a second time')
            cur.execute(
                "DELETE FROM _scan_in a USING _scan_in b "
                "WHERE a.ctid < b.ctid AND a.ticker = b.ticker;"
            )
            # Upsert
            cur.execute(
                f"INSERT INTO scan_results ({col_list}) "
                f"SELECT {col_list} FROM _scan_in "
                f"ON CONFLICT (ticker) DO UPDATE SET {update_set};"
            )
            # Full replace → städa bort tickers som inte längre finns i scanen
            if do_replace:
                cur.execute(
                    "DELETE FROM scan_results "
                    "WHERE ticker NOT IN (SELECT ticker FROM _scan_in);"
                )
        con.commit()
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scan_results;")
            n = cur.fetchone()[0]

    logger.info("scan_results loaded: %d rows (replace=%s, in=%d, was=%d)",
                n, do_replace, new_n, existing)
    return n


def log_pipeline_run(
    run_type: str,
    status: str,
    tickers_ok: int = 0,
    tickers_err: int = 0,
    duration_s: float = 0,
    error_msg: str | None = None,
    dsn: str | None = None,
) -> None:
    dsn = dsn or os.environ["DATABASE_URL"]
    with psycopg2.connect(dsn) as con, con.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs SET status=%s, tickers_ok=%s, tickers_err=%s,
              duration_s=%s, error_msg=%s, finished_at=NOW()
            WHERE run_type=%s AND status='running'
              AND started_at = (
                SELECT MAX(started_at) FROM pipeline_runs WHERE run_type=%s AND status='running'
              )
            """,
            (status, tickers_ok, tickers_err, duration_s, error_msg, run_type, run_type),
        )
        if cur.rowcount == 0:
            cur.execute(
                """INSERT INTO pipeline_runs (run_type, status, tickers_ok, tickers_err,
                     duration_s, error_msg, finished_at)
                   VALUES (%s,%s,%s,%s,%s,%s,NOW())""",
                (run_type, status, tickers_ok, tickers_err, duration_s, error_msg),
            )
        con.commit()
