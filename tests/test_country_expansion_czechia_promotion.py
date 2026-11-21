"""Czechia is published only with three separately licensed and located Commons photographs."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "cz-prague-skyline-cover": ("Prague skyline at dawn.jpg", "Petar Milošević"),
    "cz-charles-bridge-postcard": ("Charles Bridge in Old Prague.jpg", "Flukes69"),
    "cz-cesky-krumlov-postcard": ("Cesky Krumlov Landscape.jpg", "MihaiAlinAnghel"),
}
SOURCES = {
    "https://whc.unesco.org/en/list/616/",
    "https://whc.unesco.org/en/list/617/",
}


class CzechiaPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.cz = cls.doc["countries"]["CZ"]

    def test_approved_reader_has_country_cover_and_two_complete_quiz_rounds(self):
        approved = {code for code,row in self.doc["countries"].items()
                    if row["status"] == "approved"}
        self.assertIn("CZ", approved)
        self.assertGreaterEqual(len(approved), 28)
        self.assertEqual(self.cz["status"], "approved")
        self.assertEqual(len(self.cz["portraitPhotos"]), 1)
        self.assertEqual(len(self.cz["quiz"]), 2)
        self.assertEqual(set(self.cz["travelStops"]), set(FILES))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("CZ", broken)
        report = country_coverage(ROOT,[{"country": "チェコ"}])
        self.assertEqual(report["CZ"]["cover"],"assets/travel/cz-prague-skyline-cover.jpg")
        self.assertEqual(report["CZ"]["quizRounds"], 2)

    def test_commons_photos_identity_attribution_and_offline_assets_match(self):
        emitted = json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        assets = set()
        photos = set()
        for key, (filename,author) in FILES.items():
            with self.subTest(key=key):
                stop = self.cz["travelStops"][key]
                self.assertEqual(stop, emitted[key])
                encoded = quote(filename.replace(" ","_"),safe="-_.()")
                digest = hashlib.md5(filename.replace(" ","_").encode("utf-8")).hexdigest()
                expected = "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + digest[0] + "/" + digest[:2] + "/" + encoded + "/500px-" + encoded
                self.assertEqual(stop["photo"], expected)
                self.assertEqual(stop["photoPage"],"https://commons.wikimedia.org/wiki/File:"+encoded)
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["country"], "チェコ")
                self.assertEqual(stop["license"],"CC BY-SA 4.0")
                self.assertEqual(stop["licenseUrl"],"https://creativecommons.org/licenses/by-sa/4.0/")
                self.assertNotIn(stop["photoAsset"],assets)
                self.assertNotIn(stop["photoPage"],photos)
                assets.add(stop["photoAsset"])
                photos.add(stop["photoPage"])
        cover = self.cz["portraitPhotos"][0]["asset"]
        quiz = {self.cz["travelStops"][q["photoKey"]]["photoAsset"]
                for q in self.cz["quiz"]}
        self.assertEqual(len(quiz),2)
        self.assertNotIn(cover,quiz)
        self.assertEqual(set(self.cz["portrait"]["photos"]),set(FILES)-{"cz-prague-skyline-cover"})
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for key in FILES:
            self.assertIn("assets/travel/"+key+".jpg",worker)

    def test_two_complete_source_backed_distinct_mini_travel_essays(self):
        sources = set()
        for key,stop in self.cz["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory",stop)
                continue
            self.assertTrue(stop["famousTourist"])
            self.assertEqual(len(stop["travelStory"]),2)
            self.assertTrue(all(110<=len(text)<=360 for text in stop["travelStory"]))
            sources.update(src["url"] for src in stop["historicalSources"])
        self.assertEqual(sources,SOURCES)
        self.assertTrue(set(FILES).issubset(self.doc["travelOrder"]))
        self.assertEqual(set(q["photoKey"] for q in self.cz["quiz"]),
                         set(FILES)-{"cz-prague-skyline-cover"})


if __name__=="__main__":
    unittest.main()
