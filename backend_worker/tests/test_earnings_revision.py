"""Tester för Earnings Revision Velocity Engine."""
import unittest
from backend_worker.earnings_revision import compute_revision_metrics, extract_yfinance_revisions


class TestEarningsRevision(unittest.TestCase):
    def test_strong_upward_revision(self):
        """Kraftig upprevidering av EPS (+19% på 30d, 8 upp vs 1 ner) -> hög z-score (≥80) & flagga."""
        res = compute_revision_metrics(
            eps_current=2.50,
            eps_30d_ago=2.10,
            eps_7d_ago=2.40,
            eps_90d_ago=1.80,
            up_revisions_30d=8,
            down_revisions_30d=1,
        )
        self.assertAlmostEqual(res["eps_trend_30d_pct"], 19.05, places=2)
        self.assertAlmostEqual(res["revision_breadth"], 0.889, places=2)
        self.assertGreaterEqual(res["revision_velocity_z"], 80.0)
        self.assertIn("STRONG_UPWARD_REVISION", res["revision_flags"])
        self.assertIn("UNANIMOUS_ESTIMATE_UPGRADE", res["revision_flags"])

    def test_downgrade_warning(self):
        """Nedrevidering av EPS (-15% på 30d, 1 upp vs 9 ner) -> låg z-score (≤30) & varningsflagga."""
        res = compute_revision_metrics(
            eps_current=1.70,
            eps_30d_ago=2.00,
            eps_7d_ago=1.75,
            up_revisions_30d=1,
            down_revisions_30d=9,
        )
        self.assertEqual(res["eps_trend_30d_pct"], -15.0)
        self.assertLessEqual(res["revision_velocity_z"], 30.0)
        self.assertIn("ESTIMATE_DOWNGRADE_WARNING", res["revision_flags"])
        self.assertIn("UNANIMOUS_ESTIMATE_DOWNGRADE", res["revision_flags"])

    def test_missing_data_neutral(self):
        """Saknad data ger neutral z-score (50.0) utan krasch."""
        res = compute_revision_metrics(
            eps_current=None,
            eps_30d_ago=None,
            eps_7d_ago=None,
        )
        self.assertEqual(res["revision_velocity_z"], 50.0)
        self.assertEqual(res["revision_flags"], [])

    def test_extract_yfinance_dict(self):
        """Extrahering ur yfinance strukturer."""
        mock_info = {
            "epsTrend": {
                "0q": {
                    "current": 1.25,
                    "7daysAgo": 1.20,
                    "30daysAgo": 1.10,
                    "90daysAgo": 1.00,
                }
            },
            "epsRevisions": {
                "0q": {
                    "upLast30days": 5,
                    "downLast30days": 0,
                }
            }
        }
        res = extract_yfinance_revisions(mock_info)
        self.assertAlmostEqual(res["eps_trend_30d_pct"], 13.64, places=2)
        self.assertEqual(res["revision_breadth"], 1.0)
        self.assertGreater(res["revision_velocity_z"], 75.0)


if __name__ == "__main__":
    unittest.main()
