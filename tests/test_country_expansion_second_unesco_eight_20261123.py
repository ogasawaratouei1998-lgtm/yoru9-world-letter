"""Additional UNESCO-sourced pending drafts remain strictly editorial-only.

These structural assertions do not certify location images, copyrights,
travel safety, or final journalistic review.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITES = {
    "CF": {"475", "1380"},
    "IQ": {"277", "1130"},
    "IL": {"1040", "1096"},
    "MM": {"1588", "1444"},
    "RW": {"1697", "1586"},
    "TD": {"1400", "1475"},
    "VE": {"701", "658"},
    "YE": {"192", "1263"},
}


class EightAdditionalUnescoEditorialDraftsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads(
            (ROOT / "country-content.json").read_text(encoding="utf-8")
        )["countries"]

    def test_canonical_196_and_existing_approvals(self):
        self.assertEqual(len(self.entries), 196)
        self.assertGreaterEqual(
            sum(c["status"] == "approved" for c in self.entries.values()), 67
        )
        self.assertTrue(set(SITES).issubset(self.entries))

    def test_all_new_stories_sourced_detailed_and_non_public(self):
        for code, site_ids in SITES.items():
            with self.subTest(code=code):
                entry = self.entries[code]
                self.assertIn(entry["status"], ("pending", "approved"))
                if entry["status"] == "approved":
                    # Independently cleared photographs may permit future release.
                    continue
                self.assertEqual(entry["portraitPhotos"], [])
                self.assertEqual(entry["portrait"]["photos"], [])
                self.assertGreaterEqual(len(entry["portrait"]["body"]), 145)
                self.assertEqual(entry["travelStops"], {})
                self.assertEqual(entry["quiz"], [])
                journeys = entry["travelDrafts"]
                self.assertEqual(len(journeys), 2)
                self.assertEqual(len({j["title"] for j in journeys}), 2)
                self.assertEqual(
                    {j["sourceUrl"].rstrip("/").split("/")[-1] for j in journeys},
                    site_ids,
                )
                for journey in journeys:
                    self.assertEqual(journey["sourceName"], "UNESCO世界遺産センター")
                    self.assertEqual(journey["sourceCheckedOn"], "2026-11-23")
                    self.assertTrue(journey["sourceUrl"].startswith(
                        "https://whc.unesco.org/en/list/"
                    ))
                    self.assertEqual(len(journey["paragraphs"]), 2)
                    self.assertTrue(all(
                        110 <= len(p) <= 360 for p in journey["paragraphs"]
                    ))
                    self.assertTrue(journey["editorialOnly"])
                    self.assertEqual(
                        journey["status"], "pending_photo_rights_and_location_review"
                    )
                    self.assertEqual(
                        journey["photoStatus"], "not_selected_or_licensed"
                    )
                    self.assertNotIn("photoAsset", journey)
                    self.assertNotIn("photoKey", journey)
                    quiz = journey["quizDraft"]
                    self.assertTrue(quiz["question"] and quiz["fact"] and quiz["photoGoal"])
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0, 1, 2))
                    self.assertNotIn("photoKey", quiz)
                    self.assertNotIn("photoAsset", quiz)


if __name__ == "__main__":
    unittest.main()
