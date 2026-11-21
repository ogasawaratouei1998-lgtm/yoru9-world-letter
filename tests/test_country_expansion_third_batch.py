"""Three fully prepared countries: genuine photo hashes, credits, essays and quiz safety."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote, unquote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes

ROOT=Path(__file__).resolve().parents[1]
PHOTO_SOURCES={
    "CH":{
       "ch-lucerne-chapel-cover":("The Chapel Bridge in Lucerne.jpg","CulturedWatermelons"),
       "ch-bern-old-city-postcard":("Old City of Bern-Bern.jpg","Yair Haklai"),
       "ch-aletsch-glacier-postcard":("Aletsch Glacier view.jpg","Seba3mmm")},
    "PT":{
       "pt-belem-tower-cover":("Belém Tower in Lisbon.jpg","Lisbon Photoshoots"),
       "pt-jeronimos-monastery-postcard":("Mosteiro Jerónimos, Lisbon.jpg","MiguelNS85"),
       "pt-pena-palace-postcard":("Pena Palace Sintra.jpg","Sergey Pesterev")},
    "GR":{
       "gr-athens-skyline-cover":("Athens skyline.JPG","Orlovic"),
       "gr-parthenon-postcard":("Parthenon in Greece.jpg","Srishti Sethi"),
       "gr-delphi-apollo-postcard":("Delphi Temple of Apollo.jpg","Skyring")},
}
HISTORY={
    "CH":{"https://whc.unesco.org/en/list/267/","https://whc.unesco.org/en/list/1037/"},
    "PT":{"https://whc.unesco.org/en/list/263/","https://whc.unesco.org/en/list/723/"},
    "GR":{"https://whc.unesco.org/en/list/404/","https://whc.unesco.org/en/list/393/"}
}


class ThirdCountryExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical=check_country_content(ROOT)
        cls.export=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))

    def test_three_countries_are_ready_with_two_unrepeated_quiz_photographs(self):
        ready,pending=ready_country_codes(ROOT)
        self.assertEqual(len(ready),24)
        self.assertEqual(len(self.canonical["countries"]),196)
        for code,files in PHOTO_SOURCES.items():
            with self.subTest(country=code):
                entry=self.canonical["countries"][code]
                self.assertEqual(entry["status"],"approved")
                self.assertIn(code,ready)
                self.assertNotIn(code,pending)
                self.assertEqual(len(entry["portraitPhotos"]),1)
                self.assertEqual(len(entry["quiz"]),2)
                self.assertEqual(set(entry["travelStops"]),set(files))
                self.assertGreaterEqual(len(entry["portrait"]["body"]),145)
                primary=entry["portraitPhotos"][0]["asset"]
                quiz_files={entry["travelStops"][q["photoKey"]]["photoAsset"]
                           for q in entry["quiz"]}
                self.assertEqual(len(quiz_files),2)
                self.assertNotIn(primary,quiz_files)
                self.assertTrue(all(q["photoLabel"].startswith("正解写真｜") for q in entry["quiz"]))

    def test_nine_commons_photos_have_exact_file_hash_country_and_creator(self):
        assets=set()
        for code,entries in PHOTO_SOURCES.items():
            for key,(filename,author) in entries.items():
                with self.subTest(code=code,key=key):
                    row=self.canonical["countries"][code]
                    stop=row["travelStops"][key]
                    self.assertEqual(stop,self.export[key])
                    self.assertEqual(stop["country"],row["name"])
                    self.assertEqual(stop["author"],author)
                    self.assertEqual(stop["license"],"CC BY-SA 4.0")
                    self.assertEqual(stop["licenseUrl"],
                                     "https://creativecommons.org/licenses/by-sa/4.0/")
                    encoded=quote(filename.replace(" ","_"),safe="-_.()")
                    self.assertEqual(stop["photoPage"],
                        "https://commons.wikimedia.org/wiki/File:"+encoded)
                    md5=hashlib.md5(filename.replace(" ","_").encode("utf-8")).hexdigest()
                    self.assertEqual(stop["photo"],
                        "https://thumb.wikimedia.org/wikipedia/commons/thumb/"+
                        md5[0]+"/"+md5[:2]+"/"+encoded+"/500px-"+encoded)
                    self.assertNotIn(stop["photoAsset"],assets)
                    assets.add(stop["photoAsset"])
        self.assertEqual(len(assets),9)

    def test_six_original_travel_essays_have_relevant_unesco_sources(self):
        for code,urls in HISTORY.items():
            entry=self.canonical["countries"][code]
            actual=set()
            for key,stop in entry["travelStops"].items():
                if stop.get("coverOnly"):
                    continue
                self.assertEqual(len(stop["travelStory"]),2)
                self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
                self.assertNotEqual(stop["travelStory"][0],stop["travelStory"][1])
                for src in stop["historicalSources"]:
                    self.assertEqual(src["checkedOn"],"2026-11-21")
                    actual.add(src["url"])
            self.assertEqual(actual,urls)

    def test_worker_offline_quiz_photos_always_match_manifest(self):
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("yoru9-shell-v57",worker)
        for country in PHOTO_SOURCES.values():
            for key in country:
                self.assertIn("assets/travel/"+key+".jpg",worker)


if __name__=="__main__":
    unittest.main()
