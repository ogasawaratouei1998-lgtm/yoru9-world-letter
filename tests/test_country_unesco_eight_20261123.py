"""New 2026-11-23 UNESCO-source editorial portraits may not bypass release safety."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODES = {"CI","CM","GM","KG","MR","MW","SC","SR"}
class EightUNESCOPortraitDraftsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.countries = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))["countries"]

    def test_new_source_backed_portraits_and_two_virtual_travel_stories(self):
        for code in CODES:
            with self.subTest(code=code):
                country = self.countries[code]
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                self.assertTrue(country["portrait"]["sourceUrl"].startswith("https://whc.unesco.org/en/statesparties/"))
                if country["status"] == "approved":
                    continue
                self.assertEqual(country["status"], "pending")
                self.assertEqual(country["portraitPhotos"], [])
                self.assertEqual(country["travelStops"], {})
                self.assertEqual(country["quiz"], [])
                drafts = country["travelDrafts"]
                self.assertEqual(len(drafts), 2)
                self.assertEqual(len(set(d["title"] for d in drafts)), 2)
                for d in drafts:
                    self.assertTrue(d["editorialOnly"])
                    self.assertEqual(d["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", d)
                    self.assertNotIn("photoKey", d)
                    self.assertNotIn("photoPage", d)
                    self.assertEqual(d["status"], "pending_photo_rights_and_location_review")
                    self.assertEqual(len(d["paragraphs"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in d["paragraphs"]))
                    self.assertTrue(d["sourceUrl"].startswith("https://whc.unesco.org/en/list/"))
                    self.assertEqual(d["sourceCheckedOn"], "2026-11-23")
                    quiz = d["quizDraft"]
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0,1,2))
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
                    self.assertNotIn("photoKey", quiz)

if __name__ == "__main__":
    unittest.main()
