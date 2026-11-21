"""Austria is released only with three distinct licensed real local photographs."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "at-vienna-opera-cover": ("Vienna state opera.jpg", "HamedSharifian1"),
    "at-schoenbrunn-palace-postcard": ("Schoenbrunn Palace in Vienna.jpg", "Vitold Muratov"),
    "at-salzburg-old-town-postcard": ("Salzburg Altstadt, Austria.jpg", "North Cascade"),
}


class AustrianCountryReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.austria = cls.doc["countries"]["AT"]

    def test_austria_is_really_ready_for_country_reader(self):
        approved = [k for k, row in self.doc["countries"].items() if row["status"] == "approved"]
        self.assertGreaterEqual(len(approved), 28)
        self.assertEqual(self.austria["status"], "approved")
        self.assertEqual(len(self.austria["portraitPhotos"]), 1)
        self.assertEqual(len(self.austria["quiz"]), 2)
        self.assertEqual(set(self.austria["travelStops"]), set(SOURCES))
        ready, incomplete = ready_country_codes(ROOT)
        self.assertIn("AT", ready)
        self.assertNotIn("AT", incomplete)
        report = country_coverage(ROOT, [{"country": "オーストリア"}])
        self.assertEqual(report["AT"]["quizRounds"], 2)
        self.assertEqual(set(report["AT"]["quizPhotoKeys"]), set(SOURCES) - {"at-vienna-opera-cover"})
        self.assertEqual(report["AT"]["cover"], "assets/travel/at-vienna-opera-cover.jpg")

    def test_verified_commons_identity_licenses_and_nonoverlapping_photos(self):
        actual = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        assets = set()
        for key, (filename, author) in SOURCES.items():
            with self.subTest(key=key):
                stop = self.austria["travelStops"][key]
                self.assertEqual(stop, actual[key])
                file = quote(filename.replace(" ", "_"), safe="-_.()")
                md5 = hashlib.md5(filename.replace(" ", "_").encode("utf-8")).hexdigest()
                expected_page = "https://commons.wikimedia.org/wiki/File:" + file
                expected_thumb = ("https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                                  + md5[0] + "/" + md5[:2] + "/" + file + "/500px-" + file)
                self.assertEqual(stop["photoPage"], expected_page)
                self.assertEqual(stop["photo"], expected_thumb)
                self.assertEqual(stop["country"], "オーストリア")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], "CC BY-SA 4.0")
                self.assertEqual(stop["licenseUrl"], "https://creativecommons.org/licenses/by-sa/4.0/")
                self.assertNotIn(stop["photoAsset"], assets)
                assets.add(stop["photoAsset"])
        cover = self.austria["portraitPhotos"][0]["asset"]
        answers = {self.austria["travelStops"][q["photoKey"]]["photoAsset"]
                   for q in self.austria["quiz"]}
        self.assertNotIn(cover, answers)
        self.assertEqual(len(answers), 2)

    def test_two_historical_microtrips_and_offline_cache(self):
        urls = {"https://whc.unesco.org/en/list/786",
                "https://whc.unesco.org/en/list/784"}
        found = set()
        for key, stop in self.austria["travelStops"].items():
            if stop.get("coverOnly"):
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(t) <= 360 for t in stop["travelStory"]))
            found.update(src["url"] for src in stop["historicalSources"])
        self.assertEqual(found, urls)
        sw = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(sw, r"yoru9-shell-v[0-9]+")
        for key in SOURCES:
            self.assertIn("assets/travel/" + key + ".jpg", sw)


if __name__ == "__main__":
    unittest.main()
