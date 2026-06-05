"""Shared enrichment logic — merges scan_results fields into items."""
ENRICH_COLUMNS = "ticker, name, price, change_pct, score_total, entry_signal, trend_signal"


def enrich_with_scan_data(items: list[dict], sb, ticker_key: str = "ticker") -> list[dict]:
    """Merge scan_results fields into a list of items (in place, returns items)."""
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
    return items
