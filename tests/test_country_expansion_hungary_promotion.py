"""Hungary release requires three independently attributed and located Commons photographs."""
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
    "hu-budapest-parliament-cover": (
        "Hungarian Parliament Building, Budapest, Hungary.jpg", "CivArmy",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "hu-buda-castle-postcard": (
        "Buda Castle, Budapest.jpg", "Michal Klajban",
        "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "hu-holloko-village-postcard": (
        "Holloko Village Center.jpg", "Kfbs06",
        "CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/400/",
    "https://whc.unesco.org/en/list/401/",
}


class HungaryPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.hu = cls.doc["countries"]["HU"]

    def test_hungary_approved_and_ready_with_independent_quiz_photo_answers(self):
        approved = {code for code, entry in self.doc["countries"].items()
                    if entry["status"] == "approved"}
        self.assertIn("HU", approved)
        self.assertGreaterEqual(len(approved), 35)
        self.assertEqual(self.hu["status"], "approved")
        self.assertEqual(len(self.hu["portraitPhotos"]), 1)
        self.assertEqual(len(self.hu["quiz"]), 2)
        self.assertEqual(set(self.hu["travelStops"]), set(PHOTOS))
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        ready, incomplete = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("HU", incomplete)
        report = country_coverage(ROOT, [{"country": "ハンガリー"}])
        self.assertEqual(report["HU"]["cover"], "assets/travel/hu-budapest-parliament-cover.jpg")
        self.assertEqual(report["HU"]["quizRounds"], 2)

    def test_three_distinct_original_commons_files_authors_licenses_and_locations(self):
        exported = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        photo_assets, source_pages = set(), set()
        for key, (filename, creator, license_name, license_url) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.hu["travelStops"][key]
                self.assertEqual(stop, exported[key])
                native = filename.replace(" ", "_")
                encoded = quote(native, safe="-_.()")
                digest = hashlib.md5(native.encode("utf-8")).hexdigest()
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
                self.assertEqual(stop["country"], "ハンガリー")
                self.assertEqual(stop["author"], creator)
                self.assertEqual(stop["license"], license_name)
                self.assertEqual(stop["licenseUrl"], license_url)
                self.assertTrue(47 <= stop["latitude"] <= 49)
                self.assertTrue(18 <= stop["longitude"] <= 21)
                self.assertNotIn(stop["photoAsset"], photo_assets)
                self.assertNotIn(stop["photoPage"], source_pages)
                photo_assets.add(stop["photoAsset"])
                source_pages.add(stop["photoPage"])
        cover = self.hu["portraitPhotos"][0]["asset"]
        quiz_assets = {self.hu["travelStops"][q["photoKey"]]["photoAsset"]
                       for q in self.hu["quiz"]}
        self.assertEqual(len(quiz_assets), 2)
        self.assertNotIn(cover, quiz_assets)
        self.assertEqual(
            set(self.hu["portrait"]["photos"]),
            set(PHOTOS) - {"hu-budapest-parliament-cover"},
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in photo_assets:
            self.assertIn("'" + asset + "'", worker)

    def test_buda_castle_and_holloko_trips_are_complete_unesco_sourced_essays(self):
        urls = set()
        for key, stop in self.hu["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop["famousTourist"])
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertEqual(len(stop["historicalSources"]), 1)
            source = stop["historicalSources"][0]
            self.assertEqual(source["checkedOn"], "2026-11-21")
            urls.add(source["url"])
        self.assertEqual(urls, SOURCES)
        self.assertEqual(
            {q["photoKey"] for q in self.hu["quiz"]},
            set(PHOTOS) - {"hu-budapest-parliament-cover"},
        )


if __name__ == "__main__":
    unittest.main()
