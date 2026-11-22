"""New countries remain private until photographs and all release assets pass validation."""
import json
from pathlib import Path
import unittest

from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
FILENAME = "country-expansion-batch-central-asia-americas-africa-eight-20261121.json"
CODES = {"MN", "KZ", "BO", "PA", "NA", "SN", "OM", "MT"}


class CentralAsiaWorldExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads((ROOT / FILENAME).read_text(encoding="utf-8"))
        cls.canonical = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))

    def test_eight_original_drafts_remain_immutable_after_separate_approval(self):
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        self.assertEqual(set(self.batch["countries"]), CODES)
        for code, draft in self.batch["countries"].items():
            with self.subTest(country=code):
                country = self.canonical["countries"][code]
                self.assertEqual(draft["status"], "pending")
                self.assertEqual(draft["name"], country["name"])
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                if code == "MT":
                    # Immutable November 21 draft later received three independently
                    # reviewed CC photos and two rich UNESCO-backed travel trips.
                    self.assertEqual(country["status"], "approved")
                    self.assertEqual(country["portrait"]["body"], draft["portrait"]["body"])
                    self.assertEqual(country["portrait"]["lead"], draft["portrait"]["lead"])
                    self.assertEqual(country["portrait"]["facts"], draft["portrait"]["facts"])
                    self.assertEqual(len(country["portrait"]["photos"]), 2)
                    self.assertEqual(len(country["portraitPhotos"]), 1)
                    self.assertEqual(len(country["quiz"]), 2)
                    self.assertEqual(len(country["travelStops"]), 3)
                else:
                    self.assertEqual(country["status"], "pending")
                    self.assertEqual(draft["portrait"], country["portrait"])
                    self.assertEqual(country["portrait"]["photos"], [])
                    self.assertEqual(country["portraitPhotos"], [])
                    self.assertEqual(country["quiz"], [])
                    self.assertEqual(country["travelStops"], {})
                self.assertEqual(country["highlights"], [])
                self.assertEqual(
                    country["portrait"]["sourceUrl"],
                    "https://whc.unesco.org/en/statesparties/" + code.lower(),
                )
                self.assertEqual(len(draft["travelDrafts"]), 2)
                self.assertGreaterEqual(len(draft["coverCommonsSearch"]), 8)
                self.assertEqual(len(draft["requiredBeforeApproval"]), 4)

    def test_sixteen_distinct_sourced_places_and_real_quizzes(self):
        seen_places = set()
        seen_search_terms = set()
        for code, draft in self.batch["countries"].items():
            for stop in draft["travelDrafts"]:
                with self.subTest(country=code, place=stop["place"]):
                    self.assertNotIn(stop["place"], seen_places)
                    seen_places.add(stop["place"])
                    self.assertEqual(len(stop["travelStory"]), 2)
                    for paragraph in stop["travelStory"]:
                        self.assertGreaterEqual(len(paragraph), 110)
                        self.assertLessEqual(len(paragraph), 360)
                    self.assertNotEqual(*stop["travelStory"])
                    self.assertEqual(len(stop["historicalSources"]), 1)
                    source = stop["historicalSources"][0]
                    self.assertRegex(
                        source["url"], r"^https://whc\.unesco\.org/en/list/[0-9]+$"
                    )
                    self.assertEqual(source["checkedOn"], "2026-11-21")
                    quiz = stop["quizDraft"]
                    self.assertGreaterEqual(len(quiz["question"]), 12)
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIs(type(quiz["answer"]), int)
                    self.assertIn(quiz["answer"], range(3))
                    self.assertGreaterEqual(len(quiz["fact"]), 22)
                    self.assertTrue(quiz["photoGoal"])
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", stop)
                    self.assertNotIn(stop["commonsSearch"], seen_search_terms)
                    seen_search_terms.add(stop["commonsSearch"])
        self.assertEqual(len(seen_places), 16)

    def test_photo_research_auto_discovers_all_24_new_tasks(self):
        tasks = list(draft_queries(ROOT))
        chosen = [task for task in tasks if task["countryCode"] in CODES]
        self.assertEqual(len(chosen), 24)
        for code in CODES:
            selected = [task for task in chosen if task["countryCode"] == code]
            self.assertEqual(len(selected), 3)
            self.assertEqual(
                [task["role"] for task in selected],
                ["cover", "quizAndTravel", "quizAndTravel"],
            )
            self.assertEqual(
                len({task["searchQuery"] for task in selected}), 3
            )


if __name__ == "__main__":
    unittest.main()
