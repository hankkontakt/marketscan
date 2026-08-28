"""Tester för compute_sector_value — sektorrelativ värdepercentil (ren, ingen DB)."""
import unittest

from backend_worker.qmj_scores import compute_sector_value


def _rows(spec):
    """spec: {ticker: (sector, value_metric)} → lista av dict."""
    return [{"ticker": t, "sector": s, "value_metric": v} for t, (s, v) in spec.items()]


class TestComputeSectorValue(unittest.TestCase):
    def test_n_below_min_returns_none(self):
        # 14 bolag i sektorn → None (kräver ≥15)
        rows = _rows({f"T{i}": ("Industrials", float(i)) for i in range(14)})
        out = compute_sector_value(rows)
        self.assertEqual(len(out), 14)
        self.assertTrue(all(v is None for v in out.values()))

    def test_exactly_min_ok(self):
        # exakt 15 → percentiler beräknas (rank_pct: lo + 0.5*eq)
        rows = _rows({f"T{i}": ("Industrials", float(i)) for i in range(15)})
        out = compute_sector_value(rows)
        self.assertTrue(all(v is not None for v in out.values()))
        self.assertAlmostEqual(out["T0"], 100.0 * 0.5 / 15, places=2)    # 3.33
        self.assertAlmostEqual(out["T7"], 50.0, places=2)
        self.assertAlmostEqual(out["T14"], 100.0 * 14.5 / 15, places=2)  # 96.67

    def test_missing_sector_returns_none(self):
        rows = _rows({f"T{i}": (None, float(i)) for i in range(20)})
        out = compute_sector_value(rows)
        self.assertTrue(all(v is None for v in out.values()))

    def test_empty_sector_string_returns_none(self):
        rows = _rows({f"T{i}": ("", float(i)) for i in range(20)})
        out = compute_sector_value(rows)
        self.assertTrue(all(v is None for v in out.values()))

    def test_different_sectors_separate(self):
        rows = _rows({f"A{i}": ("SectorA", float(i)) for i in range(15)})
        rows += _rows({f"B{i}": ("SectorB", float(i)) for i in range(15)})
        out = compute_sector_value(rows)
        # Båda sektorerna rankas var för sig → max i varje = 96.67
        self.assertAlmostEqual(out["A14"], 100.0 * 14.5 / 15, places=2)
        self.assertAlmostEqual(out["B14"], 100.0 * 14.5 / 15, places=2)
        self.assertAlmostEqual(out["A0"], 100.0 * 0.5 / 15, places=2)
        self.assertAlmostEqual(out["B0"], 100.0 * 0.5 / 15, places=2)

    def test_ties_share_percentile(self):
        # Alla lika → delad mittpercentil 50.0
        rows = _rows({f"T{i}": ("Sector", 10.0) for i in range(15)})
        out = compute_sector_value(rows)
        self.assertTrue(all(v == 50.0 for v in out.values()))

    def test_partial_ties(self):
        # 3 st lika (10.0) → samma percentil; övriga rankas normalt
        vals = [10.0, 10.0, 10.0] + [float(x) for x in range(20, 140, 10)]
        rows = _rows({f"T{i}": ("Sector", v) for i, v in enumerate(vals)})
        out = compute_sector_value(rows)
        self.assertEqual(out["T0"], out["T1"])
        self.assertEqual(out["T1"], out["T2"])
        self.assertAlmostEqual(out["T0"], 100.0 * 1.5 / 15, places=2)   # 10.0
        self.assertAlmostEqual(out["T3"], 100.0 * 3.5 / 15, places=2)   # 23.33
        self.assertAlmostEqual(out["T14"], 100.0 * 14.5 / 15, places=2)  # 96.67

    def test_missing_value_metric_returns_none(self):
        rows = _rows({f"T{i}": ("Sector", float(i)) for i in range(15)})
        rows.append({"ticker": "TNone", "sector": "Sector", "value_metric": None})
        out = compute_sector_value(rows)
        self.assertIsNone(out["TNone"])
        # TNone räknas inte i grupp-n → övriga 15 st får percentil
        self.assertIsNotNone(out["T0"])

    def test_invalid_metric_excluded_from_group(self):
        # 14 giltiga + 1 ogiltig (None) → grupp-n = 14 < 15 → alla None
        rows = _rows({f"T{i}": ("Sector", float(i)) for i in range(14)})
        rows.append({"ticker": "TBad", "sector": "Sector", "value_metric": None})
        out = compute_sector_value(rows)
        self.assertTrue(all(v is None for v in out.values()))

    def test_nan_metric_excluded(self):
        rows = _rows({f"T{i}": ("Sector", float(i)) for i in range(14)})
        rows.append({"ticker": "TNaN", "sector": "Sector", "value_metric": float("nan")})
        out = compute_sector_value(rows)
        self.assertIsNone(out["TNaN"])
        self.assertTrue(all(v is None for v in out.values()))

    def test_min_n_custom(self):
        rows = _rows({f"T{i}": ("Sector", float(i)) for i in range(5)})
        out = compute_sector_value(rows, min_n=5)
        self.assertIsNotNone(out["T4"])
        out2 = compute_sector_value(rows, min_n=6)
        self.assertIsNone(out2["T4"])

    def test_empty_input(self):
        self.assertEqual(compute_sector_value([]), {})


if __name__ == "__main__":
    unittest.main()