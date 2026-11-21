"""Country editorial manifest is canonical; pending material cannot ship silently."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from country_content import check_country_content, load_country_content, sync_country_content
from check_country_experience import country_coverage

ROOT=Path(__file__).resolve().parents[1]
FILES=("country-content.json","country-catalog.json","index.html",
       "world-passport.js","travel-stops.json","country-highlights.json")


class CountryContentTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for file in FILES:
            shutil.copy2(ROOT/file,self.root/file)

    def test_whole_196_location_dataset_matches_runtime(self):
        doc=check_country_content(ROOT)
        self.assertEqual(len(doc["countries"]),196)
        self.assertEqual({code for code,row in doc["countries"].items()
                          if row["status"]=="approved"},{"IT","DE","US"})
        self.assertGreaterEqual(len(doc["travelOrder"]),40)
        self.assertTrue(doc["countries"]["IT"]["portrait"]["body"])
        self.assertEqual(doc["countries"]["NG"]["status"],"pending")

    def test_edited_postcard_must_be_synced_before_release(self):
        file=self.root/"country-content.json"
        data=json.loads(file.read_text(encoding="utf-8"))
        data["countries"]["IT"]["travelStops"]["italy-pisa-tower-postcard"]["travelStory"][0]+=" 昔の風景をたどります。"
        file.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"IT.travelStops"):
            check_country_content(self.root)
        sync_country_content(self.root)
        check_country_content(self.root)
        exported=json.loads((self.root/"travel-stops.json").read_text(encoding="utf-8"))
        self.assertEqual(exported["italy-pisa-tower-postcard"]["travelStory"],
                         data["countries"]["IT"]["travelStops"]["italy-pisa-tower-postcard"]["travelStory"])

    def test_legacy_photo_mutation_is_rejected(self):
        path=self.root/"travel-stops.json"
        stops=json.loads(path.read_text(encoding="utf-8"))
        stops["italy-pisa-tower-postcard"]["country"]="ドイツ"
        path.write_text(json.dumps(stops,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            check_country_content(self.root)

    def test_sync_preserves_readiness_of_published_three(self):
        sync_country_content(self.root)
        txt=(self.root/"world-passport.js").read_text(encoding="utf-8")
        section=txt.split(" US:[",1)[1].split(" NZ:[",1)[0]
        self.assertEqual(section.count("question:"),2,section[:1000])
        result=country_coverage(self.root,[{"id":"a","country":"イタリア"},
                                          {"id":"b","country":"ドイツ"},
                                          {"id":"c","country":"アメリカ合衆国"}])
        self.assertEqual(set(result),{"IT","DE","US"})

    def test_pending_country_cannot_be_promoted_without_photos(self):
        file=self.root/"country-content.json"
        data=json.loads(file.read_text(encoding="utf-8"))
        data["countries"]["NG"]["status"]="approved"
        file.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"NG: approval"):
            load_country_content(self.root)

    def test_unreviewed_country_no_fabricated_photographs(self):
        doc=load_country_content(self.root)
        country=doc["countries"]["NG"]
        self.assertFalse(country["portraitPhotos"])
        self.assertFalse(country["travelStops"])


if __name__=="__main__":
    unittest.main()
