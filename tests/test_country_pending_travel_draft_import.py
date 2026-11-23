"""Keep imported historical country travel/quiz drafts editorial-only.

The batch source is historical editorial work, not fresh factual verification.
Promotion requires independent current photo/license/location review.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODES = set(["AZ","BH","BO","BZ","CL","CN","CO","CR","CU","EC","HN","KE","KZ","LA","LB","LU","ME","MG","MN","MU","MY","NA","OM","PA","PY","RO","RS","SN","TJ","TN","UG","UZ","ZA","ZW"])


class CanonicalPendingTravelDraftImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))

    def test_catalog_and_release_boundary_are_unchanged(self):
        entries = self.doc["countries"]
        self.assertEqual(len(entries), 196)
        self.assertEqual(sum(c["status"] == "approved" for c in entries.values()), 67)
        self.assertTrue(CODES.issubset(entries))

    def test_two_sourced_travel_stories_and_quiz_drafts_per_pending_country(self):
        for code in sorted(CODES):
            with self.subTest(country=code):
                entry = self.doc["countries"][code]
                if entry["status"] == "approved":
                    # Independent photo and source review may approve a country later.
                    continue
                self.assertEqual(entry["status"], "pending")
                self.assertEqual(entry["portraitPhotos"], [])
                self.assertEqual(entry["travelStops"], {})
                self.assertEqual(entry["quiz"], [])
                drafts = entry.get("travelDrafts", [])
                self.assertEqual(len(drafts), 2)
                self.assertEqual(len({d["title"] for d in drafts}), 2)
                for d in drafts:
                    self.assertTrue(d["editorialOnly"])
                    self.assertEqual(d["status"], "pending_photo_rights_and_location_review")
                    self.assertEqual(d["photoStatus"], "not_selected_or_licensed")
                    self.assertEqual(len(d["paragraphs"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in d["paragraphs"]))
                    self.assertTrue(d["sourceUrl"].startswith("https://"))
                    self.assertTrue(d["sourceName"].strip())
                    self.assertTrue(d["sourceCheckedOn"].startswith("2026-11-"))
                    self.assertTrue((ROOT / d["sourceBatch"]).is_file())
                    q = d["quizDraft"]
                    self.assertEqual(len(q["options"]), 3)
                    self.assertEqual(len(set(q["options"])), 3)
                    self.assertIn(q["answer"], (0, 1, 2))
                    self.assertTrue(q["question"] and q["fact"])
                    self.assertNotIn("photoKey", q)
                    self.assertNotIn("photoAsset", d)

    def test_every_story_still_matches_its_historical_source_batch(self):
        entries = self.doc["countries"]
        for code in CODES:
            entry = entries[code]
            if entry["status"] == "approved":
                continue
            for draft in entry["travelDrafts"]:
                batch = json.loads((ROOT / draft["sourceBatch"]).read_text(encoding="utf-8"))
                candidates = batch["countries"][code]["travelDrafts"]
                matching = [s for s in candidates if s["place"] == draft["title"]]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0]["travelStory"], draft["paragraphs"])
                self.assertEqual(matching[0]["historicalSources"], draft["historicalSources"])

if __name__ == "__main__":
    unittest.main()
