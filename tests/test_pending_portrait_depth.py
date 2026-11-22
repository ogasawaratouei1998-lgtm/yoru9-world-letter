"""Every prepared pending country portrait needs enough factual context."""
from pathlib import Path
import unittest
from country_content import check_country_content

ROOT = Path(__file__).resolve().parents[1]

class PendingCountryPortraitDepthTests(unittest.TestCase):
    def test_all_pending_portrait_bodies_have_editorial_depth(self):
        countries = check_country_content(ROOT)["countries"]
        prepared = {code: row for code, row in countries.items()
                    if row["status"] == "pending" and row.get("portrait")}
        self.assertGreaterEqual(len(prepared), 31)
        for code, row in prepared.items():
            with self.subTest(code=code):
                self.assertGreaterEqual(len(row["portrait"]["body"]), 145)
                self.assertTrue(row["portrait"].get("sourceUrl", "").startswith("https://"))
        for code in ("BH", "MU"):
            self.assertEqual(countries[code]["status"], "pending")
            self.assertEqual(countries[code]["portraitPhotos"], [])
            self.assertEqual(countries[code]["quiz"], [])
            self.assertEqual(countries[code]["travelStops"], {})

if __name__ == "__main__":
    unittest.main()
