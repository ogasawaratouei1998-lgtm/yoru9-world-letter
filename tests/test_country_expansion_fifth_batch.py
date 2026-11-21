"""Fifth country-content expansion batch stays editorial until photographs are verified."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import unittest

from country_content import check_country_content
from country_editorial_queue import country_editorial_queue

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = ("ID", "VN", "ZA", "KE", "MA", "NO", "CL", "PE")


class FifthBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = check_country_content(ROOT)
        cls.batch = json.loads(
            (ROOT / "country-expansion-batch-eight-20261121.json")
            .read_text(encoding="utf-8")
        )

    def test_eight_new_source_backed_country_portraits_remain_private(self):
        self.assertEqual(set(self.batch["countries"]), set(COUNTRIES))
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        approved = [code for code, entry in self.content["countries"].items()
                    if entry["status"] == "approved"]
        self.assertEqual(len(approved), 27)
        for code in COUNTRIES:
            with self.subTest(code=code):
                country = self.content["countries"][code]
                draft = self.batch["countries"][code]
                # The eight-country draft is an immutable editing snapshot.
                # Norway was subsequently promoted with three distinct licensed photographs.
                if code in ("NO","PE"):
                    self.assertEqual(country["status"], "approved")
                    self.assertEqual(draft["status"], "pending")
                    self.assertEqual(country["portrait"]["body"], draft["portrait"]["body"])
                    self.assertEqual(len(country["portraitPhotos"]), 1)
                    self.assertEqual(len(country["quiz"]), 2)
                    self.assertEqual(len(country["travelStops"]), 3)
                    continue
                self.assertEqual(country["status"], "pending")
                self.assertEqual(draft["status"], "pending")
                self.assertEqual(country["portrait"], draft["portrait"])
                self.assertEqual(country["portraitPhotos"], [])
                self.assertEqual(country["quiz"], [])
                self.assertEqual(country["travelStops"], {})
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                self.assertEqual(country["portrait"]["sourceUrl"],
                                 "https://whc.unesco.org/en/statesparties/" + code.lower())

    def test_sixteen_distinct_readable_unesco_trips_and_quizzes(self):
        names = set()
        urls = set()
        for code in COUNTRIES:
            draft = self.batch["countries"][code]
            self.assertEqual(len(draft["travelDrafts"]), 2)
            for trip in draft["travelDrafts"]:
                with self.subTest(code=code, place=trip["place"]):
                    self.assertNotIn(trip["place"], names)
                    names.add(trip["place"])
                    paragraphs = trip["travelStory"]
                    self.assertEqual(len(paragraphs), 2)
                    self.assertTrue(all(110 <= len(text) <= 360 for text in paragraphs))
                    self.assertNotEqual(paragraphs[0], paragraphs[1])
                    self.assertEqual(trip["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("photoAsset", trip)
                    sources = trip["historicalSources"]
                    self.assertEqual(len(sources), 1)
                    source = sources[0]
                    self.assertEqual(source["checkedOn"], "2026-11-21")
                    self.assertEqual(urlsplit(source["url"]).hostname, "whc.unesco.org")
                    self.assertIn("/en/list/", source["url"])
                    self.assertNotIn(source["url"], urls)
                    urls.add(source["url"])
                    quiz = trip["quizDraft"]
                    self.assertGreaterEqual(len(quiz["question"]), 10)
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertTrue(type(quiz["answer"]) is int)
                    self.assertIn(quiz["answer"], range(3))
                    self.assertIn("photoGoal", quiz)
        self.assertEqual(len(names), 16)
        self.assertEqual(len(urls), 16)

    def test_queue_counts_unfinished_photographs_as_blockers(self):
        queue = country_editorial_queue(ROOT)
        self.assertEqual(len(queue["approvedCountries"]), 27)
        self.assertEqual(queue["pendingCountries"], 169)
        entries = {row["code"]: row for row in queue["prioritizedPending"]}
        for code in COUNTRIES:
            with self.subTest(code=code):
                if code in ("NO","PE"):
                    self.assertNotIn(code, entries)
                    continue
                self.assertNotIn("substantive_portrait", entries[code]["missing"])
                self.assertNotIn("portrait_history_culture_source", entries[code]["missing"])
                self.assertIn("attributed_country_portrait_photo", entries[code]["missing"])
                self.assertIn("two_distinct_licensed_photo_quizzes", entries[code]["missing"])
                self.assertIn("two_paragraph_microtravel", entries[code]["missing"])


if __name__ == "__main__":
    unittest.main()
