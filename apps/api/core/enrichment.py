"""Shared enrichment logic — merges scan_results fields into items."""
import logging

logger = logging.getLogger(__name__)

ENRICH_COLUMNS = "ticker, name, price, change_pct, score_total, entry_signal, trend_signal"

# Fallback-källor när scan_results saknar rad för tickern (t.ex. ny listning
# som ännu inte hunnit in i scan-pipelinen). universe_registry ger basdata,
# qmj_scores ger QMJ-fälten (senaste scan_date-raden per ticker).
REGISTRY_FALLBACK_COLUMNS = "ticker, name, market"
QMJ_FALLBACK_COLUMNS = "ticker, alpha_rank, quality_z, momentum_z, value_z, stratum"
QMJ_FALLBACK_FIELDS = ("alpha_rank", "quality_z", "momentum_z", "value_z", "stratum")


def enrich_with_scan_data(items: list[dict], sb, ticker_key: str = "ticker") -> list[dict]:
    """Merge scan_results fields into a list of items (in place, returns items).

    Tickers utan scan_results-rad fallbackar till universe_registry (name,
    market) + qmj_scores (alpha_rank, quality_z, momentum_z, value_z, stratum).
    score_total/entry_signal förblir None när scan saknas (ärligt) — fallbacken
    lägger ALDRIG till påhittade scores.
    """
    tickers = [item[ticker_key] for item in items if item.get(ticker_key)]
    if not tickers:
        return items
    scan_res = (
        sb.table("scan_results")
        .select(ENRICH_COLUMNS)
        .in_("ticker", tickers)
        .execute()
    )
    scan_map = {r["ticker"]: r for r in (scan_res.data or [])}
    enrich_fields = [c.strip() for c in ENRICH_COLUMNS.replace("ticker, ", "").split(", ")]
    for item in items:
        meta = scan_map.get(item[ticker_key], {})
        for field in enrich_fields:
            if field not in item and field in meta:
                item[field] = meta[field]

    missing = [t for t in tickers if t not in scan_map]
    if missing:
        _enrich_registry_fallback(items, sb, missing, ticker_key)
    return items


# V3-beslutsdata (champion-data) — additiv berikning från current_decisions_v3.
# Dessa nycklar är NYA (inga legacy-fält) och flaggas inte bort någonstans.
V3_DECISION_FIELDS = (
    "thesis_band", "setup_state", "risk_state", "data_grade", "decision_id",
    "master_rank_score", "segment_percentile", "tradability_state",
    "is_actionable",
)


def enrich_with_v3_decisions(items: list[dict], sb, ticker_key: str = "ticker") -> list[dict]:
    """Merge current_decisions_v3 fields into items (in place, returns items).

    Additiv V3-berikning: varje item med en ticker-träff i vyn får sina
    V3-fält satta — bara om de inte redan finns. Items utan träff lämnas
    orörda (V1-beteende); aldrig syntetiska värden. Första vyn-raden per
    ticker vinner (samma mönster som _current_rows). Anroparen ansvarar för
    best-effort-hantering (try/except) om vyn saknas/är otillgänglig.
    """
    tickers = [item[ticker_key] for item in items if item.get(ticker_key)]
    if not tickers:
        return items
    res = (
        sb.table("current_decisions_v3")
        .select("*")
        .in_("ticker", tickers)
        .execute()
    )
    v3_map: dict[str, dict] = {}
    for r in (res.data or []):
        t = r.get("ticker")
        if t and t not in v3_map:  # första träffen vinner
            v3_map[t] = r
    for item in items:
        row = v3_map.get(item.get(ticker_key))
        if not row:
            continue
        for field in V3_DECISION_FIELDS:
            if field not in item and row.get(field) is not None:
                item[field] = row[field]
        if "v3_snapshot_id" not in item and row.get("decision_snapshot_id"):
            item["v3_snapshot_id"] = row["decision_snapshot_id"]
    return items


def _enrich_registry_fallback(items: list[dict], sb, missing: list[str],
                              ticker_key: str = "ticker") -> None:
    """Best-effort fallback: universe_registry (name/market) + qmj_scores.

    Aldrig kraschande — om en tabell saknas/är tom hoppar vi bara över den.
    """
    registry: dict[str, dict] = {}
    try:
        reg_res = (
            sb.table("universe_registry")
            .select(REGISTRY_FALLBACK_COLUMNS)
            .in_("ticker", missing)
            .execute()
        )
        registry = {r["ticker"]: r for r in (reg_res.data or [])}
    except Exception as e:
        logger.debug("universe_registry fallback failed: %s", e)

    qmj: dict[str, dict] = {}
    try:
        qmj_res = (
            sb.table("qmj_scores")
            .select(QMJ_FALLBACK_COLUMNS)
            .in_("ticker", missing)
            .order("scan_date", desc=True)
            .execute()
        )
        for r in (qmj_res.data or []):
            t = r.get("ticker")
            if t and t not in qmj:  # senaste scan_date-raden vinner
                qmj[t] = r
    except Exception as e:
        logger.debug("qmj_scores fallback failed: %s", e)

    missing_set = set(missing)
    for item in items:
        t = item.get(ticker_key)
        if not t or t not in missing_set:
            continue
        reg = registry.get(t, {})
        if "name" not in item and reg.get("name"):
            item["name"] = reg["name"]
        if "market" not in item and reg.get("market"):
            item["market"] = reg["market"]
        q = qmj.get(t, {})
        for field in QMJ_FALLBACK_FIELDS:
            if field not in item and q.get(field) is not None:
                item[field] = q[field]
