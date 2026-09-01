"""Immutable decision-manifest publication for the worker boundary.

The API deliberately never imports this module. A worker stages all rows for
one snapshot, validates local invariants, and asks Postgres to atomically move
the published pointer only after every row was persisted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID, uuid4


class ManifestInvariantError(ValueError):
    """Raised before a malformed or unsafe snapshot reaches the database."""


def _json_safe(value: Any) -> Any:
    """Normalize DB-native scalar values before the PostgREST JSON boundary."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@dataclass(frozen=True)
class DecisionManifest:
    listing_id: str
    decision_time: datetime
    thesis_band: str
    setup_state: str
    risk_state: str
    data_grade: str
    coverage: float
    decision_snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    master_rank_score: float | None = None
    segment_percentile: float | None = None
    setup_vector: dict[str, Any] = field(default_factory=dict)
    risk_vector: dict[str, Any] = field(default_factory=dict)
    is_actionable: bool = False
    stale_critical_count: int = 0
    street_context: dict[str, Any] = field(default_factory=dict)
    positive_drivers: list[dict[str, Any]] = field(default_factory=list)
    negative_drivers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    factor_snapshot_ids: list[str] = field(default_factory=list)
    model_versions: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.listing_id:
            raise ManifestInvariantError("listing_id is required")
        if self.decision_time.tzinfo is None:
            raise ManifestInvariantError("decision_time must be timezone-aware")
        if not 0 <= self.coverage <= 1:
            raise ManifestInvariantError("coverage must be in [0, 1]")
        if self.stale_critical_count < 0:
            raise ManifestInvariantError("stale_critical_count cannot be negative")
        if self.is_actionable and self.setup_state == "INSUFFICIENT":
            raise ManifestInvariantError("INSUFFICIENT decisions cannot be actionable")
        if self.master_rank_score is not None and not 0 <= self.master_rank_score <= 100:
            raise ManifestInvariantError("master_rank_score must be in [0, 100]")

    def database_row(self) -> dict[str, Any]:
        self.validate()
        row = asdict(self)
        row["decision_time"] = self.decision_time.astimezone(timezone.utc).isoformat()
        return _json_safe(row)


class DecisionManifestPublisher:
    """Small adapter over a Supabase/PostgREST client, deliberately worker-only."""

    def __init__(self, client: Any):
        self._client = client

    def stage_and_publish(
        self,
        *,
        snapshot_id: str,
        publication_run_id: str,
        data_snapshot_id: str,
        master_model_version: str,
        code_sha: str,
        manifests: Iterable[DecisionManifest],
        quality_report: dict[str, Any] | None = None,
        external_dependency_shas: dict[str, str] | None = None,
    ) -> str:
        rows = list(manifests)
        if not rows:
            raise ManifestInvariantError("cannot publish an empty decision snapshot")
        if any(row.decision_snapshot_id != snapshot_id for row in rows):
            raise ManifestInvariantError("every manifest must belong to snapshot_id")
        if len({row.listing_id for row in rows}) != len(rows):
            raise ManifestInvariantError("a snapshot may contain one manifest per listing")

        snapshot = {
            "decision_snapshot_id": snapshot_id,
            "publication_run_id": publication_run_id,
            "data_snapshot_id": data_snapshot_id,
            "master_model_version": master_model_version,
            "code_sha": code_sha,
            "quality_report": quality_report or {},
            "external_dependency_shas": external_dependency_shas or {},
            "status": "STAGED",
        }
        self._client.table("decision_snapshots").upsert(snapshot).execute()
        self._client.table("decision_manifests").upsert(
            [manifest.database_row() for manifest in rows]
        ).execute()
        self._client.rpc("publish_decision_snapshot", {"p_snapshot_id": snapshot_id}).execute()
        return snapshot_id
