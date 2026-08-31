import unittest
from unittest.mock import patch, MagicMock
from backend_worker.macro_fetcher import fetch_swea_series, get_live_macro_snapshot


class TestMacroFetcher(unittest.TestCase):
    @patch("backend_worker.macro_fetcher.urllib.request.urlopen")
    def test_fetch_swea_series_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'[{"date": "2026-08-28", "value": 1.75}]'
        mock_urlopen.return_value = mock_resp

        data = fetch_swea_series("SECBREPOEFF")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["value"], 1.75)

    @patch("backend_worker.macro_fetcher.fetch_swea_series")
    def test_get_live_macro_snapshot_slope(self, mock_fetch):
        def side_effect(series_id, from_date=None, timeout=10):
            if series_id == "SEGVB10YC":
                return [{"date": "2026-08-28", "value": 3.0}]
            if series_id == "SEGVB2YC":
                return [{"date": "2026-08-28", "value": 2.5}]
            if series_id == "SECBREPOEFF":
                return [{"date": "2026-08-28", "value": 1.75}]
            return []

        mock_fetch.side_effect = side_effect
        snapshot = get_live_macro_snapshot()

        self.assertEqual(snapshot["gov_bond_10y"], 3.0)
        self.assertEqual(snapshot["gov_bond_2y"], 2.5)
        self.assertEqual(snapshot["yield_curve_slope_10_2"], 0.5)
        self.assertEqual(snapshot["yield_curve_state"], "NORMAL")
        self.assertEqual(snapshot["risk_free_rate"], 0.03)


if __name__ == "__main__":
    unittest.main()
