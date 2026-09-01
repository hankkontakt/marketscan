"""Diff the two most recent published decision snapshots into transition rows.

Phase 9 delta layer. The API can never diff two snapshots itself: anon RLS
only sees ``status='PUBLISHED'`` snapshots (083) and publishing supersedes
every earlier snapshot, so the worker computes the delta with service
credentials and writes ``public.decision_transitions`` (migration 088,
anon-readable). "Workers compute, API reads."

Snapshot selection: the two most recent snapshots with status in
('PUBLISHED', 'SUPERSEDED') ordered by ``published_at DESC`` — i.e. the
current snapshot plus its immediate predecessor. Fewer than two → no diff.

Tradability semantics: every manifest is joined to the current listings row
(``valid_to IS NULL``) for ``ticker`` and ``state``. A tradability row is
emitted only when the state differs between the old and the new manifest.
Because the publication flow quarantines non-ACTIVE listings, a listing that
turns non-ACTIVE (e.g. CPRX after its acquisition) simply disappears from the
new snapshot and is never iterated — no synthetic row. A listing that is
non-ACTIVE in both snapshots is skipped entirely (CPRX invariant).

Rank: a row is emitted only when |new - old| >= 5 (raw delta); the stored
``rank_delta`` is the delta rounded to one decimal.

Idempotency: ``write_transitions`` uses ``ON CONFLICT DO NOTHING`` without a
conflict target, which is safe whether or not migration 088 adds a UNIQUE
constraint on (snapshot_to, listing_id, transition_type, from_state,
to_state). If the constraint exists, re-runs skip already-written rows.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_RANK_DELTA_MIN = 5.0

# (transition_type, manifest column) for the state dimensions that always
# materialize a row on change, regardless of magnitude.
_STATE_DIMENSIONS = (
    ("thesis", "thesis_band"),
    ("setup", "setup_state"),
    ("risk", "risk_state"),
    ("data_grade", "data_grade"),
)

_SNAPSHOT_SQL = """
    SELECT decision_snapshot_id, status, published_at
    FROM public.decision_snapshots
    WHERE status IN ('PUBLISHED', 'SUPERSEDED')
    ORDER BY published_at DESC NULLS LAST, decision_snapshot_id DESC
    LIMIT 2
"""

_MANIFEST_SQL = """
    SELECT dm.decision_id, dm.decision_snapshot_id, dm.listing_id,
           dm.master_rank_score, dm.thesis_band, dm.setup_state,
           dm.risk_state, dm.data_grade,
           l.ticker, l.state AS listing_state
    FROM public.decision_manifests dm
    LEFT JOIN public.listings l
      ON l.listing_id = dm.listing_id AND l.valid_to IS NULL
    WHERE dm.decision_snapshot_id = ANY(%s::uuid[])
"""

_INSERT_SQL = """
    INSERT INTO public.decision_transitions
        (snapshot_from, snapshot_to, listing_id, ticker, decision_id,
         transition_type, from_state, to_state, reason_code, rank_delta)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT DO NOTHING
"""


def _state_reason(transition_type: str, from_state: Any, to_state: Any) -> str:
    """Reason code for a state transition, e.g. ``thesis:BULLISH->CONSTRUCTIVE``."""
    return f"{transition_type}:{from_state or ''}->{to_state}"


def _transition(
    base: Mapping[str, Any],
    transition_type: str,
    from_state: Any,
    to_state: Any,
    reason_code: str,
    rank_delta: float | None = None,
) -> dict[str, Any]:
    return {
        **base,
        "transition_type": transition_type,
        "from_state": from_state,
        "to_state": to_state,
        "reason_code": reason_code,
        "rank_delta": rank_delta,
    }


def _changed_transitions(
    base: Mapping[str, Any], old: Mapping[str, Any], new: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Rows for a listing present in both snapshots (old -> new)."""
    rows: list[dict[str, Any]] = []
    for transition_type, key in _STATE_DIMENSIONS:
        from_state = old.get(key)
        to_state = new.get(key)
        if from_state != to_state:
            rows.append(
                _transition(base, transition_type, from_state, to_state, _state_reason(transition_type, from_state, to_state))
            )
    from_state = old.get("listing_state")
    to_state = new.get("listing_state")
    if from_state != to_state:
        rows.append(_transition(base, "tradability", from_state, to_state, _state_reason("tradability", from_state, to_state)))
    old_score = old.get("master_rank_score")
    new_score = new.get("master_rank_score")
    if old_score is not None and new_score is not None:
        raw_delta = float(new_score) - float(old_score)
        if abs(raw_delta) >= _RANK_DELTA_MIN:
            delta = round(raw_delta, 1)
            rows.append(
                _transition(base, "rank", str(old_score), str(new_score), f"rank_delta:{delta:+.1f}", rank_delta=delta)
            )
    return rows


def _new_listing_transitions(
    base: Mapping[str, Any], new: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Rows for a listing present only in the new snapshot (from_state=NULL)."""
    rows: list[dict[str, Any]] = []
    for transition_type, key in _STATE_DIMENSIONS:
        to_state = new.get(key)
        if to_state is not None:
            rows.append(_transition(base, transition_type, None, to_state, _state_reason(transition_type, None, to_state)))
    to_state = new.get("listing_state")
    if to_state is not None:
        rows.append(_transition(base, "tradability", None, to_state, _state_reason("tradability", None, to_state)))
    score = new.get("master_rank_score")
    if score is not None:
        rows.append(_transition(base, "rank", None, str(score), f"rank:->{score}"))
    return rows


def diff_manifests(
    old_by_listing: Mapping[str, Mapping[str, Any]],
    new_by_listing: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Pure diff between two snapshots' manifests keyed by listing_id.

    Each manifest dict needs: decision_snapshot_id, decision_id, listing_id,
    ticker, listing_state, thesis_band, setup_state, risk_state, data_grade,
    master_rank_score. Returns transition row dicts (see module docstring).
    """
    transitions: list[dict[str, Any]] = []
    for listing_id, new in new_by_listing.items():
        old = old_by_listing.get(listing_id)
        if (
            old is not None
            and old.get("listing_state") != "ACTIVE"
            and new.get("listing_state") != "ACTIVE"
        ):
            # CPRX invariant: a listing non-ACTIVE in both snapshots produces
            # no transition rows at all.
            continue
        base = {
            "snapshot_from": old["decision_snapshot_id"] if old else None,
            "snapshot_to": new["decision_snapshot_id"],
            "listing_id": listing_id,
            "ticker": new.get("ticker") or "?",
            "decision_id": new.get("decision_id"),
        }
        if old is None:
            transitions.extend(_new_listing_transitions(base, new))
        else:
            transitions.extend(_changed_transitions(base, old, new))
    return transitions


def diff_snapshots(conn: Any) -> list[dict[str, Any]]:
    """Load the two most recent published snapshots and diff their manifests.

    Returns transition row dicts; ``[]`` when fewer than two snapshots exist
    or when nothing changed.
    """
    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(_SNAPSHOT_SQL)
        snapshots = list(cursor.fetchall())
        if len(snapshots) < 2:
            logger.info("Fewer than two published snapshots — no diff")
            return []
        snapshot_ids = [row["decision_snapshot_id"] for row in snapshots]
        cursor.execute(_MANIFEST_SQL, (snapshot_ids,))
        manifests = list(cursor.fetchall())

    new_id, old_id = snapshot_ids[0], snapshot_ids[1]
    old_by_listing = {
        row["listing_id"]: row for row in manifests if row["decision_snapshot_id"] == old_id
    }
    new_by_listing = {
        row["listing_id"]: row for row in manifests if row["decision_snapshot_id"] == new_id
    }
    transitions = diff_manifests(old_by_listing, new_by_listing)
    logger.info("Diffed %d transitions between snapshots %s -> %s", len(transitions), old_id, new_id)
    return transitions


def write_transitions(conn: Any, transitions: list[dict[str, Any]]) -> int:
    """Insert transition rows idempotently. Returns the number of rows written."""
    if not transitions:
        return 0
    rows = [
        (
            t["snapshot_from"], t["snapshot_to"], t["listing_id"], t["ticker"],
            t["decision_id"], t["transition_type"], t["from_state"], t["to_state"],
            t["reason_code"], t["rank_delta"],
        )
        for t in transitions
    ]
    with conn.cursor() as cursor:
        cursor.executemany(_INSERT_SQL, rows)
    return len(rows)


def main() -> None:
    """Worker entry point: diff the two latest snapshots and persist the rows."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    import psycopg2

    with psycopg2.connect(database_url) as conn:
        transitions = diff_snapshots(conn)
        written = write_transitions(conn, transitions)
        logger.info("Wrote %d decision transition rows", written)


if __name__ == "__main__":
    main()