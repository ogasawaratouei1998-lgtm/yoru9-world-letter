"""Three UNESCO-verified new country drafts remain safely outside the public atlas."""

import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"AZ", "TJ", "BZ"}


class NewCountryEditorialDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads(
            (ROOT / "country-expansion-batch-az-tj-bz-20261122.json")
            .read_text(encoding="utf-8")
        )
        cls.canonical = check_country_content(ROOT)

    def test_new_countries_have_sourced_portraits_but_no_photo_approval(self):
        self.assertEqual(set(self.batch["countries"]), CODES)
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        for code, draft in self.batch["countries"].items():
            with self.subTest(code=code):
                row = self.canonical["countries"][code]
                self.assertEqual(row["status"], "pending")
                self.assertEqual({k:v for k,v in row["portrait"].items() if k != "body"}, {k:v for k,v in draft["portrait"].items() if k != "body"})
                self.assertTrue(row["portrait"]["body"].startswith(draft["portrait"]["body"]))
                self.assertGreaterEqual(len(row["portrait"]["body"]), 145)
                self.assertTrue(row["portrait"]["sourceUrl"].startswith(
                    "https://whc.unesco.org/en/statesparties/"
                ))
                self.assertEqual(row["portraitPhotos"], [])
                self.assertEqual(row["travelStops"], {})
                self.assertEqual(row["quiz"], [])
                self.assertEqual(len(draft["travelDrafts"]), 2)

    def test_distinct_documented_journeys_and_quizzes(self):
        seen = set()
        for code, draft in self.batch["countries"].items():
            answers = []
            for stop in draft["travelDrafts"]:
                with self.subTest(country=code,place=stop["place"]):
                    self.assertNotIn(stop["place"], seen)
                    seen.add(stop["place"])
                    self.assertEqual(len(stop["travelStory"]), 2)
                    self.assertTrue(all(
                        110 <= len(paragraph.strip()) <= 360
                        for paragraph in stop["travelStory"]
                    ))
                    self.assertNotEqual(*stop["travelStory"])
                    sources = stop["historicalSources"]
                    self.assertGreaterEqual(len(sources), 1)
                    self.assertTrue(all(
                        source["url"].startswith("https://whc.unesco.org/en/list/")
                        and source["checkedOn"] == "2026-11-22"
                        for source in sources
                    ))
                    quiz = stop["quizDraft"]
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0,1,2))
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
                    answers.append(quiz["answer"])
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertGreaterEqual(len(stop["commonsSearch"]), 8)
            self.assertEqual(len(set(answers)), 2, "Avoid identical answer positions")

    def test_all_nine_photo_queries_enter_manual_review_queue(self):
        queries = [row for row in draft_queries(ROOT) if row["countryCode"] in CODES]
        self.assertEqual(len(queries), 9)
        self.assertEqual({row["countryCode"] for row in queries}, CODES)
        for code in CODES:
            rows = [row for row in queries if row["countryCode"] == code]
            self.assertEqual([row["role"] for row in rows],
                             ["cover", "quizAndTravel", "quizAndTravel"])


if __name__ == "__main__":
    unittest.main()
