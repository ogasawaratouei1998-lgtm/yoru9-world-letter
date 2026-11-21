"""User-approved country expansion: three distinct real photos per country."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes

ROOT=Path(__file__).resolve().parents[1]
PHOTOS={
 "EG":{
  "eg-cairo-skyline-cover":("Cairo-skyline.jpg","Ahmed Atef (El-Mosawer)"),
  "eg-giza-pyramid-postcard":("Great Pyramid Giza.jpg","Ireneusz Jerzy Borysiewicz"),
  "eg-abu-simbel-postcard":("Abu Simbel Great Temple.jpg","Benjamin Inbar")},
 "TR":{
  "tr-istanbul-sunset-cover":("Istanbul sky2.jpg","Mobina iz"),
  "tr-hagia-sophia-postcard":("Hagia Sophia Istanbul 4.jpg","Adnane Chahboun"),
  "tr-cappadocia-rocks-postcard":("Kapadokya peri bacaları.jpg","Muhammed Diler")},
 "TH":{
  "th-bangkok-wat-arun-cover":("Bangkok Wat Arun.jpg","Cun Cun"),
  "th-ayutthaya-mahathat-postcard":("Ayutthaya Wat Mahathat 01.jpg","ErwinMeier"),
  "th-sukhothai-park-postcard":("Sukhothai HistoricalPark.jpg","Khunmoohan")}
}
OFFICIAL_SOURCES={
 "EG":{"https://whc.unesco.org/en/list/86/","https://whc.unesco.org/en/list/88/"},
 "TR":{"https://whc.unesco.org/en/list/356/","https://whc.unesco.org/en/list/357/"},
 "TH":{"https://whc.unesco.org/en/list/576/","https://whc.unesco.org/en/list/574/"}
}


class FourthBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=check_country_content(ROOT)
        cls.stops=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))

    def test_twenty_four_countries_are_ready_not_placeholder_approved(self):
        ready,pending=ready_country_codes(ROOT)
        self.assertGreaterEqual(len(ready),28)
        self.assertEqual(sum(row["status"]=="pending"
                             for row in self.doc["countries"].values()),196-len(ready))
        for code in PHOTOS:
            with self.subTest(country=code):
                c=self.doc["countries"][code]
                self.assertEqual(c["status"],"approved")
                self.assertIn(code,ready)
                self.assertGreaterEqual(len(c["portrait"]["body"]),145)
                self.assertTrue(c["portrait"]["sourceUrl"].startswith("https://whc.unesco.org/"))
                self.assertEqual(set(c["travelStops"]),set(PHOTOS[code]))
                self.assertEqual(len(c["portraitPhotos"]),1)
                self.assertEqual(len(c["quiz"]),2)
                cover=c["portraitPhotos"][0]["asset"]
                quizzes={c["travelStops"][q["photoKey"]]["photoAsset"] for q in c["quiz"]}
                self.assertEqual(len(quizzes),2)
                self.assertNotIn(cover,quizzes)
                self.assertTrue(all(q["photoLabel"].startswith("正解写真｜")
                                    for q in c["quiz"]))

    def test_all_nine_commons_photos_have_matching_creators_license_hash_and_country(self):
        assets=set()
        for code,records in PHOTOS.items():
            c=self.doc["countries"][code]
            for key,(file,author) in records.items():
                with self.subTest(code=code,key=key):
                    s=c["travelStops"][key]
                    self.assertEqual(s,self.stops[key])
                    self.assertEqual(s["country"],c["name"])
                    self.assertEqual(s["author"],author)
                    self.assertEqual(s["license"],"CC BY-SA 4.0")
                    self.assertEqual(s["licenseUrl"],"https://creativecommons.org/licenses/by-sa/4.0/")
                    filename=file.replace(" ","_")
                    encoded=quote(filename,safe="-_.()")
                    digest=hashlib.md5(filename.encode("utf-8")).hexdigest()
                    path=digest[0]+"/"+digest[:2]+"/"+encoded
                    self.assertEqual(s["photoPage"],"https://commons.wikimedia.org/wiki/File:"+encoded)
                    self.assertEqual(s["photo"],"https://thumb.wikimedia.org/wikipedia/commons/thumb/"+
                                             path+"/500px-"+encoded)
                    self.assertNotIn(s["photoAsset"],assets)
                    assets.add(s["photoAsset"])
        self.assertEqual(len(assets),9)

    def test_six_long_microtrips_have_independent_unesco_history_references(self):
        for code,expected in OFFICIAL_SOURCES.items():
            entry=self.doc["countries"][code]
            actual=set()
            for key,s in entry["travelStops"].items():
                if s.get("coverOnly"):
                    continue
                self.assertTrue(s.get("famousTourist"))
                self.assertEqual(len(s["travelStory"]),2)
                self.assertTrue(all(110<=len(p)<=360 for p in s["travelStory"]))
                self.assertNotEqual(s["travelStory"][0],s["travelStory"][1])
                for source in s["historicalSources"]:
                    self.assertEqual(source["checkedOn"],"2026-11-21")
                    actual.add(source["url"])
            self.assertEqual(actual,expected)

    def test_offline_shell_caches_the_nine_new_correct_licensed_images(self):
        sw=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("yoru9-shell-v62",sw)
        for entries in PHOTOS.values():
            for key in entries:
                self.assertIn("assets/travel/"+key+".jpg",sw)


if __name__=="__main__":
    unittest.main()
