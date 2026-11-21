"""Bulgaria release requires three distinctly licensed, visually checked real Commons photographs."""
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
    "bg-sofia-nevsky-cover": (
        "Alexander Nevsky Cathedral Sofia.jpg", "acediscovery",
        "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "bg-rila-monastery-postcard": (
        "Rila Monastery (view).jpg", "Jaimrsilva",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "bg-boyana-church-postcard": (
        "Boyana Church 018.JPG", "DMY",
        "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/216/",
    "https://whc.unesco.org/en/list/42/",
}


class BulgariaPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.bg = cls.doc["countries"]["BG"]

    def test_country_has_complete_approved_reader_content(self):
        approved = {code for code, country in self.doc["countries"].items()
                    if country["status"] == "approved"}
        self.assertIn("BG", approved)
        self.assertGreaterEqual(len(approved), 31)
        self.assertEqual(self.bg["status"], "approved")
        self.assertEqual(len(self.bg["portraitPhotos"]), 1)
        self.assertEqual(len(self.bg["quiz"]), 2)
        self.assertEqual(set(self.bg["travelStops"]), set(PHOTOS))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("BG", broken)
        results = country_coverage(ROOT, [{"country": "ブルガリア"}])
        self.assertEqual(results["BG"]["cover"], "assets/travel/bg-sofia-nevsky-cover.jpg")
        self.assertEqual(results["BG"]["quizRounds"], 2)

    def test_three_distinct_cc_photos_originals_creators_and_offline_cache(self):
        travel_export = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        source_pages = set()
        photo_assets = set()
        for key, (filename, author, license_name, license_url) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.bg["travelStops"][key]
                self.assertEqual(stop, travel_export[key])
                normalized = filename.replace(" ", "_")
                encoded = quote(normalized, safe="-_.")
                md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
                expected_photo = (
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + md5[0] + "/" + md5[:2] + "/" + encoded + "/500px-" + encoded
                )
                self.assertEqual(stop["photo"], expected_photo)
                # Parentheses are supported unchanged in a canonical Commons File URL.
                page = "https://commons.wikimedia.org/wiki/File:" + quote(normalized, safe="-_.()")
                self.assertEqual(stop["photoPage"], page)
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], license_name)
                self.assertEqual(stop["licenseUrl"], license_url)
                self.assertEqual(stop["country"], "ブルガリア")
                self.assertNotIn(stop["photoPage"], source_pages)
                self.assertNotIn(stop["photoAsset"], photo_assets)
                source_pages.add(stop["photoPage"])
                photo_assets.add(stop["photoAsset"])
        cover_asset = self.bg["portraitPhotos"][0]["asset"]
        quizzes = {self.bg["travelStops"][q["photoKey"]]["photoAsset"]
                   for q in self.bg["quiz"]}
        self.assertEqual(len(quizzes), 2)
        self.assertNotIn(cover_asset, quizzes)
        self.assertEqual(
            set(self.bg["portrait"]["photos"]),
            set(PHOTOS) - {"bg-sofia-nevsky-cover"},
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in photo_assets:
            self.assertIn("'" + asset + "'", worker)

    def test_source_backed_mini_trips_are_independent_and_complete(self):
        sources = set()
        for key, stop in self.bg["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop["famousTourist"])
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            for row in stop["historicalSources"]:
                self.assertEqual(row["checkedOn"], "2026-11-21")
                sources.add(row["url"])
        self.assertEqual(sources, SOURCES)
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        self.assertEqual(
            {q["photoKey"] for q in self.bg["quiz"]},
            set(PHOTOS) - {"bg-sofia-nevsky-cover"},
        )


if __name__ == "__main__":
    unittest.main()
