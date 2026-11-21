"""Third eight-country editorial batch must stay out of the reader until photo QA."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
BATCH = "country-expansion-batch-nordic-asia-eight-20261121.json"
COUNTRIES = {"DK", "FI", "HU", "SI", "PH", "MY", "TN", "GE"}


class ThirdEightCountryExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = check_country_content(ROOT)
        cls.draft = json.loads((ROOT / BATCH).read_text(encoding="utf-8"))

    def test_eight_new_country_portraits_are_source_backed_but_not_public(self):
        self.assertEqual(self.draft["status"], "pending_photos_not_public")
        self.assertEqual(set(self.draft["countries"]), COUNTRIES)
        for code, draft in self.draft["countries"].items():
            with self.subTest(code=code):
                entry = self.canonical["countries"][code]
                self.assertEqual(entry["name"], draft["name"])
                self.assertEqual(draft["status"], "pending")
                if code in ("DK", "FI", "HU", "SI", "PH"):
                    # Immutable draft snapshot; the country later gained reviewed CC photos.
                    self.assertEqual(entry["status"], "approved")
                    self.assertEqual(entry["portrait"]["body"], draft["portrait"]["body"])
                    self.assertEqual(len(entry["portraitPhotos"]), 1)
                    self.assertEqual(len(entry["travelStops"]), 3)
                    self.assertEqual(len(entry["quiz"]), 2)
                else:
                    self.assertEqual(entry["status"], "pending")
                    self.assertEqual(entry["portrait"], draft["portrait"])
                    self.assertEqual(entry["portraitPhotos"], [])
                    self.assertEqual(entry["travelStops"], {})
                    self.assertEqual(entry["quiz"], [])
                self.assertGreaterEqual(len(entry["portrait"]["body"]), 145)
                self.assertEqual(entry["portrait"]["sourceUrl"],
                                 "https://whc.unesco.org/en/statesparties/" + code.lower())
                self.assertEqual(len(draft["travelDrafts"]), 2)

    def test_sixteen_destination_specific_essays_and_quizzes(self):
        places, sources, prompts = set(), set(), set()
        for draft in self.draft["countries"].values():
            for stop in draft["travelDrafts"]:
                with self.subTest(place=stop["place"]):
                    self.assertNotIn(stop["place"], places)
                    places.add(stop["place"])
                    self.assertEqual(len(stop["travelStory"]), 2)
                    self.assertNotEqual(*stop["travelStory"])
                    self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", stop)
                    self.assertEqual(len(stop["historicalSources"]), 1)
                    source = stop["historicalSources"][0]
                    self.assertRegex(source["url"], r"^https://whc\.unesco\.org/en/list/\d+/$")
                    self.assertEqual(source["checkedOn"], "2026-11-21")
                    self.assertNotIn(source["url"], sources)
                    sources.add(source["url"])
                    quiz = stop["quizDraft"]
                    self.assertNotIn(quiz["question"], prompts)
                    prompts.add(quiz["question"])
                    self.assertGreaterEqual(len(quiz["question"]), 10)
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0, 1, 2))
        self.assertEqual(len(places), 16)
        self.assertEqual(len(sources), 16)
        self.assertEqual(len(prompts), 16)

    def test_autodiscovery_scans_next_batch_without_manual_python_whitelist(self):
        tasks = list(draft_queries(ROOT))
        # The queue grows automatically as more editorial batches are added.
        # Never freeze its global length to a previous country count.
        country_codes = {row["countryCode"] for row in tasks}
        self.assertGreaterEqual(len(country_codes), 32)
        self.assertEqual(len(tasks), 3 * len(country_codes))
        for code in COUNTRIES:
            matching = [row for row in tasks if row["countryCode"] == code]
            self.assertEqual(len(matching), 3)
            self.assertEqual(sorted(row["role"] for row in matching),
                             ["cover", "quizAndTravel", "quizAndTravel"])
            self.assertTrue(all(len(row["searchQuery"]) >= 8 for row in matching))
        workflow = (ROOT / ".github/workflows/research-country-photos.yml").read_text(encoding="utf-8")
        self.assertIn("country-expansion-batch-*.json", workflow)

if __name__ == "__main__":
    unittest.main()
