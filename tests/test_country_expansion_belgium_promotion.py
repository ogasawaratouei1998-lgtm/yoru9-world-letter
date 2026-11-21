"""Belgium release requires three independent place-matched, licensed Wikimedia photographs."""
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
    "be-atomium-brussels-cover": ("Atomium, Brussels, Belgium.jpg", "Theedi"),
    "be-grand-place-postcard": ("Grand Place Brussels1.jpg", "Sandor Somkuti"),
    "be-bruges-belfry-postcard": (
        "Belfry of Bruges, view from the canal, Belgium - April 2024.jpg", "Zeete"),
}
UNESCO = {"https://whc.unesco.org/en/list/857/",
          "https://whc.unesco.org/en/list/996/"}


class BelgiumPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = check_country_content(ROOT)
        cls.belgium = cls.data["countries"]["BE"]

    def test_country_is_really_approved_and_mobile_reader_has_two_photo_quizzes(self):
        country = self.belgium
        approved = {code for code,c in self.data["countries"].items()
                    if c["status"] == "approved"}
        self.assertIn("BE", approved)
        self.assertGreaterEqual(len(approved), 30)
        self.assertEqual(country["status"], "approved")
        self.assertEqual(len(country["portraitPhotos"]), 1)
        self.assertEqual(len(country["quiz"]), 2)
        self.assertEqual(set(country["travelStops"]), set(PHOTOS))
        ready,broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("BE", broken)
        info = country_coverage(ROOT, [{"country": "ベルギー"}])
        self.assertEqual(info["BE"]["cover"], "assets/travel/be-atomium-brussels-cover.jpg")
        self.assertEqual(info["BE"]["quizRounds"], 2)

    def test_all_three_images_match_independent_commons_files_and_author_credits(self):
        export = json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        assets = set()
        for key,(filename,author) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.belgium["travelStops"][key]
                self.assertEqual(stop,export[key])
                name = filename.replace(" ","_")
                quoted = quote(name,safe="-_.()")
                digest = hashlib.md5(name.encode("utf-8")).hexdigest()
                self.assertEqual(stop["photo"],"https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                                 +digest[0]+"/"+digest[:2]+"/"+quoted+"/500px-"+quoted)
                self.assertEqual(stop["photoPage"],"https://commons.wikimedia.org/wiki/File:"+quoted)
                self.assertEqual(stop["author"],author)
                self.assertEqual(stop["country"],"ベルギー")
                self.assertEqual(stop["license"],"CC BY-SA 4.0")
                self.assertEqual(stop["licenseUrl"],"https://creativecommons.org/licenses/by-sa/4.0/")
                self.assertNotIn(stop["photoAsset"],assets)
                assets.add(stop["photoAsset"])
        cover=self.belgium["portraitPhotos"][0]["asset"]
        quiz_assets={self.belgium["travelStops"][q["photoKey"]]["photoAsset"]
                     for q in self.belgium["quiz"]}
        self.assertEqual(len(quiz_assets),2)
        self.assertNotIn(cover,quiz_assets)
        self.assertEqual(set(self.belgium["portrait"]["photos"]),
                         set(PHOTOS)-{"be-atomium-brussels-cover"})
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("yoru9-shell-v64",worker)
        for key in PHOTOS:
            self.assertIn("assets/travel/"+key+".jpg",worker)

    def test_both_tourism_destinations_have_real_two_paragraph_unesco_essays(self):
        refs=set()
        for key,stop in self.belgium["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory",stop)
                continue
            self.assertTrue(stop.get("famousTourist"))
            self.assertEqual(len(stop["travelStory"]),2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            refs.update(row["url"] for row in stop["historicalSources"])
        self.assertEqual(refs,UNESCO)
        self.assertEqual(set(self.data["travelOrder"][-3:]),set(PHOTOS))
        self.assertEqual({q["photoKey"] for q in self.belgium["quiz"]},
                         set(PHOTOS)-{"be-atomium-brussels-cover"})

if __name__=="__main__":
    unittest.main()
