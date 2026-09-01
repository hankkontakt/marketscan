from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend_worker.decision_manifests import (
    DecisionManifest,
    DecisionManifestPublisher,
    ManifestInvariantError,
)


def manifest(snapshot_id: str = "snapshot-1", **overrides):
    values = {
        "listing_id": "listing-1",
        "decision_snapshot_id": snapshot_id,
        "decision_time": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "thesis_band": "NEUTRAL",
        "setup_state": "NEUTRAL",
        "risk_state": "NORMAL",
        "data_grade": "B",
        "coverage": 0.9,
    }
    values.update(overrides)
    return DecisionManifest(**values)


def test_actionable_insufficient_manifest_is_rejected():
    with pytest.raises(ManifestInvariantError, match="INSUFFICIENT"):
        manifest(setup_state="INSUFFICIENT", is_actionable=True).validate()


def test_manifest_serializes_decision_time_in_utc():
    row = manifest().database_row()
    assert row["decision_time"] == "2026-09-01T00:00:00+00:00"


def test_manifest_normalizes_database_decimals_for_postgrest_json():
    row = manifest(master_rank_score=Decimal("81.5"), setup_vector={"confidence": Decimal("0.9")}).database_row()
    assert row["master_rank_score"] == 81.5
    assert row["setup_vector"] == {"confidence": 0.9}


class _Result:
    def execute(self):
        return self


class _Client:
    def __init__(self):
        self.operations = []

    def table(self, name):
        self.operations.append(("table", name))
        return self

    def upsert(self, value):
        self.operations.append(("upsert", value))
        return _Result()

    def rpc(self, name, params):
        self.operations.append(("rpc", name, params))
        return _Result()


def test_publish_stages_rows_before_flipping_atomic_pointer():
    client = _Client()
    DecisionManifestPublisher(client).stage_and_publish(
        snapshot_id="snapshot-1", publication_run_id="run-1", data_snapshot_id="data-1",
        master_model_version="master-v3", code_sha="abc123", manifests=[manifest()],
    )
    assert client.operations[-1] == ("rpc", "publish_decision_snapshot", {"p_snapshot_id": "snapshot-1"})


def test_publisher_rejects_duplicate_listings_before_any_database_write():
    client = _Client()
    with pytest.raises(ManifestInvariantError, match="one manifest per listing"):
        DecisionManifestPublisher(client).stage_and_publish(
            snapshot_id="snapshot-1", publication_run_id="run-1", data_snapshot_id="data-1",
            master_model_version="master-v3", code_sha="abc123",
            manifests=[manifest(), manifest()],
        )
    assert client.operations == []
