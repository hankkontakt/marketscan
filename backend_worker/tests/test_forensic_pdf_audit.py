import json
import unittest
from unittest.mock import patch, MagicMock
from backend_worker.forensic_pdf_audit import run_forensic_audit, extract_text_from_pdf_bytes


class TestForensicPdfAudit(unittest.TestCase):
    def test_extract_text_empty(self):
        text = extract_text_from_pdf_bytes(b"invalid pdf bytes")
        self.assertEqual(text, "")

    @patch("backend_worker.forensic_pdf_audit.urllib.request.urlopen")
    @patch("backend_worker.forensic_pdf_audit.get_api_key", return_value="sk-or-fake-key")
    def test_run_forensic_audit_success(self, mock_key, mock_urlopen):
        mock_resp = MagicMock()
        mock_data = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "ticker": "PLEJD.ST",
                        "company_name": "Plejd AB",
                        "traffic_light": "GRÖN",
                        "audit_score": 88,
                        "dilution_emission_risk": "LÅG",
                        "cash_runway_months": 36.0,
                        "capitalized_rd_pct_of_ebit": 12.5,
                        "real_ebit_adjusted_msek": 259.0,
                        "covenant_and_debt_risks": [],
                        "accounting_red_flags": [],
                        "positive_qualities": ["Starkt kassaflöde", "Nettokassa"],
                        "verdict_summary_sv": "Stark finansiell hälsa utan dolda skulder."
                    })
                }
            }],
            "usage": {"total_tokens": 1200}
        }
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        res = run_forensic_audit("Rapporttext för Plejd...", ticker="PLEJD.ST", company_name="Plejd AB")
        self.assertTrue(res["success"])
        self.assertEqual(res["audit"]["traffic_light"], "GRÖN")
        self.assertEqual(res["audit"]["dilution_emission_risk"], "LÅG")
        self.assertEqual(res["audit"]["audit_score"], 88)


if __name__ == "__main__":
    unittest.main()
