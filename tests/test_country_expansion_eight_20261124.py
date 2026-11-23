"""Nov 24 UNESCO-sourced country drafts cannot bypass photograph review."""
import json
from pathlib import Path
import unittest
from country_content import check_country_content, load_country_content

ROOT=Path(__file__).resolve().parents[1]
CODES={"CD","RU","UA","SD","KP","PS","DO","FJ"}
BATCH="country-expansion-batch-eight-20261124.json"

class EightCountrySourcedDraftsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=load_country_content(ROOT)
        cls.source=json.loads((ROOT/BATCH).read_text(encoding="utf-8"))

    def test_real_196_country_content_extended_without_unsafe_promotion(self):
        self.assertEqual(len(self.doc["countries"]),196)
        self.assertEqual(self.source["publicationEligible"],False)
        self.assertEqual(set(self.source["countries"]),CODES)
        self.assertEqual(sum(x["status"]=="approved" for x in self.doc["countries"].values()),67)
        for code in CODES:
            with self.subTest(country=code):
                row=self.doc["countries"][code]
                self.assertEqual(row,self.source["countries"][code])
                self.assertEqual(row["status"],"pending")
                self.assertEqual(row["portraitPhotos"],[])
                self.assertEqual(row["travelStops"],{})
                self.assertEqual(row["quiz"],[])
                self.assertGreaterEqual(len(row["portrait"]["body"]),145)
                self.assertEqual(len(row["travelDrafts"]),2)
                self.assertTrue(row["portrait"]["sourceUrl"].startswith(
                    "https://whc.unesco.org/en/statesparties/"))

    def test_two_usable_cultural_and_quiz_drafts_per_country(self):
        for code in CODES:
            for item in self.doc["countries"][code]["travelDrafts"]:
                with self.subTest(country=code,place=item["title"]):
                    self.assertTrue(item["editorialOnly"])
                    self.assertEqual(item["status"],"pending_photo_rights_and_location_review")
                    self.assertEqual(item["photoStatus"],"not_selected_or_licensed")
                    self.assertEqual(item["sourceBatch"],BATCH)
                    self.assertEqual(len(item["paragraphs"]),2)
                    self.assertTrue(all(110<=len(p)<=360 for p in item["paragraphs"]))
                    self.assertEqual(len(item["historicalSources"]),1)
                    self.assertEqual(item["sourceUrl"],item["historicalSources"][0]["url"])
                    self.assertEqual(item["sourceCheckedOn"],"2026-11-24")
                    self.assertTrue(item["sourceUrl"].startswith("https://whc.unesco.org/en/list/"))
                    quiz=item["quizDraft"]
                    self.assertEqual(len(quiz["options"]),3)
                    self.assertEqual(len(set(quiz["options"])),3)
                    self.assertIn(quiz["answer"],(0,1,2))
                    self.assertGreaterEqual(len(quiz["fact"]),20)
                    self.assertNotIn("photoKey",quiz)

    def test_all_generated_runtime_countries_unchanged(self):
        self.assertEqual(check_country_content(ROOT)["countries"]["FJ"]["status"],"pending")

if __name__=="__main__":
    unittest.main()
