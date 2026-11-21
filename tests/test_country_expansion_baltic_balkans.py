"""Eight researched European drafts feed the photo queue, without approving countries."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
CODES = {"EE", "LV", "LT", "SK", "ME", "AL", "CY", "LU"}

class BalticBalkanEditorialTests(unittest.TestCase):
    def test_batch_has_independent_sources_and_complete_photo_research_slots(self):
        doc = check_country_content(ROOT)
        batch = json.loads((ROOT / "country-expansion-batch-baltic-balkans-eight-20261122.json").read_text(encoding="utf-8"))
        self.assertEqual(batch["status"], "pending_photos_not_public")
        self.assertEqual(set(batch["countries"]), CODES)
        places, sources, prompts = set(), set(), set()
        for code, row in batch["countries"].items():
            current = doc["countries"][code]
            self.assertEqual(row["status"], "pending")
            self.assertEqual(current["name"], row["name"])
            self.assertEqual(len(row["travelDrafts"]), 2)
            if current["status"] == "pending":
                self.assertEqual(current["portrait"], row["portrait"])
                self.assertEqual(current["portraitPhotos"], [])
                self.assertEqual(current["quiz"], [])
                self.assertEqual(current["travelStops"], {})
            for stop in row["travelDrafts"]:
                self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                self.assertNotIn("photoAsset", stop)
                self.assertEqual(len(stop["travelStory"]), 2)
                self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
                self.assertNotEqual(*stop["travelStory"])
                src = stop["historicalSources"][0]
                self.assertEqual(src["checkedOn"], "2026-11-22")
                self.assertTrue(src["url"].startswith(("https://whc.unesco.org/en/list/", "https://muuseum.ut.ee/en/", "https://www.luxembourg-city.com/en/")))
                self.assertNotIn(src["url"], sources)
                self.assertNotIn(stop["place"], places)
                sources.add(src["url"])
                places.add(stop["place"])
                q = stop["quizDraft"]
                self.assertEqual(len(set(q["options"])), 3)
                self.assertIn(q["answer"], (0, 1, 2))
                self.assertGreaterEqual(len(q["fact"]), 20)
                self.assertNotIn(q["question"], prompts)
                prompts.add(q["question"])
        self.assertEqual(len(places), 16)
        self.assertEqual(len(sources), 16)
        self.assertEqual(len(prompts), 16)
        tasks = list(draft_queries(ROOT))
        for code in CODES:
            self.assertEqual(len([t for t in tasks if t["countryCode"] == code]), 3)
