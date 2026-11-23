"""Eight UNESCO-referenced editorial country drafts must not leak into release assets.

This regression verifies structure and the publication boundary, not photographic
rights, on-site safety, or present-day travel advisories.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITES = {
    "AF": ("208", "211"), "BY": ("625", "1196"),
    "GA": ("1147", "1653"), "IR": ("114", "1106"),
    "ML": ("119", "116"), "SA": ("1293", "1329"),
    "TM": ("886", "1199"), "UY": ("747", "1464"),
}


class EightNewPendingUnescoDrafts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))["countries"]

    def test_catalog_stays_complete(self):
        self.assertEqual(len(self.doc), 196)
        self.assertGreaterEqual(sum(x["status"] == "approved" for x in self.doc.values()), 67)

    def test_sourced_essays_and_private_drafts(self):
        for code, ids in SITES.items():
            with self.subTest(code=code):
                country = self.doc[code]
                self.assertIsInstance(country["portrait"], dict)
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                self.assertEqual(country["portrait"]["photos"], [] if country["status"] == "pending" else country["portrait"]["photos"])
                if country["status"] == "approved":
                    # Future independently licensed releases must remain possible.
                    continue
                self.assertEqual(country["status"], "pending")
                self.assertEqual(country["portraitPhotos"], [])
                self.assertEqual(country["quiz"], [])
                self.assertEqual(country["travelStops"], {})
                journeys = country.get("travelDrafts", [])
                self.assertEqual(len(journeys), 2)
                self.assertEqual(len({j["title"] for j in journeys}), 2)
                self.assertEqual(
                    {j["sourceUrl"].rstrip("/").split("/")[-1] for j in journeys},
                    set(ids),
                )
                for journey in journeys:
                    self.assertEqual(len(journey["paragraphs"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in journey["paragraphs"]))
                    self.assertTrue(journey["editorialOnly"])
                    self.assertEqual(journey["photoStatus"], "not_selected_or_licensed")
                    self.assertEqual(journey["status"], "pending_photo_rights_and_location_review")
                    self.assertEqual(journey["sourceName"], "UNESCO世界遺産センター")
                    self.assertEqual(journey["sourceCheckedOn"], "2026-11-23")
                    self.assertNotIn("photoAsset", journey)
                    self.assertNotIn("photoKey", journey["quizDraft"])
                    quiz = journey["quizDraft"]
                    self.assertTrue(quiz["question"] and quiz["fact"] and quiz["photoGoal"])
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], range(3))


if __name__ == "__main__":
    unittest.main()
