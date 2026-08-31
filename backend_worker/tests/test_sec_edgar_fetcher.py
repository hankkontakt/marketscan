import unittest
from unittest.mock import patch
from backend_worker.sec_edgar_fetcher import get_sec_financial_summary


class TestSecEdgarFetcher(unittest.TestCase):
    @patch("backend_worker.sec_edgar_fetcher.fetch_sec_company_facts")
    def test_get_sec_financial_summary(self, mock_fetch):
        mock_raw = {
            "entityName": "MICRON TECHNOLOGY INC",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": "2025-08-31", "val": 25111000000, "form": "10-K", "fy": 2025}
                            ]
                        }
                    },
                    "OperatingIncomeLoss": {
                        "units": {
                            "USD": [
                                {"end": "2025-08-31", "val": 3500000000, "form": "10-K", "fy": 2025}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"end": "2025-08-31", "val": 2800000000, "form": "10-K", "fy": 2025}
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {"end": "2025-08-31", "val": 8500000000, "form": "10-K", "fy": 2025}
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {"end": "2025-08-31", "val": 6000000000, "form": "10-K", "fy": 2025}
                            ]
                        }
                    }
                }
            }
        }
        mock_fetch.return_value = mock_raw

        summary = get_sec_financial_summary("MU")
        self.assertTrue(summary["success"])
        self.assertEqual(summary["company_name"], "MICRON TECHNOLOGY INC")
        self.assertEqual(summary["revenue_musd"], 25111.0)
        self.assertEqual(summary["free_cash_flow_musd"], 2500.0) # 8500 - 6000


if __name__ == "__main__":
    unittest.main()
