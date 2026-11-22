"""UNESCO-backed draft expansion must never bypass the verified photo release gate."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"UG", "ZW", "MG"}

class ThreeNewHeritageDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads((ROOT / "country-expansion-batch-ug-zw-mg-20261122.json").read_text(encoding="utf-8"))
        cls.canonical = check_country_content(ROOT)

    def test_portraits_do_not_approve_or_publish_country(self):
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        self.assertEqual(set(self.batch["countries"]), CODES)
        for code, draft in self.batch["countries"].items():
            with self.subTest(code=code):
                row = self.canonical["countries"][code]
                self.assertEqual(row["status"], "pending")
                self.assertEqual(row["portrait"], draft["portrait"])
                self.assertGreaterEqual(len(row["portrait"]["body"]), 145)
                self.assertEqual(row["portraitPhotos"], [])
                self.assertEqual(row["quiz"], [])
                self.assertEqual(row["travelStops"], {})

    def test_independent_sourced_journeys_and_distinct_quiz_answers(self):
        for code, draft in self.batch["countries"].items():
            self.assertEqual(len(draft["travelDrafts"]), 2)
            self.assertEqual(len({s["place"] for s in draft["travelDrafts"]}), 2)
            self.assertEqual(len({s["quizDraft"]["answer"] for s in draft["travelDrafts"]}), 2)
            for stop in draft["travelDrafts"]:
                with self.subTest(code=code, place=stop["place"]):
                    self.assertEqual(len(stop["travelStory"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
                    self.assertTrue(all(s["url"].startswith("https://whc.unesco.org/en/list/") and
                                        s["checkedOn"] == "2026-11-22" for s in stop["historicalSources"]))
                    q = stop["quizDraft"]
                    self.assertEqual(len(q["options"]), 3)
                    self.assertEqual(len(set(q["options"])), 3)
                    self.assertIn(q["answer"], (0, 1, 2))
                    self.assertGreaterEqual(len(q["fact"]), 20)
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")

    def test_manual_photo_queue_has_cover_and_two_destinations_each(self):
        queries = [q for q in draft_queries(ROOT) if q["countryCode"] in CODES]
        self.assertEqual(len(queries), 9)
        for code in CODES:
            self.assertEqual([q["role"] for q in queries if q["countryCode"] == code],
                             ["cover", "quizAndTravel", "quizAndTravel"])

    def test_updated_world_heritage_name_not_obsolete(self):
        madagascar = self.batch["countries"]["MG"]
        self.assertIn("2023年", madagascar["portrait"]["body"])
        self.assertTrue(any("アンドレファナ乾燥林" in s["place"] for s in madagascar["travelDrafts"]))

if __name__ == "__main__":
    unittest.main()
