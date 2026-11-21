"""Finland release checks three distinct Commons images, cultural sources and mobile assets."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from check_country_experience import country_coverage
from country_content import check_country_content
from country_readiness import ready_country_codes

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = {
    "fi-helsinki-cathedral-cover": ("Helsinki Senate Square and Helsinki Cathedral in May 2026.jpg", "JIP"),
    "fi-suomenlinna-fortress-postcard": ("Fortress of Suomenlinna, 2019 (01).jpg", "Bahnfrend"),
    "fi-old-rauma-postcard": ("Vanha Rauma.jpg", "Anninaem"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/583/",
    "https://whc.unesco.org/en/list/582/",
}
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


class FinlandPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.fi = cls.doc["countries"]["FI"]

    def test_finland_has_complete_approved_portrait_and_photo_quizzes(self):
        approved = {code for code, country in self.doc["countries"].items()
                    if country["status"] == "approved"}
        self.assertIn("FI", approved)
        self.assertGreaterEqual(len(approved), 33)
        self.assertEqual(self.fi["status"], "approved")
        self.assertEqual(len(self.fi["portraitPhotos"]), 1)
        self.assertEqual(len(self.fi["quiz"]), 2)
        self.assertEqual(set(self.fi["travelStops"]), set(PHOTOS))
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("FI", broken)
        info = country_coverage(ROOT, [{"country": "フィンランド"}])
        self.assertEqual(info["FI"]["cover"], "assets/travel/fi-helsinki-cathedral-cover.jpg")
        self.assertEqual(info["FI"]["quizRounds"], 2)

    def test_original_commons_photo_identity_and_licenses_match_exact_assets(self):
        export = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        sources, assets = set(), set()
        for key, (filename, author) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.fi["travelStops"][key]
                self.assertEqual(stop, export[key])
                normalized = filename.replace(" ", "_")
                encoded = quote(normalized, safe="-_.()")
                md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
                expected_url = (
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + md5[0] + "/" + md5[:2] + "/" + encoded
                    + "/500px-" + encoded
                )
                self.assertEqual(stop["photo"], expected_url)
                self.assertEqual(
                    stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + encoded
                )
                self.assertEqual(stop["country"], "フィンランド")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], LICENSE)
                self.assertEqual(stop["licenseUrl"], LICENSE_URL)
                self.assertGreater(stop["latitude"], 59)
                self.assertLess(stop["latitude"], 62)
                self.assertNotIn(stop["photoPage"], sources)
                self.assertNotIn(stop["photoAsset"], assets)
                sources.add(stop["photoPage"])
                assets.add(stop["photoAsset"])
        cover_asset = self.fi["portraitPhotos"][0]["asset"]
        quiz_assets = {
            self.fi["travelStops"][q["photoKey"]]["photoAsset"]
            for q in self.fi["quiz"]
        }
        self.assertEqual(len(quiz_assets), 2)
        self.assertNotIn(cover_asset, quiz_assets)
        self.assertEqual(
            set(self.fi["portrait"]["photos"]),
            set(PHOTOS) - {"fi-helsinki-cathedral-cover"}
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in assets:
            self.assertIn("'" + asset + "'", worker)

    def test_two_unesco_trips_keep_correct_places_and_full_essays(self):
        sources = set()
        for key, stop in self.fi["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop["famousTourist"])
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertEqual(len(stop["historicalSources"]), 1)
            source = stop["historicalSources"][0]
            self.assertEqual(source["checkedOn"], "2026-11-21")
            sources.add(source["url"])
        self.assertEqual(sources, SOURCES)
        self.assertEqual(
            {q["photoKey"] for q in self.fi["quiz"]},
            set(PHOTOS) - {"fi-helsinki-cathedral-cover"}
        )


if __name__ == "__main__":
    unittest.main()
