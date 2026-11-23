"""Eight new UNESCO-grounded country drafts must remain private editorial data until photo rights pass."""
import json
import unittest
from pathlib import Path
from country_content import load_country_content, check_country_content
ROOT=Path(__file__).resolve().parents[1]
CODES={"CD","RU","UA","SD","KP","PS","DO","FJ"}

class EightCountryNovember24DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch=json.loads((ROOT/"country-expansion-batch-eight-20261124.json").read_text(encoding="utf-8"))
        cls.country=load_country_content(ROOT)
    def test_eight_countries_are_real_additions_and_pending(self):
        self.assertEqual(set(self.batch["countries"]),CODES)
        self.assertFalse(self.batch["publicationEligible"])
        self.assertEqual(len(self.country["countries"]),196)
        self.assertGreaterEqual(sum(c["status"]=="approved" for c in self.country["countries"].values()),67)
        for code in CODES:
            with self.subTest(code=code):
                row=self.country["countries"][code]
                self.assertEqual(row,self.batch["countries"][code])
                self.assertEqual(row["status"],"pending")
                self.assertEqual(row["portraitPhotos"],[])
                self.assertEqual(row["travelStops"],{})
                self.assertEqual(row["quiz"],[])
                self.assertGreaterEqual(len(row["portrait"]["body"]),145)
                self.assertEqual(len(row["travelDrafts"]),2)
                self.assertTrue(row["portrait"]["sourceUrl"].startswith("https://whc.unesco.org/en/list/"))
    def test_sixteen_real_two_paragraph_quiz_drafts_remain_unpublished(self):
        count=0
        for code in CODES:
            row=self.country["countries"][code]
            for draft in row["travelDrafts"]:
                count+=1
                with self.subTest(code=code,title=draft["title"]):
                    self.assertTrue(draft["editorialOnly"])
                    self.assertEqual(draft["status"],"pending_photo_rights_and_location_review")
                    self.assertEqual(draft["photoStatus"],"not_selected_or_licensed")
                    self.assertEqual(len(draft["paragraphs"]),2)
                    self.assertTrue(all(110<=len(p)<=360 for p in draft["paragraphs"]))
                    self.assertEqual(len(draft["historicalSources"]),1)
                    self.assertEqual(draft["historicalSources"][0]["url"],draft["sourceUrl"])
                    self.assertEqual(draft["sourceCheckedOn"],"2026-11-24")
                    self.assertEqual(draft["sourceBatch"],"country-expansion-batch-eight-20261124.json")
                    quiz=draft["quizDraft"]
                    self.assertEqual(len(quiz["options"]),3)
                    self.assertEqual(len(set(quiz["options"])),3)
                    self.assertIn(quiz["answer"],(0,1,2))
                    self.assertGreaterEqual(len(quiz["fact"]),20)
                    self.assertGreaterEqual(len(quiz["quip"]),10)
                    self.assertNotIn("photoKey",quiz)
        self.assertEqual(count,16)
    def test_canonical_approved_runtime_remains_unmodified(self):
        check_country_content(ROOT)
if __name__=="__main__":
    unittest.main()
