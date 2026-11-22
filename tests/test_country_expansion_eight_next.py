"""Second eight-country editorial expansion is sourced and never auto-published."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"CZ", "PL", "SE", "BE", "RO", "BG", "CO", "ET"}
BATCH = "country-expansion-batch-europe-world-eight-20261121.json"


class NextEightCountryBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = check_country_content(ROOT)
        cls.batch = json.loads((ROOT / BATCH).read_text(encoding="utf-8"))

    def test_canonical_portraits_are_sourced_pending_and_hidden_from_reader(self):
        self.assertEqual(set(self.batch["countries"]), CODES)
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        for code, draft in self.batch["countries"].items():
            with self.subTest(country=code):
                entry = self.canonical["countries"][code]
                self.assertEqual(entry["name"], draft["name"])
                if code in ("CZ", "BE", "BG", "SE", "PL", "ET"):
                    # Original pending drafts remain immutable snapshots when
                    # editorially approved countries gain licensed photo sets.
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

    def test_distinct_heritage_sources_and_readable_travel_quiz_drafts(self):
        places, urls = set(), set()
        for draft in self.batch["countries"].values():
            for stop in draft["travelDrafts"]:
                with self.subTest(place=stop["place"]):
                    self.assertNotIn(stop["place"], places)
                    places.add(stop["place"])
                    paragraphs = stop["travelStory"]
                    self.assertEqual(len(paragraphs), 2)
                    self.assertNotEqual(paragraphs[0], paragraphs[1])
                    self.assertTrue(all(110 <= len(p) <= 360 for p in paragraphs))
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", stop)
                    self.assertEqual(len(stop["historicalSources"]), 1)
                    source = stop["historicalSources"][0]
                    self.assertRegex(source["url"], r"^https://whc\.unesco\.org/en/list/\d+/$")
                    self.assertEqual(source["checkedOn"], "2026-11-21")
                    self.assertNotIn(source["url"], urls)
                    urls.add(source["url"])
                    q = stop["quizDraft"]
                    self.assertGreaterEqual(len(q["question"]), 10)
                    self.assertGreaterEqual(len(q["fact"]), 20)
                    self.assertEqual(len(q["options"]), 3)
                    self.assertEqual(len(set(q["options"])), 3)
                    self.assertIn(q["answer"], (0, 1, 2))
        self.assertEqual(len(places), 16)
        self.assertEqual(len(urls), 16)

    def test_free_photo_candidate_queue_adds_three_role_specific_queries_per_country(self):
        tasks = list(draft_queries(ROOT))
        matches = [task for task in tasks if task["countryCode"] in CODES]
        self.assertEqual(len(matches), 24)
        self.assertEqual({task["countryCode"] for task in matches}, CODES)
        for code in CODES:
            roles = [task["role"] for task in matches if task["countryCode"] == code]
            self.assertEqual(sorted(roles), ["cover", "quizAndTravel", "quizAndTravel"])
        # Original 16-country research cohort remains supported unchanged.
        self.assertGreaterEqual(len({task["countryCode"] for task in tasks}), 24)
        self.assertGreaterEqual(len(tasks), 72)


if __name__ == "__main__":
    unittest.main()
