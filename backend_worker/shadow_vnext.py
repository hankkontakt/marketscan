"""Shadow vNext decision engine (Ultimate Rebuild v3, Phase 6).

Computes SetupState/RiskState with the documented vNext rules next to the
legacy-bridge values, and writes a comparison report. It NEVER publishes and
is NEVER served: promotion requires research evidence, not a code path.

Rules are explicit and deterministic — deliberately not tuned:
- Setup: trend alignment (Upptrend -> candidate), entry signal, event
  proximity (catalyst within 14 days -> WAIT), insufficient coverage ->
  INSUFFICIENT. Reason codes travel with every state.
- Risk: stale pit -> CRITICAL; low liquidity or D-grade coverage -> ELEVATED;
  else NORMAL.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend_worker.decision_publication import manifest_from_legacy_row

logger = logging.getLogger(__name__)

EVENT_PROXIMITY_DAYS = 14
SETUP_UP = {"Upptrend"}
SETUP_SIDEWAYS = {"Sidled"}


def compute_setup_vnext(row: Mapping[str, Any], as_of: date) -> tuple[str, list[str]]:
    """vNext setup state: READY | WATCH | WAIT | INSUFFICIENT + reason codes."""
    reasons: list[str] = []
    trend = str(row.get("trend_tech") or "")
    entry_signal = str(row.get("entry_signal") or "EJ_AKTUELL")
    coverage = _coverage(row)

    if coverage < 0.5:
        return "INSUFFICIENT", ["coverage_below_0_5"]

    catalyst_next = _value(row, "catalyst_next")
    if catalyst_next:
        try:
            event_date = datetime.fromisoformat(str(catalyst_next)[:10]).date()
            if event_date <= as_of + timedelta(days=EVENT_PROXIMITY_DAYS):
                return "WAIT", [f"event_within_{EVENT_PROXIMITY_DAYS}d"]
        except ValueError:
            reasons.append("unparsable_catalyst_date")

    if entry_signal == "STARK" and trend in SETUP_UP:
        return "READY", reasons + ["strong_signal_and_uptrend"]
    if entry_signal == "OK" and trend in SETUP_UP | SETUP_SIDEWAYS:
        return "WATCH", reasons + ["ok_signal"]
    if trend in SETUP_UP and coverage >= 0.75:
        return "WATCH", reasons + ["uptrend_coverage_ok"]
    if trend in SETUP_SIDEWAYS:
        return "WAIT", reasons + ["sideways_trend"]
    return "INSUFFICIENT", reasons + ["no_qualified_setup"]


def compute_risk_vnext(row: Mapping[str, Any]) -> tuple[str, list[str]]:
    """vNext risk state: NORMAL | ELEVATED | CRITICAL + reason codes."""
    reasons: list[str] = []
    pit_status = str(row.get("pit_status") or "STALE")
    low_liquidity = bool(_value(row, "low_liquidity", False))
    warning_flags = _list(row.get("warning_flags")) + _list(row.get("data_missing"))

    if pit_status != "READY":
        return "CRITICAL", ["stale_pit"]
    if low_liquidity:
        reasons.append("low_liquidity")
    if warning_flags:
        reasons.append(f"warnings:{len(warning_flags)}")
    if _coverage(row) < 0.75:
        reasons.append("coverage_below_0_75")
    return ("ELEVATED" if reasons else "NORMAL"), reasons


def _value(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    value = row.get(key, default)
    return default if value is None else value


def _coverage(row: Mapping[str, Any]) -> float:
    fields = (
        "master_rank", "master_rank_pctl", "quality_z", "value_z", "momentum_z",
        "analyst_z", "tech_z", "insider_z", "catalyst_z", "growth_z",
    )
    return sum(_value(row, field) is not None for field in fields) / len(fields)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value else []


def run_shadow_comparison(
    cursor: Any, scan_date: date, report_path: Path | None = None
) -> dict[str, Any]:
    """Compare bridge vs vNext for every same-day publishable row.

    Returns the comparison report dict and (optionally) writes it as JSON.
    Never touches decision_snapshots/decision_manifests — shadow only.
    """
    from backend_worker.decision_publication import load_publishable_rows

    rows, excluded = load_publishable_rows(cursor, scan_date)
    snapshot_id = "shadow"
    decision_time = datetime.now(timezone.utc)
    comparisons: list[dict[str, Any]] = []
    agreements = {"setup": 0, "risk": 0}
    for row in rows:
        bridge = manifest_from_legacy_row(row, snapshot_id=snapshot_id, decision_time=decision_time)
        setup_state, setup_reasons = compute_setup_vnext(row, scan_date)
        risk_state, risk_reasons = compute_risk_vnext(row)
        comparisons.append({
            "ticker": str(row["ticker"]),
            "bridge": {"setup_state": bridge.setup_state, "risk_state": bridge.risk_state},
            "vnext": {"setup_state": setup_state, "risk_state": risk_state,
                      "setup_reasons": setup_reasons, "risk_reasons": risk_reasons},
            "agreement": bridge.setup_state == setup_state and bridge.risk_state == risk_state,
        })
        agreements["setup"] += bridge.setup_state == setup_state
        agreements["risk"] += bridge.risk_state == risk_state

    report = {
        "scan_date": scan_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n": len(comparisons),
        "excluded": excluded,
        "agreement": {
            "setup": round(agreements["setup"] / len(comparisons), 4) if comparisons else None,
            "risk": round(agreements["risk"] / len(comparisons), 4) if comparisons else None,
        },
        "comparisons": comparisons,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Shadow vNext: %d rows, setup agreement %.0f%%, risk agreement %.0f%%",
        len(comparisons),
        (report["agreement"]["setup"] or 0) * 100,
        (report["agreement"]["risk"] or 0) * 100,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Shadow vNext comparison (never publishes)")
    parser.add_argument("--scan-date", default=None, help="scan date YYYY-MM-DD (default: today)")
    parser.add_argument("--report", default=None, help="report path (default: docs/audit/shadow-vnext-<date>.json)")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    effective_date = date.fromisoformat(args.scan_date) if args.scan_date else date.today()
    report_path = Path(args.report) if args.report else Path("docs/audit") / f"shadow-vnext-{effective_date.isoformat()}.json"
    import psycopg2
    from psycopg2.extras import RealDictCursor
    with psycopg2.connect(database_url) as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            run_shadow_comparison(cursor, effective_date, report_path=report_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()