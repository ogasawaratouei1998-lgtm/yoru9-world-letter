"""Algeria draft content is complete, unique, and remains unpublished."""
import json
import unittest
from pathlib import Path

from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"DZ"}


class AlgeriaExpansionTests(unittest.TestCase):
    def test_drafts_and_photo_slots(self):
        doc = check_country_content(ROOT)
        batch = json.loads((ROOT / "country-expansion-batch-algeria-20261122.json").read_text(encoding="utf-8"))
        self.assertEqual(set(batch["countries"]), CODES)
        self.assertEqual(batch["status"], "pending_photos_not_public")
        tasks = list(draft_queries(ROOT))
        places, urls = set(), set()
        for code, draft in batch["countries"].items():
            entry = doc["countries"][code]
            self.assertEqual(entry["name"], draft["name"])
            self.assertEqual(draft["status"], "pending")
            self.assertEqual(entry["portrait"]["body"], draft["portrait"]["body"])
            if entry["status"] == "pending":
                self.assertEqual(entry["portrait"], draft["portrait"])
                self.assertEqual(entry["portraitPhotos"], [])
                self.assertEqual(entry["quiz"], [])
                self.assertEqual(entry["travelStops"], {})
            else:
                self.assertEqual(entry["status"], "approved")
                self.assertGreaterEqual(len(entry["quiz"]), 2)
            self.assertTrue(draft["safetySource"]["url"].startswith("https://www.anzen.mofa.go.jp/"))
            self.assertEqual(len(draft["travelDrafts"]), 2)
            self.assertEqual(len([t for t in tasks if t["countryCode"] == code]), 3)
            for stop in draft["travelDrafts"]:
                self.assertNotIn(stop["place"], places)
                places.add(stop["place"])
                self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                self.assertEqual(len(stop["travelStory"]), 2)
                self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
                source = stop["historicalSources"][0]["url"]
                self.assertTrue(source.startswith("https://whc.unesco.org/en/list/"))
                self.assertNotIn(source, urls)
                urls.add(source)
                quiz = stop["quizDraft"]
                self.assertEqual(len(set(quiz["options"])), 3)
                self.assertIn(quiz["answer"], range(3))
                self.assertGreaterEqual(len(quiz["fact"]), 20)
