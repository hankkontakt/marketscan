"""Tester för Global Smart Money Tracking Engine."""
import unittest
from backend_worker.smart_money import analyze_insider_transactions


class TestSmartMoney(unittest.TestCase):
    def test_ceo_cfo_buy_cluster(self):
        """Både VD och CFO köper inom 30 dagar -> Kluster, C-suite flagga & hög z-score (≥85)."""
        txs = [
            {"transaction_type": "BUY", "role": "CEO", "amount_usd": 1500000, "is_open_market": True, "days_ago": 10, "insider_name": "CEO Person"},
            {"transaction_type": "BUY", "role": "CFO", "amount_usd": 800000, "is_open_market": True, "days_ago": 15, "insider_name": "CFO Person"},
        ]
        res = analyze_insider_transactions(txs)
        self.assertTrue(res["is_buy_cluster"])
        self.assertTrue(res["ceo_cfo_bought"])
        self.assertIn("INSIDER_BUY_CLUSTER", res["flags"])
        self.assertIn("C_SUITE_ACCUMULATION", res["flags"])
        self.assertGreaterEqual(res["smart_money_z"], 85.0)

    def test_sell_cluster_warning(self):
        """3 separata säljare inom 30 dagar -> Säljklusterflagga & sänkt z-score (≤35)."""
        txs = [
            {"transaction_type": "SELL", "role": "Director", "amount_usd": 500000, "is_open_market": True, "days_ago": 5, "insider_name": "Dir A"},
            {"transaction_type": "SELL", "role": "Officer", "amount_usd": 400000, "is_open_market": True, "days_ago": 12, "insider_name": "Off B"},
            {"transaction_type": "SELL", "role": "10% Owner", "amount_usd": 2000000, "is_open_market": True, "days_ago": 20, "insider_name": "Owner C"},
        ]
        res = analyze_insider_transactions(txs)
        self.assertTrue(res["is_sell_cluster"])
        self.assertIn("INSIDER_SELL_CLUSTER", res["flags"])
        self.assertLessEqual(res["smart_money_z"], 35.0)

    def test_ignore_option_exercises(self):
        """Automatiska optionsprogram / icke-öppna marknadstransaktioner filtreras bort."""
        txs = [
            {"transaction_type": "BUY", "role": "CEO", "amount_usd": 1000000, "is_open_market": False, "days_ago": 5, "insider_name": "CEO Person"},
        ]
        res = analyze_insider_transactions(txs)
        self.assertEqual(res["unique_buyers_90d"], 0)
        self.assertFalse(res["ceo_cfo_bought"])
        self.assertEqual(res["smart_money_z"], 50.0)

    def test_empty_transactions(self):
        """Tom lista ger neutralt utfall (50.0)."""
        res = analyze_insider_transactions([])
        self.assertEqual(res["smart_money_z"], 50.0)
        self.assertEqual(res["flags"], [])


if __name__ == "__main__":
    unittest.main()
