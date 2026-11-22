"""Three UNESCO-grounded heritage countries must stay unpublished until photo review."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"LB", "RS", "PY"}

class NewHeritageDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads(
            (ROOT / "country-expansion-batch-lb-rs-py-20261122.json").read_text(encoding="utf-8")
        )
        cls.canonical = check_country_content(ROOT)

    def test_pending_and_no_photos_or_reader_release(self):
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

    def test_twelve_original_paragraphs_and_six_source_backed_quizzes(self):
        for code, draft in self.batch["countries"].items():
            self.assertEqual(len(draft["travelDrafts"]), 2)
            self.assertEqual(len({s["place"] for s in draft["travelDrafts"]}), 2)
            self.assertEqual(len({s["quizDraft"]["answer"] for s in draft["travelDrafts"]}), 2)
            for stop in draft["travelDrafts"]:
                with self.subTest(code=code, place=stop["place"]):
                    self.assertEqual(len(stop["travelStory"]), 2)
                    self.assertTrue(all(110 <= len(t) <= 360 for t in stop["travelStory"]))
                    self.assertTrue(all(s["url"].startswith("https://whc.unesco.org/en/list/")
                                        and s["checkedOn"] == "2026-11-22"
                                        for s in stop["historicalSources"]))
                    q = stop["quizDraft"]
                    self.assertEqual(len(q["options"]), 3)
                    self.assertEqual(len(set(q["options"])), 3)
                    self.assertIn(q["answer"], (0, 1, 2))
                    self.assertGreaterEqual(len(q["fact"]), 20)
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")

    def test_all_nine_distinct_cover_and_destination_queries_in_manual_review(self):
        queue = [q for q in draft_queries(ROOT) if q["countryCode"] in CODES]
        self.assertEqual(len(queue), 9)
        self.assertEqual(len({(q["countryCode"], q["role"], q["place"]) for q in queue}), 9)
        for code in CODES:
            self.assertEqual([q["role"] for q in queue if q["countryCode"] == code],
                             ["cover", "quizAndTravel", "quizAndTravel"])

    def test_previously_unsuitable_image_types_are_explicitly_blocked(self):
        lebanon = self.batch["countries"]["LB"]
        serbia = self.batch["countries"]["RS"]
        self.assertIn("柱頭", lebanon["travelDrafts"][0]["quizDraft"]["photoGoal"])
        self.assertIn("960×194", lebanon["travelDrafts"][1]["quizDraft"]["photoGoal"])
        self.assertIn("絵画", serbia["portrait"]["body"])
        paraguay = self.batch["countries"]["PY"]
        self.assertIn("二つ", paraguay["portrait"]["body"])
        self.assertIn("使い回さない", paraguay["travelDrafts"][1]["quizDraft"]["photoGoal"])

if __name__ == "__main__":
    unittest.main()
