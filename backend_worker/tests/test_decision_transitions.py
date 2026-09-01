from backend_worker.decision_transitions import diff_manifests, diff_snapshots, write_transitions


def manifest(**overrides):
    """A new-snapshot manifest row as returned by the listings join."""
    values = {
        "decision_snapshot_id": "snapshot-new",
        "decision_id": "decision-new",
        "listing_id": "listing-1",
        "ticker": "MSFT",
        "listing_state": "ACTIVE",
        "thesis_band": "BULLISH",
        "setup_state": "READY",
        "risk_state": "NORMAL",
        "data_grade": "A",
        "master_rank_score": 82.0,
    }
    values.update(overrides)
    return values


def old_manifest(**overrides):
    """Same listing in the previous snapshot; identical dimensions by default."""
    values = manifest(
        decision_snapshot_id="snapshot-old",
        decision_id="decision-old",
    )
    values.update(overrides)
    return values


# --- pure diff logic (dicts, no DB) -----------------------------------------


def test_diff_manifests_thesis_change_emits_row():
    transitions = diff_manifests(
        {"listing-1": old_manifest(thesis_band="CONSTRUCTIVE")},
        {"listing-1": manifest()},
    )
    assert [t["transition_type"] for t in transitions] == ["thesis"]
    row = transitions[0]
    assert row["from_state"] == "CONSTRUCTIVE"
    assert row["to_state"] == "BULLISH"
    assert row["reason_code"] == "thesis:CONSTRUCTIVE->BULLISH"
    assert row["snapshot_from"] == "snapshot-old"
    assert row["snapshot_to"] == "snapshot-new"
    assert row["decision_id"] == "decision-new"
    assert row["rank_delta"] is None


def test_diff_manifests_rank_delta_below_threshold_emits_no_row():
    transitions = diff_manifests(
        {"listing-1": old_manifest(master_rank_score=79.0)},
        {"listing-1": manifest(master_rank_score=82.0)},
    )
    assert transitions == []


def test_diff_manifests_rank_delta_at_threshold_emits_row_with_delta():
    transitions = diff_manifests(
        {"listing-1": old_manifest(master_rank_score=75.0)},
        {"listing-1": manifest(master_rank_score=82.0)},
    )
    assert [t["transition_type"] for t in transitions] == ["rank"]
    row = transitions[0]
    assert row["rank_delta"] == 7.0
    assert row["reason_code"] == "rank_delta:+7.0"
    assert row["from_state"] == "75.0"
    assert row["to_state"] == "82.0"


def test_diff_manifests_rank_delta_negative_emits_row():
    transitions = diff_manifests(
        {"listing-1": old_manifest(master_rank_score=82.0)},
        {"listing-1": manifest(master_rank_score=75.0)},
    )
    assert transitions[0]["rank_delta"] == -7.0
    assert transitions[0]["reason_code"] == "rank_delta:-7.0"


def test_diff_manifests_setup_risk_data_grade_changes_emit_rows():
    transitions = diff_manifests(
        {"listing-1": old_manifest(setup_state="WATCH", risk_state="ELEVATED", data_grade="B")},
        {"listing-1": manifest()},
    )
    by_type = {t["transition_type"]: t for t in transitions}
    assert set(by_type) == {"setup", "risk", "data_grade"}
    assert by_type["setup"]["reason_code"] == "setup:WATCH->READY"
    assert by_type["risk"]["reason_code"] == "risk:ELEVATED->NORMAL"
    assert by_type["data_grade"]["reason_code"] == "data_grade:B->A"


def test_diff_manifests_new_listing_emits_rows_with_null_from_state():
    transitions = diff_manifests(
        {},
        {"listing-2": manifest(listing_id="listing-2", ticker="NVDA", thesis_band="CONSTRUCTIVE")},
    )
    assert transitions
    for row in transitions:
        assert row["from_state"] is None
        assert row["snapshot_from"] is None
        assert row["listing_id"] == "listing-2"
        assert row["ticker"] == "NVDA"
    by_type = {t["transition_type"]: t for t in transitions}
    assert by_type["thesis"]["reason_code"] == "thesis:->CONSTRUCTIVE"
    assert by_type["tradability"]["reason_code"] == "tradability:->ACTIVE"
    assert by_type["rank"]["reason_code"] == "rank:->82.0"
    assert by_type["rank"]["rank_delta"] is None


def test_diff_manifests_inactive_listing_unchanged_emits_no_row():
    transitions = diff_manifests(
        {"listing-1": old_manifest(listing_state="MERGED")},
        {"listing-1": manifest(listing_state="MERGED")},
    )
    assert transitions == []


def test_diff_manifests_inactive_listing_in_both_emits_no_rows_even_with_changes():
    # CPRX invariant: a listing non-ACTIVE in both snapshots produces no rows
    # at all, even when its thesis/setup/risk/data_grade changed.
    transitions = diff_manifests(
        {"listing-1": old_manifest(listing_state="MERGED", thesis_band="CONSTRUCTIVE")},
        {"listing-1": manifest(listing_state="MERGED")},
    )
    assert transitions == []


def test_diff_manifests_tradability_change_emits_row():
    transitions = diff_manifests(
        {"listing-1": old_manifest(listing_state="ACTIVE")},
        {"listing-1": manifest(listing_state="HALTED")},
    )
    tradability = [t for t in transitions if t["transition_type"] == "tradability"]
    assert len(tradability) == 1
    assert tradability[0]["reason_code"] == "tradability:ACTIVE->HALTED"


# --- DB-facing functions (minimal fake conn) --------------------------------


class ScriptedCursor:
    """Returns snapshots on the first fetchall, manifests on the second."""

    def __init__(self, snapshots, manifests):
        self._snapshots = snapshots
        self._manifests = manifests
        self._calls = 0
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        self._calls += 1

    def fetchall(self):
        return self._snapshots if self._calls == 1 else self._manifests

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class ScriptedConnection:
    def __init__(self, snapshots, manifests):
        self._snapshots = snapshots
        self._manifests = manifests

    def cursor(self, cursor_factory=None):
        return ScriptedCursor(self._snapshots, self._manifests)


def test_diff_snapshots_zero_snapshots_returns_empty():
    conn = ScriptedConnection([], [])
    assert diff_snapshots(conn) == []


def test_diff_snapshots_one_snapshot_returns_empty():
    conn = ScriptedConnection(
        [{"decision_snapshot_id": "snapshot-new", "status": "PUBLISHED", "published_at": "2026-09-02T00:00:00+00:00"}],
        [],
    )
    assert diff_snapshots(conn) == []


def test_diff_snapshots_two_snapshots_diffs_manifests():
    snapshots = [
        {"decision_snapshot_id": "snapshot-new", "status": "PUBLISHED", "published_at": "2026-09-02T00:00:00+00:00"},
        {"decision_snapshot_id": "snapshot-old", "status": "SUPERSEDED", "published_at": "2026-09-01T00:00:00+00:00"},
    ]
    manifests = [
        manifest(),
        old_manifest(thesis_band="CONSTRUCTIVE"),
    ]
    conn = ScriptedConnection(snapshots, manifests)
    transitions = diff_snapshots(conn)
    assert [t["transition_type"] for t in transitions] == ["thesis"]
    assert transitions[0]["reason_code"] == "thesis:CONSTRUCTIVE->BULLISH"
    assert transitions[0]["snapshot_from"] == "snapshot-old"
    assert transitions[0]["snapshot_to"] == "snapshot-new"


class RecordingCursor:
    def __init__(self):
        self.sql = None
        self.rows = None

    def executemany(self, sql, rows):
        self.sql = sql
        self.rows = list(rows)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class RecordingConnection:
    def __init__(self):
        self.cursor_instance = RecordingCursor()

    def cursor(self, cursor_factory=None):
        return self.cursor_instance


def test_write_transitions_inserts_rows_idempotently():
    conn = RecordingConnection()
    transitions = [{
        "snapshot_from": "snapshot-old", "snapshot_to": "snapshot-new",
        "listing_id": "listing-1", "ticker": "MSFT", "decision_id": "decision-new",
        "transition_type": "thesis", "from_state": "CONSTRUCTIVE", "to_state": "BULLISH",
        "reason_code": "thesis:CONSTRUCTIVE->BULLISH", "rank_delta": None,
    }]
    written = write_transitions(conn, transitions)
    assert written == 1
    assert "ON CONFLICT DO NOTHING" in conn.cursor_instance.sql
    row = conn.cursor_instance.rows[0]
    assert row[0] == "snapshot-old"
    assert row[1] == "snapshot-new"
    assert row[5] == "thesis"
    assert row[9] is None  # rank_delta


def test_write_transitions_empty_returns_zero():
    conn = RecordingConnection()
    assert write_transitions(conn, []) == 0
    assert conn.cursor_instance.sql is None