import unittest
from backend_worker.rebalancer_engine import calculate_portfolio_allocation, generate_rebalance_plan


class TestRebalancerEngine(unittest.TestCase):
    def setUp(self):
        self.stocks = [
            {"ticker": "PLEJD.ST", "name": "Plejd AB", "shares": 20, "price": 1000.0, "sector": "Technology"},
            {"ticker": "BONEX.ST", "name": "Bonesupport", "shares": 50, "price": 200.0, "sector": "Healthcare"},
        ]
        self.funds = [
            {"fund_name": "Länsförsäkringar Global Index", "isin": "SE0005188836", "current_value": 70000.0}
        ]

    def test_calculate_portfolio_allocation(self):
        alloc = calculate_portfolio_allocation(self.stocks, self.funds)
        # Stocks: 20*1000 + 50*200 = 30000. Funds: 70000. Total = 100000.
        self.assertEqual(alloc["total_value_sek"], 100000.0)
        self.assertEqual(alloc["stocks_value_sek"], 30000.0)
        self.assertEqual(alloc["funds_value_sek"], 70000.0)
        self.assertEqual(alloc["stocks_pct"], 30.0)
        self.assertEqual(alloc["funds_pct"], 70.0)
        self.assertEqual(alloc["sector_weights"]["Technology"], 20.0)
        self.assertEqual(alloc["sector_weights"]["Healthcare"], 10.0)

    def test_generate_rebalance_plan_smart_deposit(self):
        # Mål: 60% Fonder (60k), 40% Aktier (40k).
        # Nuvarande: 70k Fonder, 30k Aktier. Insättning: 10 000 kr.
        # Nytt totalvärde = 110k. Mål Fonder: 66k (redan 70k). Mål Aktier: 44k (har 30k).
        # Hela insättningen ska gå till Aktier för att återställa balansen skattefritt!
        plan = generate_rebalance_plan(
            self.stocks,
            self.funds,
            target_funds_pct=60.0,
            target_stocks_pct=40.0,
            monthly_deposit_sek=10000.0,
        )

        self.assertTrue(plan["success"])
        self.assertIsNotNone(plan["smart_deposit_plan"])
        actions = plan["smart_deposit_plan"]["actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "KÖP")
        self.assertEqual(actions[0]["asset_type"], "AKTIE")

    def test_generate_rebalance_plan_one_time_trades(self):
        # Mål: 60% Fonder (60k), 40% Aktier (40k).
        # Nuvarande: 70k Fonder, 30k Aktier.
        # Skall generera SÄLJ FOND 10k för att nå 60k.
        plan = generate_rebalance_plan(
            self.stocks,
            self.funds,
            target_funds_pct=60.0,
            target_stocks_pct=40.0,
        )

        self.assertTrue(plan["success"])
        orders = plan["one_time_rebalance_orders"]
        self.assertTrue(any(o["action"] == "SÄLJ" and o["asset_type"] == "FOND" for o in orders))


if __name__ == "__main__":
    unittest.main()
