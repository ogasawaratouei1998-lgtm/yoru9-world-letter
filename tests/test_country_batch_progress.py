"""Bulk editorial approval is automatic only after source, photography and quiz readiness."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content, load_country_content
from country_batch_progress import expansion_progress

ROOT=Path(__file__).resolve().parents[1]
CODES={"AT","TR","EG"}


class CountryBatchProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=check_country_content(ROOT)["countries"]
        cls.batch=json.loads((ROOT/"country-expansion-batch-at-tr-eg-20261121.json").read_text(encoding="utf-8"))

    def test_original_draft_snapshot_and_current_photo_ready_states(self):
        self.assertEqual(set(self.batch["countries"]),CODES)
        self.assertEqual(self.batch["status"],"pending_photos_not_public")
        for code in CODES:
            with self.subTest(country=code):
                canonical=self.catalog[code]
                draft=self.batch["countries"][code]
                self.assertEqual(draft["status"],"pending")
                self.assertEqual(canonical["name"],draft["name"])
                self.assertGreaterEqual(len(canonical["portrait"]["body"]),145)
                self.assertTrue(canonical["portrait"]["sourceUrl"].startswith(
                    "https://whc.unesco.org/en/"))
                self.assertEqual(canonical["status"],"approved")
                self.assertEqual(len(canonical["portraitPhotos"]),1)
                self.assertEqual(len(canonical["quiz"]),2)
                self.assertEqual(len(canonical["travelStops"]),3)

    def test_six_real_unesco_destinations_have_individual_two_paragraph_essays(self):
        seen=set()
        for code in CODES:
            for item in self.batch["countries"][code]["travelDrafts"]:
                with self.subTest(code=code,place=item["place"]):
                    self.assertNotIn(item["place"],seen)
                    seen.add(item["place"])
                    self.assertEqual(len(item["travelStory"]),2)
                    self.assertTrue(all(110<=len(p)<=360 for p in item["travelStory"]))
                    self.assertNotEqual(item["travelStory"][0],item["travelStory"][1])
                    self.assertEqual(len(item["historicalSources"]),1)
                    self.assertRegex(item["historicalSources"][0]["url"],
                                     r"^https://whc\.unesco\.org/en/list/\d+$")
                    self.assertEqual(item["historicalSources"][0]["checkedOn"],"2026-11-21")
                    self.assertEqual(item["photoStatus"],"not_selected_or_licensed")
                    self.assertNotIn("photoAsset",item)
                    q=item["quizDraft"]
                    self.assertEqual(len(q["options"]),3)
                    self.assertEqual(len(set(q["options"])),3)
                    self.assertIn(q["answer"],(0,1,2))
                    self.assertGreaterEqual(len(q["fact"]),22)
                    self.assertTrue(q["photoGoal"])
        self.assertEqual(len(seen),6)

    def test_summary_preserves_austria_draft_and_approved_turkiye_egypt(self):
        report=expansion_progress(ROOT)
        self.assertEqual(report["catalogCount"],196)
        self.assertEqual(report["approvedCount"],27)
        self.assertEqual(report["pendingCount"],169)
        self.assertNotIn("AT",report["pendingPortraitsPrepared"])
        self.assertIn("AT",report["photoReady"])
        self.assertNotIn("AT",report["pendingCountriesBlocked"])
        for code in ("TR","EG"):
            self.assertNotIn(code,report["pendingPortraitsPrepared"])
            self.assertIn(code,report["photoReady"])
            self.assertNotIn(code,report["pendingCountriesBlocked"])
        for code in ("NL","SG","MX","CH","GR","PT"):
            self.assertIn(code,report["photoReady"])


if __name__=="__main__":
    unittest.main()
