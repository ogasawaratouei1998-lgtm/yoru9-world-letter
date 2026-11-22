"""Eighth-source cohort: country portraits and sixteen destinations remain photo-gated."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"CN", "UZ", "LA", "CU", "EC", "CR", "AM", "BA"}
BATCH = "country-expansion-batch-next-eight-20261121.json"


class NextEightUnescoCountryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.batch = json.loads((ROOT / BATCH).read_text(encoding="utf-8"))

    def test_country_portraits_start_pending_without_fake_photographs(self):
        self.assertEqual(set(self.batch["countries"]), CODES)
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        for code, draft in self.batch["countries"].items():
            with self.subTest(code=code):
                country = self.doc["countries"][code]
                self.assertEqual(country["name"], draft["name"])
                if code == "AM" and country["status"] == "approved":
                    # The original source-backed draft is immutable; approval
                    # separately appends verified current regional danger levels.
                    self.assertTrue(country["portrait"]["body"].startswith(draft["portrait"]["body"]))
                    self.assertIn("危険レベル4", country["portrait"]["body"])
                    self.assertIn("隣接地域をレベル2", country["portrait"]["body"])
                    self.assertIn("多くの地域をレベル1", country["portrait"]["body"])
                    self.assertIn("渡航を推奨するものではありません", country["portrait"]["body"])
                else:
                    self.assertTrue(country["portrait"]["body"].startswith(draft["portrait"]["body"]))
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                self.assertEqual(country["portrait"]["sourceUrl"],
                                 "https://whc.unesco.org/en/statesparties/" + code.lower())
                # A future approved country must pass photo/readiness gates.
                # The immutable original batch remains pending in that case.
                if country["status"] == "pending":
                    self.assertTrue(country["portrait"]["body"].startswith(draft["portrait"]["body"]))
                    self.assertEqual(
                        {key: value for key, value in country["portrait"].items() if key != "body"},
                        {key: value for key, value in draft["portrait"].items() if key != "body"},
                    )
                    self.assertEqual(country["portraitPhotos"], [])
                    self.assertEqual(country["quiz"], [])
                    self.assertEqual(country["travelStops"], {})
                else:
                    self.assertEqual(country["status"], "approved")
                    self.assertEqual(len(country["portraitPhotos"]), 1)
                    self.assertEqual(len(country["quiz"]), 2)
                    self.assertEqual(len(country["travelStops"]), 3)

    def test_sixteen_place_specific_sourced_trips_and_unique_quizzes(self):
        places, urls = set(), set()
        for code, draft in self.batch["countries"].items():
            self.assertEqual(len(draft["travelDrafts"]), 2)
            self.assertEqual(draft["status"], "pending")
            for stop in draft["travelDrafts"]:
                with self.subTest(code=code, place=stop["place"]):
                    self.assertNotIn(stop["place"], places)
                    places.add(stop["place"])
                    story = stop["travelStory"]
                    self.assertEqual(len(story), 2)
                    self.assertNotEqual(story[0], story[1])
                    self.assertTrue(all(110 <= len(p) <= 360 for p in story))
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", stop)
                    sources = stop["historicalSources"]
                    self.assertEqual(len(sources), 1)
                    self.assertRegex(sources[0]["url"],
                                     r"^https://whc\.unesco\.org/en/list/\d+/$")
                    self.assertEqual(sources[0]["checkedOn"], "2026-11-21")
                    self.assertNotIn(sources[0]["url"], urls)
                    urls.add(sources[0]["url"])
                    quiz = stop["quizDraft"]
                    self.assertGreaterEqual(len(quiz["question"]), 10)
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0, 1, 2))
        self.assertEqual(len(places), 16)
        self.assertEqual(len(urls), 16)

    def test_photograph_research_discovers_new_batch_automatically(self):
        tasks = [task for task in draft_queries(ROOT) if task["countryCode"] in CODES]
        self.assertEqual(len(tasks), 24)
        for code in CODES:
            roles = sorted(task["role"] for task in tasks if task["countryCode"] == code)
            self.assertEqual(roles, ["cover", "quizAndTravel", "quizAndTravel"])


if __name__ == "__main__":
    unittest.main()
