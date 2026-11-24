"""Malaysia release is backed by independent UNESCO sources, three distinct actual CC photos, and regional safety disclosure."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content,_commons_identity
from check_country_experience import country_coverage
from country_manifest_format import validate
ROOT=Path(__file__).resolve().parents[1]
HASHES={
 "MY-0.jpg":"f2de8cde67d10d7a0040898b816fdc2fceecdd869ab8f574a8c708e3491c80be",
 "MY-1.jpg":"ba9a7b95eeeaa3a6e74911a8c586918ac013fd84ef927fd472fdff715b43c66c",
 "MY-2.jpg":"b75c49aa2f60936758c2779ec9d92af6bbef1d3b9b1317d2e0e81a48d3f6bd9a"
}
class MalaysiaReleaseTests(unittest.TestCase):
 def test_photo_and_quiz_identity_and_readiness(self):
  doc=check_country_content(ROOT)
  entry=doc["countries"]["MY"]
  self.assertEqual(entry["status"],"approved")
  self.assertEqual(len(entry["portraitPhotos"]),1)
  self.assertEqual(len(entry["travelStops"]),3)
  self.assertEqual(len(entry["quiz"]),2)
  self.assertEqual(set(country_coverage(ROOT,[{"country":"MY"}])),{"MY"})
  self.assertEqual(len({_commons_identity(s["photoPage"]) for s in entry["travelStops"].values()}),3)
  self.assertIn("外務省",entry["portrait"]["body"])
  self.assertIn("UNESCO登録資産の構成物と断定しません",entry["travelStops"]["my-georgetown-woodville-postcard"]["note"])
  self.assertIn("洞窟内部は写っていません",entry["travelStops"]["my-mulu-garden-of-eden-postcard"]["photoCaption"])
  self.assertEqual(entry["travelStops"]["my-mulu-garden-of-eden-postcard"]["author"],"Bernard DUPONT from FRANCE")
  for q in entry["quiz"]:
   stop=entry["travelStops"][q["photoKey"]]
   self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
   self.assertTrue(any("whc.unesco.org" in s["url"] for s in stop["historicalSources"]))
   self.assertTrue(any("anzen.mofa.go.jp" in s["url"] for s in stop["historicalSources"]))
  self.assertEqual(len(validate(ROOT/"country-content.json")["countries"]),196)
 def test_exact_reviewed_photographs_have_pinned_hashes(self):
  data=check_country_content(ROOT)["countries"]["MY"]
  rows=json.loads((ROOT/"editorial-country-photo-reviews/cache-seeds.json").read_text())["photos"]
  rows=[r for r in rows if r["country"]=="マレーシア"]
  self.assertEqual({r["file"]:r["sha256"] for r in rows},HASHES)
  self.assertEqual({r["photoAsset"] for r in rows},{s["photoAsset"] for s in data["travelStops"].values()})
  self.assertEqual(sum(r["cover"] for r in rows),1)
  for r in rows:
   stop=next(x for x in data["travelStops"].values() if x["photoAsset"]==r["photoAsset"])
   for key in ("photoAsset","photo","photoPage","author","license","licenseUrl","country","place"):
    self.assertEqual(r[key],stop[key])
   self.assertEqual(r["runId"],45291236614)
  review=json.loads((ROOT/"editorial-country-photo-reviews/malaysia-20261124.json").read_text())
  self.assertFalse(review["publicationEligible"])
  self.assertEqual(review["artifact"]["artifactId"],14874936176)
if __name__=="__main__":
 unittest.main()
