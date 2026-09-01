"""Unit tests for screener master_rank enrichment and fallback logic."""
import unittest
from types import SimpleNamespace
from apps.api.routers.screener import _enrich_with_master_rank


class FakeQuery:
    def __init__(self, data_or_exc):
        self._data_or_exc = data_or_exc

    def select(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *a, **k):
        return self

    def execute(self):
        if isinstance(self._data_or_exc, Exception):
            raise self._data_or_exc
        return SimpleNamespace(data=self._data_or_exc)


class FakeSupabase:
    def __init__(self, query_handler):
        self._query_handler = query_handler

    def table(self, name):
        return self._query_handler(name)


class TestScreenerEnrichment(unittest.TestCase):
    def test_enrichment_success_with_pctl(self):
        mr_rows = [{
            "ticker": "AOF.DE", "master_rank": 52.0, "master_rank_pctl": 85.0,
            "tier": "T3", "quality_z": 89.0, "value_z": 22.0, "momentum_z": 60.0,
            "analyst_z": 43.5, "analyst_upside": 19.3, "analyst_count": 8,
            "trend_tech": "Upptrend", "currency": "EUR", "pit_status": "READY"
        }]
        sb = FakeSupabase(lambda t: FakeQuery(mr_rows))
        scan_rows = [{"ticker": "AOF.DE", "segment": "small_cap", "score_total": 68.0}]

        res = _enrich_with_master_rank(sb, scan_rows)
        self.assertEqual(res[0]["master_rank"], 52.0)
        self.assertEqual(res[0]["master_rank_pctl"], 85.0)
        self.assertEqual(res[0]["tier"], "T2")  # 52.0 >= 50.0 is T2 for small_cap
        self.assertEqual(res[0]["entry_signal"], "OK")

    def test_enrichment_retry_when_pctl_column_missing(self):
        """If master_rank_pctl column fails, retry without it and succeed."""
        attempts = []

        def handler(table_name):
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                # First attempt fails with ColumnNotFound
                return FakeQuery(Exception("Column master_rank_pctl does not exist"))
            # Second attempt succeeds without pctl
            return FakeQuery([{
                "ticker": "AOF.DE", "master_rank": 51.96, "tier": "T3",
                "quality_z": 89.0, "value_z": 22.0, "momentum_z": 60.0,
                "analyst_z": 43.5, "analyst_upside": 19.3, "analyst_count": 8,
                "trend_tech": "Upptrend", "currency": "EUR", "pit_status": "READY"
            }])

        sb = FakeSupabase(handler)
        scan_rows = [{"ticker": "AOF.DE", "segment": "small_cap", "score_total": 68.0}]

        res = _enrich_with_master_rank(sb, scan_rows)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(res[0]["master_rank"], 51.96)
        self.assertIsNone(res[0]["master_rank_pctl"])
        self.assertEqual(res[0]["tier"], "T2")  # 51.96 >= 50.0 is T2 for small_cap
        self.assertEqual(res[0]["entry_signal"], "OK")

    def test_fallback_when_db_fails_completely(self):
        """If DB fails completely, fallback to score_total always runs."""
        sb = FakeSupabase(lambda t: FakeQuery(Exception("DB connection down")))
        scan_rows = [
            {"ticker": "HARVIA.HE", "segment": "small_cap", "score_total": 56.0, "score_quality": 80.0},
            {"ticker": "UNKNOWN.ST", "segment": "large_cap", "score_total": 45.0}
        ]

        res = _enrich_with_master_rank(sb, scan_rows)
        self.assertEqual(res[0]["master_rank"], 56.0)
        self.assertEqual(res[0]["tier"], "T2")  # 56.0 >= 50.0 is T2 for small_cap
        self.assertEqual(res[0]["entry_signal"], "OK")
        self.assertIsNone(res[0]["master_rank_pctl"])

        self.assertEqual(res[1]["master_rank"], 45.0)
        self.assertEqual(res[1]["tier"], "T4")  # 45.0 < 50.0 is T4 for large_cap
        self.assertEqual(res[1]["entry_signal"], "EJ_AKTUELL")


if __name__ == "__main__":
    unittest.main()
