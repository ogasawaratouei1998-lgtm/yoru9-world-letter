"""Sweden's 34th country promotion requires independent real Wikimedia photographs."""
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
    "se-stockholm-gamla-stan-cover": (
        "Stockholm-Gamla-Stan-panorama.jpg", "Acediscovery",
        "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "se-drottningholm-palace-postcard": (
        "Drottningholm palace Stockholm.jpg", "Anubhuti.Battu",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "se-tanum-rock-carvings-postcard": (
        "Rock carving Vitlycke Tanum.JPG", "Boberger",
        "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/559/",
    "https://whc.unesco.org/en/list/557/",
}


class SwedenPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.se = cls.doc["countries"]["SE"]

    def test_sweden_approved_and_ready_with_three_distinct_photos(self):
        approved = {code for code, v in self.doc["countries"].items()
                    if v["status"] == "approved"}
        self.assertIn("SE", approved)
        self.assertGreaterEqual(len(approved), 34)
        self.assertEqual(self.se["status"], "approved")
        self.assertEqual(set(self.se["travelStops"]), set(PHOTOS))
        self.assertEqual(len(self.se["portraitPhotos"]), 1)
        self.assertEqual(len(self.se["quiz"]), 2)
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        ready, incomplete = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("SE", incomplete)
        report = country_coverage(ROOT, [{"country": "スウェーデン"}])
        self.assertEqual(report["SE"]["cover"], "assets/travel/se-stockholm-gamla-stan-cover.jpg")
        self.assertEqual(report["SE"]["quizRounds"], 2)

    def test_each_photo_has_original_commons_file_hash_author_and_license(self):
        exported = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        assets, origins = set(), set()
        for key, (original, author, license_name, license_url) in PHOTOS.items():
            with self.subTest(key=key):
                stop = self.se["travelStops"][key]
                self.assertEqual(stop, exported[key])
                name = original.replace(" ", "_")
                encoded = quote(name, safe="-_.()")
                digest = hashlib.md5(name.encode("utf-8")).hexdigest()
                self.assertEqual(
                    stop["photo"],
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + digest[0] + "/" + digest[:2] + "/" + encoded
                    + "/500px-" + encoded,
                )
                self.assertEqual(
                    stop["photoPage"],
                    "https://commons.wikimedia.org/wiki/File:" + encoded,
                )
                self.assertEqual(stop["country"], "スウェーデン")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], license_name)
                self.assertEqual(stop["licenseUrl"], license_url)
                self.assertGreater(stop["latitude"], 58)
                self.assertLess(stop["latitude"], 60)
                self.assertGreater(stop["longitude"], 11)
                self.assertLess(stop["longitude"], 19)
                self.assertNotIn(stop["photoPage"], origins)
                self.assertNotIn(stop["photoAsset"], assets)
                origins.add(stop["photoPage"])
                assets.add(stop["photoAsset"])
        cover = self.se["portraitPhotos"][0]["asset"]
        quiz_photos = {self.se["travelStops"][q["photoKey"]]["photoAsset"]
                       for q in self.se["quiz"]}
        self.assertEqual(len(quiz_photos), 2)
        self.assertNotIn(cover, quiz_photos)
        self.assertEqual(
            set(self.se["portrait"]["photos"]),
            set(PHOTOS) - {"se-stockholm-gamla-stan-cover"},
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in assets:
            self.assertIn("'" + asset + "'", worker)

    def test_drottningholm_and_tanum_essays_are_source_backed_and_separate(self):
        source_urls = set()
        for key, stop in self.se["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertEqual(len(stop["historicalSources"]), 1)
            source = stop["historicalSources"][0]
            self.assertEqual(source["checkedOn"], "2026-11-21")
            source_urls.add(source["url"])
        self.assertEqual(source_urls, SOURCES)
        self.assertEqual(
            {q["photoKey"] for q in self.se["quiz"]},
            set(PHOTOS) - {"se-stockholm-gamla-stan-cover"}
        )


if __name__ == "__main__":
    unittest.main()
