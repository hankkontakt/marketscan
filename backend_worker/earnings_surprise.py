"""
earnings_surprise.py — TS-SUE (standardiserad kvartalsöverraskning) per ticker.

Källa: yfinance `earnings_dates` (konsensus-estimat, utfall och surprise % per
kvartal, med annonseringstidpunkt = PIT-nyckel). Verifierat live 2026-08-28 för
MYCR.ST / SIVE.ST / BOOZT.ST (3/3): index = tz-aware annonce-timestamps
(America/New_York), kolumner ['EPS Estimate', 'Reported EPS', 'Surprise(%)'],
NaN i 'Reported EPS' = kommande kvartal.

ÄRLIGHET (viktigt):
- SUE är ett MÅTT på kvartalsöverraskning, ALDRIG en prediktion. Variabelnamn
  och prints säger "surprise"/"measure", inte "signal"/"forecast".
- Yahoo-konsensus kan bygga på få analytiker (särskilt nordiska småbolag) — en
  SUE-z från ett tunt konsensus är mindre informativ. Datan är vad den är.
- PIT-snapshot: för kommande kvartal sparas estimatet FÖRE annonsering
  (estimate_source='snapshot'). När utfallet landar används snapshot-estimatet
  om det fångades före annonsering (captured_at < announce_at); annars
  Yahoo-estimatet i efterhand (estimate_source='retro'). Retro-rader
  överskriver ALDRIG en giltig snapshot-rad.
- surprise_pct lagras som Yahoo:s 'Surprise(%)' (konsensus-baserad) för alla
  rader; snapshot-estimatet styr bara den lagrade eps_estimate (PIT-ärlighet
  för själva estimatet). För snapshot-rader är surprise_pct därför inte exakt
  återberäkningsbar ur (eps_estimate, eps_actual).

SUE-formel (per publicerat kvartal):
    z = surprise_t / std(surprises över upp till 8 TIDIGARE kvartal)
    krav: >= 4 giltiga tidigare kvartal, std > 0; z clip ±3.
    surprise på %-skala (std i samma skala — z är skalenlig).
    std = population std (statistics.pstdev) över fönstret.

Chunkad körning (sedan 2026-08-29): Yahoo throttlar GH-runnern — en full
156-ticker-körning överskrider 60-min-job-timeout (två körningar CANCELLED).
Varje körning bearbetar max CHUNK_SIZE (60) tickers; worker_state-nyckeln
'earnings_surprise_cursor' pekar på nästa chunk, så successiva veckor
ackumulerar tills hela universumet är täckt (sedan wrap). --force/--full =
fullkörning (ignorerar cursorn, manuellt).

Användning:
    python -m backend_worker.earnings_surprise --dry-run   # beräkna, skriv inte
    python -m backend_worker.earnings_surprise             # skriv till DB (chunk)
    python -m backend_worker.earnings_surprise --full      # fullkörning (ignorerar cursor)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "fi_raw"

FETCH_SLEEP_MIN = 1.2          # sekunder — yfinance rate-limitar
FETCH_SLEEP_MAX = 2.0
FETCH_RETRIES = 1              # 1 retry utöver första försöket
RETRY_SLEEP = 2.0
FETCH_TIMEOUT_SECONDS = 20     # hård gräns per yfinance-anrop — ett hängande
                               # Yahoo-anrop får ALDRIG blockera steget
                               # (worst case 60 × 20 s = 20 min < job-timeout 90 min)

CHUNK_SIZE = 60                # max tickers per körning — Yahoo throttlar GH-
                               # runnern; en full 156-ticker-körning överskrider
                               # 60-min-job-timeout. Chunkade körningar
                               # ackumulerar över successiva veckor via cursorn.

SUE_MAX_PRIOR = 8              # upp till 8 tidigare kvartal i std-fönstret
SUE_MIN_PRIOR = 4              # kräv minst 4 giltiga tidigare kvartal
SUE_CLIP = 3.0                 # z clip ±3

WORKER_STATE_KEY = "earnings_surprise_last_run"
CURSOR_STATE_KEY = "earnings_surprise_cursor"   # {"next_index": int, "updated_at": iso}
RECENT_RUN_HOURS = 23          # logga-notis om senaste körning var < 23 h sedan

# Fallback-universum för --dry-run utan DATABASE_URL (lokal smoke-test).
DRY_RUN_FALLBACK_UNIVERSE = ["MYCR.ST", "SIVE.ST", "BOOZT.ST"]


# ─── Pure funktioner ──────────────────────────────────────────────────────────

def pick_chunk(tickers: list[str], cursor: int, chunk: int) -> tuple[list[str], int]:
    """Välj nästa chunk ur universum + nästa cursor (pure funktion).

    Returnerar (tickers[cursor:cursor+chunk], next_cursor). next_cursor =
    cursor+chunk om det finns fler tickers kvar, annars 0 (wrap — nästa
    körning börjar om från början). Tomt universum → ([], 0). Negativ cursor
    klampas till 0 (korrupt worker_state ska aldrig processa fel tickers).
    """
    if not tickers:
        return [], 0
    cursor = max(0, cursor)
    end = cursor + chunk
    if end >= len(tickers):
        return tickers[cursor:], 0
    return tickers[cursor:end], end


def compute_sue(prior_surprises: list[float]) -> float | None:
    """SUE-z för ett kvartal (pure funktion).

    `prior_surprises` = surprise-serien för kvartalet som ska poängsättas OCH
    dess föregångare, senaste först. Element 0 = aktuella kvartalets surprise
    (surprise_t); element 1..8 = de upp till 8 senaste TIDIGARE kvartalen
    (None-värden filtreras bort). Kräver >= 4 giltiga tidigare kvartal och
    std > 0. z = surprise_t / std(priors), clip ±3. None om kraven ej uppfylls.
    """
    if not prior_surprises:
        return None
    surprise_t = prior_surprises[0]
    if surprise_t is None:
        return None
    priors = [x for x in prior_surprises[1 : 1 + SUE_MAX_PRIOR] if x is not None]
    if len(priors) < SUE_MIN_PRIOR:
        return None
    try:
        std = statistics.pstdev(priors)
    except statistics.StatisticsError:
        return None
    if std <= 0:
        return None
    z = surprise_t / std
    return max(-SUE_CLIP, min(SUE_CLIP, z))


def select_estimate_source(snapshot_eps, snapshot_captured_at, yahoo_eps,
                           announce_at) -> tuple[float | None, str]:
    """Välj PIT-ärligt estimat för en publicerad rad (pure funktion).

    Snapshot-estimatet används bara om det fångades FÖRE annonsering
    (captured_at < announce_at) — annars kan det vara reviderat i efterhand
    och Yahoo-estimatet (retro) vinner. Returnerar (eps_estimate, source).
    """
    if (snapshot_eps is not None and snapshot_captured_at is not None
            and snapshot_captured_at < announce_at):
        return snapshot_eps, "snapshot"
    return yahoo_eps, "retro"


def _to_float(val) -> float | None:
    """NaN/None → None, annars float."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if pd.isna(f):
        return None
    return f


def process_earnings_frame(df: pd.DataFrame, ticker: str, now: datetime) -> dict:
    """Dela earnings_dates-framen i publicerade + snapshot-rader.

    - Index (America/New_York) konverteras till UTC; announced_on = UTC-datum.
    - Rader med announce > now (framtida) SKIPAS från SUE-beräkning men blir
      snapshot-kandidater (estimat fångat före annonsering).
    - Publicerade rader (actual närvarande, announce <= now) får SUE-z.
    - Returnerar {"published": [...], "snapshots": [...]}.
    """
    published: list[dict] = []
    snapshots: list[dict] = []
    if df is None or df.empty:
        return {"published": published, "snapshots": snapshots}

    frame = df.copy()
    if getattr(frame.index, "tz", None) is not None:
        frame.index = frame.index.tz_convert("UTC")

    records: list[dict] = []
    for ts, row in frame.iterrows():
        announce_at = ts.to_pydatetime()
        if announce_at.tzinfo is None:
            announce_at = announce_at.replace(tzinfo=timezone.utc)
        records.append({
            "ticker": ticker,
            "announced_on": announce_at.date(),
            "announce_at": announce_at,
            "eps_estimate": _to_float(row.get("EPS Estimate")),
            "eps_actual": _to_float(row.get("Reported EPS")),
            "surprise_pct": _to_float(row.get("Surprise(%)")),
        })

    # Dedup på announced_on (PK) — behåll senaste (framen är sorterad fallande)
    seen: set[date] = set()
    unique: list[dict] = []
    for rec in records:
        if rec["announced_on"] in seen:
            continue
        seen.add(rec["announced_on"])
        unique.append(rec)

    for rec in unique:
        if rec["eps_actual"] is None:
            snapshots.append(rec)          # kommande kvartal → snapshot-kandidat
        elif rec["announce_at"] > now:
            logger.warning("%s: actual finns men announce i framtiden (%s) — "
                           "hoppar över (dataanomali)", ticker, rec["announced_on"])
        else:
            published.append(rec)

    # SUE per publicerat kvartal: priors = upp till 8 senaste tidigare kvartal
    published.sort(key=lambda r: r["announce_at"], reverse=True)
    for i, rec in enumerate(published):
        window = [p["surprise_pct"] for p in published[i + 1 : i + 1 + SUE_MAX_PRIOR]]
        rec["sue"] = compute_sue([rec["surprise_pct"]] + window)

    return {"published": published, "snapshots": snapshots}


# ─── Hämtning ─────────────────────────────────────────────────────────────────

def _fetch_earnings_dates_once(ticker: str) -> pd.DataFrame:
    """Ett yfinance-anrop (körs i daemon-tråd av fetch_earnings_dates)."""
    import yfinance as yf
    df = yf.Ticker(ticker).earnings_dates
    if df is None:
        raise ValueError("earnings_dates returnerade None")
    return df


def _run_with_hard_timeout(fn, timeout: float):
    """Kör `fn` i en daemon-tråd med hård tidsgräns.

    Daemon-tråd (inte ThreadPoolExecutor): CPython joinar icke-daemon-trådar
    vid interpreter shutdown, så en hängande ThreadPoolExecutor-tråd skulle
    blockera process-exit i slutet av steget (verifierat lokalt). En daemon-
    tråd dör med processen — hänget kan aldrig förlänga steget.
    """
    import queue
    import threading

    result_q: queue.Queue = queue.Queue(maxsize=1)

    def _worker():
        try:
            result_q.put(("ok", fn()))
        except BaseException as e:  # noqa: BLE001 — fånga ALLT i tråden
            result_q.put(("err", e))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    try:
        status, payload = result_q.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError(f"timeout efter {timeout:g}s") from None
    if status == "err":
        raise payload
    return payload


def fetch_earnings_dates(ticker: str) -> pd.DataFrame:
    """Hämta earnings_dates med 1 retry. Rate-limiting sköts av anroparen.

    Hård tidsgräns per anrop (FETCH_TIMEOUT_SECONDS): ett hängande Yahoo-anrop
    får aldrig blockera steget. Vid timeout skippas tickern DIREKT (ingen
    retry — worst case 156 × 20 s ≈ 52 min < job-timeout 60 min); en senare
    körning omhämtar skippade tickers. Övriga fel får 1 retry som tidigare.
    """
    last_err: Exception | None = None
    for attempt in range(FETCH_RETRIES + 1):
        try:
            return _run_with_hard_timeout(
                lambda: _fetch_earnings_dates_once(ticker),
                FETCH_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning("%s: fetch TIMEOUT efter %ds — skippar ticker "
                           "(omhämtas vid nästa körning)",
                           ticker, FETCH_TIMEOUT_SECONDS)
            raise
        except Exception as e:
            last_err = e
            logger.warning("%s: fetch-försök %d/%d misslyckades: %s",
                           ticker, attempt + 1, FETCH_RETRIES + 1, e)
            if attempt < FETCH_RETRIES:
                time.sleep(RETRY_SLEEP)
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"{ticker}: earnings_dates fetch misslyckades utan fel")


def _frame_to_records(df: pd.DataFrame) -> list[dict]:
    """Rå earnings_dates → JSON-vänliga records (för arkiv)."""
    if df is None or df.empty:
        return []
    frame = df.copy()
    if getattr(frame.index, "tz", None) is not None:
        frame.index = frame.index.tz_convert("UTC")
    out: list[dict] = []
    for ts, row in frame.iterrows():
        out.append({
            "announce_at": ts.isoformat(),
            "eps_estimate": _to_float(row.get("EPS Estimate")),
            "eps_actual": _to_float(row.get("Reported EPS")),
            "surprise_pct": _to_float(row.get("Surprise(%)")),
        })
    return out


def _archive_raw(payload: dict) -> None:
    """Spara rå earnings_dates per körning (felsökningsarkiv, data/fi_raw)."""
    try:
        RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_ARCHIVE_DIR / f"earnings_dates_{date.today().isoformat()}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                        encoding="utf-8")
        logger.info("Rått arkiv sparat: %s", path.name)
    except Exception as e:
        logger.warning("Rått arkiv misslyckades: %s", e)


# ─── DB ───────────────────────────────────────────────────────────────────────

def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def load_universe(cur) -> list[str]:
    """Universum: listade tickers ur registret (sorterat — chunk-cursorn
    kräver stabil ordning mellan körningar)."""
    cur.execute(
        "SELECT ticker FROM universe_registry "
        "WHERE status = 'listed' AND ticker IS NOT NULL "
        "ORDER BY ticker"
    )
    return [row[0] for row in cur.fetchall()]


def upsert_earnings_surprises(conn, published: list[dict], snapshots: list[dict]) -> dict:
    """Skriv publicerade + snapshot-rader till earnings_surprises.

    Retro-rader överskriver ALDRIG en giltig snapshot-rad. Skyddet ligger i
    python (SELECT + select_estimate_source) OCH i SQL: CASE-guard på
    eps_estimate samt WHERE eps_actual IS NULL för snapshot-uppdateringar.

    COMMIT sköts av anroparen — samma transaktion som worker_state-cursorn,
    så cursorn avancerar bara om datan faktiskt skrivs.
    """
    cur = conn.cursor()
    written = snapshot_written = 0

    for rec in published:
        cur.execute(
            "SELECT eps_estimate, estimate_source, captured_at FROM earnings_surprises "
            "WHERE ticker = %s AND announced_on = %s",
            (rec["ticker"], rec["announced_on"]),
        )
        existing = cur.fetchone()
        snapshot_eps = existing[0] if existing and existing[1] == "snapshot" else None
        captured_at = existing[2] if existing else None
        eps_estimate, source = select_estimate_source(
            snapshot_eps, captured_at, rec["eps_estimate"], rec["announce_at"])

        cur.execute("""
            INSERT INTO earnings_surprises (
                ticker, announced_on, announce_at, eps_estimate, eps_actual,
                surprise_pct, sue, estimate_source, captured_at, computed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (ticker, announced_on) DO UPDATE SET
                announce_at = EXCLUDED.announce_at,
                eps_estimate = CASE
                    WHEN earnings_surprises.estimate_source = 'snapshot'
                         AND earnings_surprises.captured_at < EXCLUDED.announce_at
                    THEN earnings_surprises.eps_estimate
                    ELSE EXCLUDED.eps_estimate
                END,
                eps_actual = EXCLUDED.eps_actual,
                surprise_pct = EXCLUDED.surprise_pct,
                sue = EXCLUDED.sue,
                estimate_source = EXCLUDED.estimate_source,
                captured_at = COALESCE(earnings_surprises.captured_at, EXCLUDED.captured_at),
                computed_at = NOW()
        """, (
            rec["ticker"], rec["announced_on"], rec["announce_at"], eps_estimate,
            rec["eps_actual"], rec["surprise_pct"], rec["sue"], source,
            None,  # retro-rader har ingen snapshot → captured_at NULL
        ))
        written += 1

    for rec in snapshots:
        cur.execute("""
            INSERT INTO earnings_surprises (
                ticker, announced_on, announce_at, eps_estimate, eps_actual,
                surprise_pct, sue, estimate_source, captured_at, computed_at
            ) VALUES (%s, %s, %s, %s, NULL, NULL, NULL, 'snapshot', NOW(), NOW())
            ON CONFLICT (ticker, announced_on) DO UPDATE SET
                announce_at = EXCLUDED.announce_at,
                eps_estimate = EXCLUDED.eps_estimate,
                estimate_source = 'snapshot',
                captured_at = NOW()
            WHERE earnings_surprises.eps_actual IS NULL
        """, (
            rec["ticker"], rec["announced_on"], rec["announce_at"], rec["eps_estimate"],
        ))
        snapshot_written += 1

    return {"rows": written, "snapshots": snapshot_written}


def _last_run_age_hours() -> float | None:
    """Timmar sedan senaste körning (worker_state). None om aldrig kört/DB-fel."""
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT updated_at FROM worker_state WHERE key = %s", (WORKER_STATE_KEY,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        ts = row[0]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
    except Exception:
        return None


def _write_worker_state(conn, stats: dict) -> None:
    """Upsert earnings_surprise_last_run till worker_state.

    COMMIT sköts av anroparen — samma transaktion som upsert + cursor.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO worker_state (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """, (WORKER_STATE_KEY, json.dumps({
        "last_run": datetime.now(timezone.utc).isoformat(),
        "tickers": stats.get("tickers", 0),
        "rows": stats.get("rows", 0),
        "snapshots": stats.get("snapshots", 0),
        "errors": stats.get("errors", []),
    })))


def _load_cursor(conn) -> int:
    """Läs earnings_surprise_cursor ur worker_state → next_index (int).

    Ingen rad / ogiltigt värde → 0 (börja från början). DB-fel → 0 (samma
    transaktion skrivs ändå inte — nästa körning tar om chunken).
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM worker_state WHERE key = %s", (CURSOR_STATE_KEY,))
        row = cur.fetchone()
        if row:
            value = row[0]
            if isinstance(value, dict):
                return int(value.get("next_index", 0))
            if isinstance(value, str):
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return int(parsed.get("next_index", 0))
        return 0
    except Exception as e:
        logger.warning("Cursor-läsning misslyckades — startar från 0: %s", e)
        return 0


def _save_cursor(conn, next_index: int) -> None:
    """Upsert earnings_surprise_cursor till worker_state.

    Skrivs i SAMMA transaktion som earnings_surprises-upserten (commit sköts
    av anroparen) — cursorn avancerar bara om datan också skrivs.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO worker_state (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """, (CURSOR_STATE_KEY, json.dumps({
        "next_index": next_index,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TS-SUE: standardiserad kvartalsöverraskning (mått, inte prediktion)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--full", action="store_true",
                        help="fullkörning — ignorerar worker_state-cursorn")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    full_run = args.force or args.full
    db_url = os.environ.get("DATABASE_URL")
    tickers: list[str] = []
    if db_url:
        conn0 = _connect()
        try:
            tickers = load_universe(conn0.cursor())
        finally:
            conn0.close()
        age = _last_run_age_hours()
        if age is not None and age < RECENT_RUN_HOURS and not args.force:
            logger.info("Senaste körning var för %.1f h sedan (< %d h) — kör ändå "
                        "(veckovis snapshot behöver uppdateras). --force tystar notisen.",
                        age, RECENT_RUN_HOURS)
    elif args.dry_run:
        tickers = list(DRY_RUN_FALLBACK_UNIVERSE)
        logger.warning("DATABASE_URL saknas — --dry-run använder fallback-universum: %s",
                       tickers)
    else:
        logger.warning("DATABASE_URL saknas — hoppar över DB-steg")
        print(json.dumps({"status": "ok-no-db", "tickers": 0, "rows": 0,
                          "snapshots": 0, "errors": []}))
        return

    # Chunkad körning: max CHUNK_SIZE tickers per run (Yahoo throttlar GH-
    # runnern — en full 156-ticker-körning överskred 60-min-job-timeout).
    # Cursor i worker_state ('earnings_surprise_cursor') pekar på nästa chunk;
    # successiva veckor ackumulerar tills hela universumet är täckt (sedan
    # wrap). --force/--full = fullkörning (ignorerar cursorn).
    cursor = 0
    if db_url and not full_run:
        conn_c = _connect()
        try:
            cursor = _load_cursor(conn_c)
        finally:
            conn_c.close()
    chunk_tickers, next_cursor = pick_chunk(tickers, cursor, CHUNK_SIZE)
    logger.info("Chunk: %d/%d tickers (cursor %d → nästa %d%s)",
                len(chunk_tickers), len(tickers), cursor, next_cursor,
                ", fullkörning" if full_run else "")

    now = datetime.now(timezone.utc)
    published: list[dict] = []
    snapshots: list[dict] = []
    errors: list[str] = []
    raw_archive: dict[str, list] = {}

    for ticker in chunk_tickers:
        try:
            df = fetch_earnings_dates(ticker)
            raw_archive[ticker] = _frame_to_records(df)
            res = process_earnings_frame(df, ticker, now)
            published.extend(res["published"])
            snapshots.extend(res["snapshots"])
            logger.info("%s: %d publicerade kvartal, %d snapshot-kandidater",
                        ticker, len(res["published"]), len(res["snapshots"]))
        except Exception as e:
            errors.append(f"{ticker}: {e}")
            logger.warning("Per-ticker-fel %s: %s", ticker, e)
        time.sleep(random.uniform(FETCH_SLEEP_MIN, FETCH_SLEEP_MAX))
    _archive_raw(raw_archive)

    if args.dry_run:
        print(json.dumps({
            "status": "ok", "dry_run": True,
            "tickers": len(chunk_tickers), "rows": len(published),
            "snapshots": len(snapshots), "errors": errors,
            "next_cursor": next_cursor,
        }))
        return

    if not db_url:
        print(json.dumps({"status": "ok-no-db", "tickers": len(chunk_tickers),
                          "rows": len(published), "snapshots": len(snapshots),
                          "errors": errors}))
        return

    try:
        conn = _connect()
        try:
            stats = upsert_earnings_surprises(conn, published, snapshots)
            _write_worker_state(conn, {"tickers": len(chunk_tickers), **stats,
                                       "errors": errors})
            _save_cursor(conn, next_cursor)
            conn.commit()   # EN transaktion: data + last-run + cursor
        finally:
            conn.close()
        print(json.dumps({"status": "ok", "tickers": len(chunk_tickers),
                          **stats, "errors": errors, "next_cursor": next_cursor}))
    except Exception as e:
        logger.error("DB-steg misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e),
                          "tickers": len(chunk_tickers), "rows": len(published),
                          "snapshots": len(snapshots), "errors": errors}))
        sys.exit(1)


if __name__ == "__main__":
    main()