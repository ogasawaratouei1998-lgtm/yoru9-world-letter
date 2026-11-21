"""Slovenia must publish with three independently credited Commons photographs and UNESCO trips."""
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
    "si-ljubljana-panorama-cover": (
        "Panorama Ljubljane.jpg", "August Dominus",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "si-skocjan-caves-postcard": (
        "Škocjan Caves, Slovenia, 20240502 1210 7581.jpg", "Jakub Hałun",
        "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "si-triple-bridge-postcard": (
        "Triple Bridge in Ljubljana in late June.jpg", "JIP",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/390/",
    "https://whc.unesco.org/en/list/1643/",
}


class SloveniaPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.si = cls.doc["countries"]["SI"]

    def test_full_country_is_approved_and_available_for_news_release(self):
        approved = {code for code, entry in self.doc["countries"].items()
                    if entry["status"] == "approved"}
        self.assertIn("SI", approved)
        self.assertGreaterEqual(len(approved), 36)
        self.assertEqual(self.si["status"], "approved")
        self.assertEqual(len(self.si["portraitPhotos"]), 1)
        self.assertEqual(len(self.si["quiz"]), 2)
        self.assertEqual(set(self.si["travelStops"]), set(PHOTOS))
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("SI", broken)
        report = country_coverage(ROOT, [{"country": "スロベニア"}])
        self.assertEqual(report["SI"]["cover"], "assets/travel/si-ljubljana-panorama-cover.jpg")
        self.assertEqual(report["SI"]["quizRounds"], 2)

    def test_commons_photo_original_file_md5_author_license_and_no_overlap(self):
        exported = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        assets, sources = set(), set()
        for key, (filename, author, license_name, license_url) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.si["travelStops"][key]
                self.assertEqual(stop, exported[key])
                name = filename.replace(" ", "_")
                encoded = quote(name, safe="-_.()")
                digest = hashlib.md5(name.encode("utf-8")).hexdigest()
                self.assertEqual(
                    stop["photo"],
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + digest[0] + "/" + digest[:2] + "/" + encoded
                    + "/500px-" + encoded,
                )
                self.assertEqual(
                    stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + encoded
                )
                self.assertEqual(stop["country"], "スロベニア")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], license_name)
                self.assertEqual(stop["licenseUrl"], license_url)
                self.assertTrue(45 < stop["latitude"] < 47)
                self.assertTrue(13 < stop["longitude"] < 15)
                self.assertNotIn(stop["photoAsset"], assets)
                self.assertNotIn(stop["photoPage"], sources)
                assets.add(stop["photoAsset"])
                sources.add(stop["photoPage"])
        cover = self.si["portraitPhotos"][0]["asset"]
        answer_assets = {
            self.si["travelStops"][quiz["photoKey"]]["photoAsset"]
            for quiz in self.si["quiz"]
        }
        self.assertEqual(len(answer_assets), 2)
        self.assertNotIn(cover, answer_assets)
        self.assertEqual(set(self.si["portrait"]["photos"]),
                         set(PHOTOS) - {"si-ljubljana-panorama-cover"})
        sw = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(sw, r"yoru9-shell-v[0-9]+")
        for asset in assets:
            self.assertIn("'" + asset + "'", sw)

    def test_skocjan_and_plecnik_two_paragraph_trips_have_unesco_sources(self):
        refs = set()
        for key, stop in self.si["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(text) <= 360 for text in stop["travelStory"]))
            self.assertEqual(len(stop["historicalSources"]), 1)
            src = stop["historicalSources"][0]
            self.assertEqual(src["checkedOn"], "2026-11-21")
            refs.add(src["url"])
        self.assertEqual(refs, SOURCES)
        self.assertEqual(
            {q["photoKey"] for q in self.si["quiz"]},
            set(PHOTOS) - {"si-ljubljana-panorama-cover"}
        )


if __name__ == "__main__":
    unittest.main()
