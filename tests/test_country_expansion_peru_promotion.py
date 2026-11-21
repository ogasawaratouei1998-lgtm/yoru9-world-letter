"""Peru release requires three distinct licensed and geographically correct Commons photos."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes
from check_country_experience import country_coverage
ROOT=Path(__file__).resolve().parents[1]
PHOTOS={
 "pe-lima-plaza-mayor-cover":("Plaza Mayor de Lima 04.jpg","Ovruni"),
 "pe-machu-picchu-postcard":("Machu Picchu, Perú.jpg","Rodolfo pimentel"),
 "pe-cusco-historic-center-postcard":("Main Square and Historic Center, Cusco, PE.jpg","Clyde Charles Brown"),
}
class PeruPromotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=check_country_content(ROOT)
  cls.peru=cls.doc["countries"]["PE"]
 def test_peru_is_ready_with_two_nonrepeated_photo_quizzes(self):
  self.assertGreaterEqual(len([x for x in self.doc["countries"].values() if x["status"]=="approved"]),28)
  self.assertEqual(self.peru["status"],"approved")
  self.assertEqual(len(self.peru["portraitPhotos"]),1)
  self.assertEqual(len(self.peru["quiz"]),2)
  self.assertEqual(set(self.peru["travelStops"]),set(PHOTOS))
  ready,errors=ready_country_codes(ROOT)
  self.assertGreaterEqual(len(ready),28)
  self.assertIn("PE",ready)
  self.assertNotIn("PE",errors)
  report=country_coverage(ROOT,[{"country":"ペルー"}])
  self.assertEqual(report["PE"]["quizRounds"],2)
  self.assertEqual(report["PE"]["cover"],"assets/travel/pe-lima-plaza-mayor-cover.jpg")
 def test_three_unique_peru_photo_file_pages_hashes_authors_and_credits(self):
  export=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
  assets=set()
  for key,(filename,author) in PHOTOS.items():
   stop=self.peru["travelStops"][key]
   self.assertEqual(export[key],stop)
   name=filename.replace(" ","_")
   encoded=quote(name,safe="-_.()")
   md5=hashlib.md5(name.encode("utf-8")).hexdigest()
   self.assertEqual(stop["photoPage"],"https://commons.wikimedia.org/wiki/File:"+encoded)
   self.assertEqual(stop["photo"],"https://thumb.wikimedia.org/wikipedia/commons/thumb/"+
                          md5[0]+"/"+md5[:2]+"/"+encoded+"/500px-"+encoded)
   self.assertEqual(stop["author"],author)
   self.assertEqual(stop["country"],"ペルー")
   self.assertEqual(stop["license"],"CC BY-SA 4.0")
   self.assertEqual(stop["licenseUrl"],"https://creativecommons.org/licenses/by-sa/4.0/")
   self.assertNotIn(stop["photoAsset"],assets)
   assets.add(stop["photoAsset"])
  cover=self.peru["portraitPhotos"][0]["asset"]
  quiz={self.peru["travelStops"][q["photoKey"]]["photoAsset"] for q in self.peru["quiz"]}
  self.assertEqual(len(quiz),2)
  self.assertNotIn(cover,quiz)
 def test_heritage_source_and_two_full_travel_essays_are_in_offline_shell(self):
  source=set()
  for stop in self.peru["travelStops"].values():
   if stop.get("coverOnly"):continue
   self.assertEqual(len(stop["travelStory"]),2)
   self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
   source.update(s["url"] for s in stop["historicalSources"])
  self.assertEqual(source,{"https://whc.unesco.org/en/list/274/","https://whc.unesco.org/en/list/273/"})
  sw=(ROOT/"service-worker.js").read_text(encoding="utf-8")
  self.assertIn("yoru9-shell-v64",sw)
  for key in PHOTOS:
   self.assertIn("assets/travel/"+key+".jpg",sw)
if __name__=="__main__":
 unittest.main()
