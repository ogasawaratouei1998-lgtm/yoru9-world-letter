"""Danish reader release requires independently licensed real Copenhagen and UNESCO photos."""
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
    "dk-copenhagen-skyline-cover": ("Copenhagen skyline, Denmark.jpg", "CivArmy"),
    "dk-kronborg-castle-postcard": ("Kronbore Castle.jpg", "Danicholson"),
    "dk-roskilde-cathedral-postcard": ("2021 Roskilde Cathedral (16).jpg", "Chris06"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/696/",
    "https://whc.unesco.org/en/list/695/",
}
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


class DenmarkPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.dk = cls.doc["countries"]["DK"]

    def test_denmark_is_approved_and_has_complete_photo_quiz_and_trips(self):
        approved = {code for code, c in self.doc["countries"].items()
                    if c["status"] == "approved"}
        self.assertIn("DK", approved)
        self.assertGreaterEqual(len(approved), 32)
        self.assertEqual(self.dk["status"], "approved")
        self.assertEqual(len(self.dk["portraitPhotos"]), 1)
        self.assertEqual(len(self.dk["quiz"]), 2)
        self.assertEqual(set(self.dk["travelStops"]), set(PHOTOS))
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("DK", broken)
        country = country_coverage(ROOT, [{"country": "デンマーク"}])
        self.assertEqual(country["DK"]["cover"], "assets/travel/dk-copenhagen-skyline-cover.jpg")
        self.assertEqual(country["DK"]["quizRounds"], 2)

    def test_distinct_commons_photo_identity_license_creator_and_geo(self):
        registry = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        assets, sources = set(), set()
        for key, (filename, author) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.dk["travelStops"][key]
                self.assertEqual(stop, registry[key])
                native = filename.replace(" ", "_")
                encoded = quote(native, safe="-_.()")
                digest = hashlib.md5(native.encode("utf-8")).hexdigest()
                self.assertEqual(
                    stop["photo"],
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + digest[0] + "/" + digest[:2] + "/" + encoded + "/500px-" + encoded,
                )
                self.assertEqual(
                    stop["photoPage"],
                    "https://commons.wikimedia.org/wiki/File:" + encoded,
                )
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], LICENSE)
                self.assertEqual(stop["licenseUrl"], LICENSE_URL)
                self.assertEqual(stop["country"], "デンマーク")
                self.assertGreater(stop["latitude"], 55)
                self.assertLess(stop["latitude"], 57)
                self.assertGreater(stop["longitude"], 12)
                self.assertLess(stop["longitude"], 13)
                self.assertNotIn(stop["photoPage"], sources)
                self.assertNotIn(stop["photoAsset"], assets)
                sources.add(stop["photoPage"])
                assets.add(stop["photoAsset"])
        cover = self.dk["portraitPhotos"][0]["asset"]
        quiz_assets = {self.dk["travelStops"][quiz["photoKey"]]["photoAsset"]
                       for quiz in self.dk["quiz"]}
        self.assertEqual(len(quiz_assets), 2)
        self.assertNotIn(cover, quiz_assets)
        self.assertEqual(
            set(self.dk["portrait"]["photos"]),
            set(PHOTOS) - {"dk-copenhagen-skyline-cover"},
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in assets:
            self.assertIn("'" + asset + "'", worker)

    def test_two_unesco_stories_match_the_correct_photographs_and_quizzes(self):
        seen = set()
        for key, stop in self.dk["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(s) <= 360 for s in stop["travelStory"]))
            self.assertGreaterEqual(len(stop["photoCaption"]), 20)
            self.assertEqual(len(stop["historicalSources"]), 1)
            source = stop["historicalSources"][0]
            self.assertEqual(source["checkedOn"], "2026-11-21")
            seen.add(source["url"])
        self.assertEqual(seen, SOURCES)
        self.assertEqual(
            {q["photoKey"] for q in self.dk["quiz"]},
            set(PHOTOS) - {"dk-copenhagen-skyline-cover"},
        )


if __name__ == "__main__":
    unittest.main()
