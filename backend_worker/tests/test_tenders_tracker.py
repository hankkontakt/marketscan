"""
test_tenders_tracker.py -- Enhetstester for offentliga upphandlingar och free float.
"""
import unittest
from backend_worker.alpha_discovery.tenders_tracker import score_public_tenders
from backend_worker.smart_money import compute_free_float_quality, analyze_insider_transactions


class TestTendersAndSmartMoney(unittest.TestCase):
    def test_public_tenders_strong_exposure(self):
        """Verifiera att hog andel offentliga ramavtal (libkompounders som Bouvet) ger vallgravspoang."""
        res = score_public_tenders(
            tender_volume_msek=500.0,
            annual_revenue_msek=1000.0,
            has_multiyear_framework=True,
            is_defense_or_critical_gov=True,
        )
        self.assertGreaterEqual(res["tender_score_z"], 90.0)
        self.assertIn("STRONG_PUBLIC_SECTOR_MOAT", res["flags"])
        self.assertIn("CRITICAL_INFRASTRUCTURE_SUPPLIER", res["flags"])

    def test_tight_free_float_flagged(self):
        """Float < 20% flaggas som illikvid."""
        res = compute_free_float_quality(0.15)
        self.assertTrue(res["is_tight_float"])
        self.assertIn("TIGHT_FREE_FLOAT_ILLIQUID", res["float_flags"])
        self.assertLess(res["float_quality_score"], 50.0)

    def test_opportunistic_insider_cluster_buys(self):
        """VD och CFO som koper over marknaden ger custom Z_score-hojning."""
        txs = [
            {"transaction_type": "KOP", "role": "VD", "amount_usd": 2000000, "is_open_market": True, "days_ago": 15, "insider_name": "VD-1"},
            {"transaction_type": "KOP", "role": "Finanschef", "amount_usd": 1000000, "is_open_market": True, "days_ago": 20, "insider_name": "CFO-1"},
        ]
        res = analyze_insider_transactions(txs, market_cap=500000000)
        self.assertTrue(res["ceo_cfo_bought"])
        self.assertTrue(res["is_buy_cluster"])
        self.assertGreaterEqual(res["smart_money_z"], 80.0)


if __name__ == "__main__":
    unittest.main()
