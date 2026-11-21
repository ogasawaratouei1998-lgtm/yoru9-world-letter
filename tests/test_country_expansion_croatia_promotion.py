"""Croatia is released only with three distinct, properly sourced real-world photographs."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = {
    "hr-zagreb-panorama-cover": ("Zagreb, Panorama 001.jpg", "Vojtěch Dočkal"),
    "hr-dubrovnik-old-city-postcard": ("Old Town of Dubrovnik.jpg", "Pierre König"),
    "hr-plitvice-lakes-postcard": ("Plitvice Lakes.jpg", "Matthiasmullie"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/95/",
    "https://whc.unesco.org/en/list/98/",
}


class CroatiaPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.croatia = cls.doc["countries"]["HR"]

    def test_croatia_is_approved_and_has_separate_country_and_quiz_photos(self):
        country = self.croatia
        approved = {code for code, row in self.doc["countries"].items()
                    if row["status"] == "approved"}
        self.assertIn("HR", approved)
        self.assertGreaterEqual(len(approved), 29)
        self.assertEqual(country["status"], "approved")
        self.assertEqual(len(country["portraitPhotos"]), 1)
        self.assertEqual(len(country["quiz"]), 2)
        self.assertEqual(set(country["travelStops"]), set(PHOTOS))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("HR", broken)
        coverage = country_coverage(ROOT, [{"country": "クロアチア"}])
        self.assertEqual(coverage["HR"]["quizRounds"], 2)
        self.assertEqual(coverage["HR"]["cover"], "assets/travel/hr-zagreb-panorama-cover.jpg")

    def test_three_unique_commons_files_have_exact_paths_authors_and_licenses(self):
        exported = json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        assets, pages = set(), set()
        for key, (file, author) in PHOTOS.items():
            with self.subTest(key=key):
                stop = self.croatia["travelStops"][key]
                self.assertEqual(exported[key], stop)
                original = file.replace(" ", "_")
                escaped = quote(original, safe="-_.()")
                digest = hashlib.md5(original.encode("utf-8")).hexdigest()
                self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                                 + digest[0] + "/" + digest[:2] + "/" + escaped + "/500px-" + escaped)
                self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + escaped)
                self.assertEqual(stop["country"], "クロアチア")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], "CC BY-SA 4.0")
                self.assertEqual(stop["licenseUrl"], "https://creativecommons.org/licenses/by-sa/4.0/")
                self.assertNotIn(stop["photoAsset"], assets)
                self.assertNotIn(stop["photoPage"], pages)
                assets.add(stop["photoAsset"])
                pages.add(stop["photoPage"])
        cover = self.croatia["portraitPhotos"][0]["asset"]
        quiz_assets = {self.croatia["travelStops"][q["photoKey"]]["photoAsset"]
                       for q in self.croatia["quiz"]}
        self.assertNotIn(cover, quiz_assets)
        self.assertEqual(len(quiz_assets), 2)
        self.assertEqual(set(self.croatia["portrait"]["photos"]),
                         set(PHOTOS)-{"hr-zagreb-panorama-cover"})

    def test_distinct_independent_unesco_essays_are_available_offline(self):
        sources = set()
        for stop in self.croatia["travelStops"].values():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            sources.update(src["url"] for src in stop["historicalSources"])
        self.assertEqual(sources, SOURCES)
        self.assertTrue(set(PHOTOS).issubset(self.doc["travelOrder"]))
        sw = (ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(sw, r"yoru9-shell-v[0-9]+")
        for key in PHOTOS:
            self.assertIn("assets/travel/"+key+".jpg", sw)


if __name__ == "__main__":
    unittest.main()
