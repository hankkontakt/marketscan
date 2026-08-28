"""Tester för fi_short_positions.py — rena enhetstester (ingen DB, inga externa anrop).

Täcker:
- _to_float: tusentalsavgränsare + decimal i sv- och en-format.
- parse_register: header-alias-kolumnmappning (rubrikradsnamn) + positionell fallback.
- LEI→ISIN-cache: DB-roundtrip via fake-conn (load/save/merge).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend_worker import fi_short_positions as fsp


class TestToFloat(unittest.TestCase):
    """Robust float-parse: '1,234.56', '1 234,56', '7,00926', '20000,0'."""

    def test_en_tusentals_och_decimal(self):
        # en-format: komma = tusentals, punkt = decimal.
        self.assertEqual(fsp._to_float("1,234.56"), 1234.56)

    def test_sv_mellanslag_och_komma_decimal(self):
        # sv-format: mellanslag = tusentals, komma = decimal.
        self.assertEqual(fsp._to_float("1 234,56"), 1234.56)

    def test_sv_komma_decimal(self):
        self.assertEqual(fsp._to_float("7,00926"), 7.00926)

    def test_sv_heltal_med_komma(self):
        self.assertEqual(fsp._to_float("20000,0"), 20000.0)

    def test_en_punkt_decimal(self):
        # Verklig FI-tabell (en-GB): '4.71'.
        self.assertEqual(fsp._to_float("4.71"), 4.71)

    def test_procenttecken(self):
        self.assertEqual(fsp._to_float("9,7 %"), 9.7)

    def test_nbsp_tusentalsavgransare(self):
        self.assertEqual(fsp._to_float("1\u00a0234,56"), 1234.56)

    def test_ogiltigt_varde(self):
        self.assertIsNone(fsp._to_float("abc"))
        self.assertIsNone(fsp._to_float(""))


class TestParseRegister(unittest.TestCase):
    """Header-alias-mappning: rad-parse med given rubrikrad (verklig FI-tabell)."""

    @staticmethod
    def _html(header, rows):
        trs = ["<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"]
        for r in rows:
            trs.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
        return "<table>" + "".join(trs) + "</table>"

    def test_verklig_fi_rubrikrad(self):
        # en-GB-rubriker (verifierade live 2026-08-29) → mappning på namn.
        html = self._html(
            ["Issuer name", "Issuer LEI code", "Latest position date", "Sum short %"],
            [
                ["Vitec Software Group AB (publ)", "5493005EB5RV1QHE6H94", "2026-08-26", "4.71"],
                ["Dynavox Group", "5493008X1XZR4R5R0P66", "2026-08-26", "9,7"],
            ],
        )
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["issuer_name"], "Vitec Software Group AB (publ)")
        self.assertEqual(rows[0]["lei"], "5493005EB5RV1QHE6H94")
        self.assertEqual(rows[0]["latest_position_date"], "2026-08-26")
        self.assertEqual(rows[0]["total_short_pct"], 4.71)
        self.assertEqual(rows[1]["total_short_pct"], 9.7)

    def test_th_med_attribut(self):
        # Verklig FI-tabell: <th class="numeric"> — attribut får inte störa.
        html = ("<table><tr><th>Issuer name</th><th>Issuer LEI code</th>"
                "<th>Latest position date</th><th class=\"numeric\">Sum short %</th></tr>"
                "<tr><td>Vitec Software Group AB (publ)</td>"
                "<td>5493005EB5RV1QHE6H94</td><td>2026-08-26</td>"
                "<td class=\"numeric\">4.71</td></tr></table>")
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_short_pct"], 4.71)

    def test_omordnade_kolumner(self):
        # Kolumnordningen ändras → alias-mappningen följer rubriknamnen.
        html = self._html(
            ["Sum short %", "Issuer name", "Issuer LEI code", "Latest position date"],
            [["4.71", "Vitec Software Group AB (publ)", "5493005EB5RV1QHE6H94", "2026-08-26"]],
        )
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["issuer_name"], "Vitec Software Group AB (publ)")
        self.assertEqual(rows[0]["total_short_pct"], 4.71)

    def test_svensk_rubrikrad(self):
        # sv-varianter av samma fyra kolumner.
        html = self._html(
            ["Emittent", "LEI-kod", "Datum", "Summa kort position, %"],
            [["Vitec Software Group AB (publ)", "5493005EB5RV1QHE6H94", "2026-08-26", "4,71"]],
        )
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_short_pct"], 4.71)

    def test_fallback_positionellt_utan_rubrikrad(self):
        # Ingen rubrikrad → positionellt index (befintlig väg).
        html = ("<table><tr><td>Vitec Software Group AB (publ)</td>"
                "<td>5493005EB5RV1QHE6H94</td><td>2026-08-26</td><td>4.71</td></tr></table>")
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lei"], "5493005EB5RV1QHE6H94")

    def test_okand_rubrikrad_faller_tillbaka_positionellt(self):
        # Rubrikrad finns men inga kända alias → positionell fallback (befintlig väg).
        html = self._html(
            ["Foo", "Bar", "Baz", "Qux"],
            [["Vitec Software Group AB (publ)", "5493005EB5RV1QHE6H94", "2026-08-26", "4.71"]],
        )
        rows = fsp.parse_register(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lei"], "5493005EB5RV1QHE6H94")

    def test_ogiltig_lei_skippas(self):
        html = self._html(
            ["Issuer name", "Issuer LEI code", "Latest position date", "Sum short %"],
            [["Ej LEI", "inte-en-lei", "2026-08-26", "4.71"]],
        )
        self.assertEqual(fsp.parse_register(html), [])

    def test_tom_html(self):
        self.assertEqual(fsp.parse_register(""), [])


class _FakeCursor:
    """Cursor med execute/rowcount — lagrar skrivet värde, returnerar på läs."""

    def __init__(self, stored_value=None):
        self.stored_value = stored_value
        self.rowcount = 1
        self.last_query = ""
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_query = sql
        self.last_params = params
        return self

    def fetchone(self):
        if self.stored_value is None:
            return None
        return (self.stored_value,)


class _FakeConn:
    def __init__(self, stored_value=None):
        self._cursor = _FakeCursor(stored_value)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


class TestLeiCacheDbRoundtrip(unittest.TestCase):
    """LEI→ISIN-cache i worker_state: load/save/merge via fake-conn."""

    def test_load_fran_worker_state(self):
        # psycopg2 returnerar JSONB som dict → returneras direkt.
        conn = _FakeConn(stored_value={"5493008X1XZR4R5R0P66": "SE0017769995"})
        self.assertEqual(fsp._load_lei_cache(conn),
                         {"5493008X1XZR4R5R0P66": "SE0017769995"})

    def test_load_tom_worker_state(self):
        # Ingen rad → {}.
        self.assertEqual(fsp._load_lei_cache(_FakeConn(stored_value=None)), {})

    def test_load_fallback_lokalfil_vid_db_fel(self):
        # DB-fel → lokalfilen läses read-only (andra lagret).
        conn = _FakeConn(stored_value=None)
        conn._cursor.execute = mock.Mock(side_effect=RuntimeError("db down"))
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "lei_isin_cache.json"
            cache_path.write_text(json.dumps({"LEI1": "SE0017769995"}), encoding="utf-8")
            with mock.patch.object(fsp, "LEI_ISIN_CACHE_PATH", cache_path):
                self.assertEqual(fsp._load_lei_cache(conn), {"LEI1": "SE0017769995"})

    def test_save_upsert_till_worker_state(self):
        conn = _FakeConn()
        fsp._save_lei_cache(conn, {"LEI1": "SE0017769995"})
        self.assertTrue(conn.committed)
        self.assertEqual(conn._cursor.last_params[0], fsp.LEI_ISIN_CACHE_KEY)
        self.assertEqual(json.loads(conn._cursor.last_params[1]),
                         {"LEI1": "SE0017769995"})

    def test_enrich_merge_med_befintlig_cache(self):
        # Befintlig cache i worker_state + nya LEI:s → merge + spara tillbaka.
        existing = {"5493008X1XZR4R5R0P66": "SE0017769995"}
        conn = _FakeConn(stored_value=existing)
        rows = [
            {"lei": "5493008X1XZR4R5R0P66", "issuer_name": "Dynavox Group",
             "total_short_pct": 9.7, "latest_position_date": "2026-08-26"},
            {"lei": "5493005EB5RV1QHE6H94", "issuer_name": "Vitec Software Group AB (publ)",
             "total_short_pct": 4.71, "latest_position_date": "2026-08-26"},
        ]
        with mock.patch.object(fsp, "fetch_lei_isin", return_value="SE0012345678"), \
             mock.patch.object(fsp, "time", mock.Mock()):
            stats = fsp.enrich_lei_to_isin(rows, conn=conn)
        self.assertEqual(stats["fetched_now"], 1)
        self.assertEqual(stats["enriched"], 2)
        # Mergad cache sparades till DB (worker_state).
        saved = json.loads(conn._cursor.last_params[1])
        self.assertEqual(saved["5493008X1XZR4R5R0P66"], "SE0017769995")
        self.assertEqual(saved["5493005EB5RV1QHE6H94"], "SE0012345678")
        # Raderna anrikades med ISIN.
        self.assertEqual(rows[0]["isin"], "SE0017769995")
        self.assertEqual(rows[1]["isin"], "SE0012345678")

    def test_enrich_utan_conn_lokalfil_read_only(self):
        # conn=None (dry-run-vägen) → lokalfilen läses read-only, ingen skrivning.
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "lei_isin_cache.json"
            cache_path.write_text(json.dumps({"5493008X1XZR4R5R0P66": "SE0017769995"}),
                                  encoding="utf-8")
            rows = [{"lei": "5493008X1XZR4R5R0P66", "issuer_name": "Dynavox Group",
                     "total_short_pct": 9.7, "latest_position_date": "2026-08-26"}]
            with mock.patch.object(fsp, "LEI_ISIN_CACHE_PATH", cache_path):
                stats = fsp.enrich_lei_to_isin(rows)
            self.assertEqual(stats["enriched"], 1)
            self.assertEqual(rows[0]["isin"], "SE0017769995")


if __name__ == "__main__":
    unittest.main()