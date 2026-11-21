"""Norway releases only three distinct Commons photographs with matched provenance."""
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
 "no-oslo-skyline-cover": ("Skyline of Oslo, 2019 (01).jpg", "Bahnfrend"),
 "no-bryggen-postcard": ("Bryggen - Bergen, Norway 2021-07-30 (02).jpg", "Ryan Hodnett"),
 "no-geirangerfjord-postcard": ("Geirangerfjord from SE 10 2018 3049.jpg",
                               "Mariordo (Mario Roberto Durán Ortiz)"),
}
SOURCES = {"https://whc.unesco.org/en/list/59/",
           "https://whc.unesco.org/en/list/1195/"}

class NorwayPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.norway = cls.doc["countries"]["NO"]

    def test_ready_norway_is_a_real_twenty_sixth_approved_country(self):
        approved=[c for c,v in self.doc["countries"].items() if v["status"]=="approved"]
        self.assertGreaterEqual(len(approved),28)
        self.assertEqual(self.norway["status"],"approved")
        self.assertEqual(len(self.norway["portraitPhotos"]),1)
        self.assertEqual(len(self.norway["quiz"]),2)
        self.assertEqual(set(self.norway["travelStops"]),set(PHOTOS))
        ready,broken=ready_country_codes(ROOT)
        self.assertEqual(len(ready),len(approved))
        self.assertIn("NO",ready)
        self.assertNotIn("NO",broken)
        experience=country_coverage(ROOT,[{"country":"ノルウェー"}])
        self.assertEqual(experience["NO"]["quizRounds"],2)
        self.assertEqual(experience["NO"]["cover"],"assets/travel/no-oslo-skyline-cover.jpg")

    def test_three_unique_photo_file_authors_hashes_and_credits(self):
        exports=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        assets=set()
        for key,(filename,author) in PHOTOS.items():
            stop=self.norway["travelStops"][key]
            self.assertEqual(exports[key],stop)
            file=quote(filename.replace(" ","_"),safe="-_.()")
            md5=hashlib.md5(filename.replace(" ","_").encode("utf-8")).hexdigest()
            self.assertEqual(stop["photoPage"],"https://commons.wikimedia.org/wiki/File:"+file)
            self.assertEqual(stop["photo"],("https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                             +md5[0]+"/"+md5[:2]+"/"+file+"/500px-"+file))
            self.assertEqual(stop["author"],author)
            self.assertEqual(stop["country"],"ノルウェー")
            self.assertEqual(stop["license"],"CC BY-SA 4.0")
            self.assertEqual(stop["licenseUrl"],"https://creativecommons.org/licenses/by-sa/4.0/")
            self.assertNotIn(stop["photoAsset"],assets)
            assets.add(stop["photoAsset"])
        cover=self.norway["portraitPhotos"][0]["asset"]
        quiz_images={self.norway["travelStops"][q["photoKey"]]["photoAsset"]
                     for q in self.norway["quiz"]}
        self.assertEqual(len(quiz_images),2)
        self.assertNotIn(cover,quiz_images)

    def test_independent_unesco_readings_and_offline_photos(self):
        sources=set()
        for stop in self.norway["travelStops"].values():
            if stop.get("coverOnly"): continue
            self.assertEqual(len(stop["travelStory"]),2)
            self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
            sources.update(s["url"] for s in stop["historicalSources"])
        self.assertEqual(sources,SOURCES)
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("yoru9-shell-v63",worker)
        for key in PHOTOS:
            self.assertIn("assets/travel/"+key+".jpg",worker)

if __name__=="__main__":
    unittest.main()
