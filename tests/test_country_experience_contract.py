"""Regression: published countries must retain genuinely complete portrait and passport assets."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_country_experience import country_coverage

ROOT=Path(__file__).resolve().parents[1]


class CountryExperienceContractTest(unittest.TestCase):
    def setUp(self):
        self.issue=json.loads((ROOT/"data/archive/2026-11-20.json").read_text(encoding="utf-8"))
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for path in ("index.html","world-passport.js","travel-stops.json"):
            shutil.copy2(ROOT/path,self.root/path)

    def test_all_three_published_countries_have_portraits_and_photo_quizzes(self):
        result=country_coverage(self.root,self.issue["stories"])
        self.assertEqual(set(result),{"IT","US","DE"})
        self.assertEqual({country:row["quizRounds"] for country,row in result.items()},
                         {"IT":2,"US":2,"DE":2})
        self.assertEqual(len({row["cover"] for row in result.values()}),3)
        for row in result.values():
            self.assertEqual(len(set(row["quizPhotoKeys"])),2)

    def test_missing_italian_photo_prevents_incomplete_release(self):
        path=self.root/"travel-stops.json"
        manifest=json.loads(path.read_text(encoding="utf-8"))
        manifest["italy-pisa-tower-postcard"]["author"]=""
        path.write_text(json.dumps(manifest,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"IT.*license/attribution"):
            country_coverage(self.root,self.issue["stories"])

    def test_unreviewed_country_never_silently_falls_back_to_one_question(self):
        with self.assertRaisesRegex(ValueError,"substantive country portrait"):
            country_coverage(self.root,[{"id":"verified-news-example",
                                        "country":"Nigeria"}])

    def test_legacy_country_does_not_bypass_new_country_quality_gate(self):
        with self.assertRaisesRegex(ValueError,"GB: cover source/creator"):
            country_coverage(self.root,[{"id":"verified-uk","country":"イギリス"}])

    def test_two_paragraph_travel_story_is_required_for_published_country(self):
        path=self.root/"travel-stops.json"
        manifest=json.loads(path.read_text(encoding="utf-8"))
        for item in manifest.values():
            if item.get("country")=="ドイツ" and not item.get("coverOnly") and not item.get("quizOnly"):
                item.pop("travelStory",None)
        path.write_text(json.dumps(manifest,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"DE.*detailed essay"):
            country_coverage(self.root,self.issue["stories"])

    def test_wrong_country_photo_rejected(self):
        path=self.root/"travel-stops.json"
        manifest=json.loads(path.read_text(encoding="utf-8"))
        manifest["germany-cologne-cathedral-postcard"]["country"]="イタリア"
        path.write_text(json.dumps(manifest,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"wrong country"):
            country_coverage(self.root,self.issue["stories"])

    def test_rejects_missing_german_portait(self):
        path=self.root/"index.html"
        html=path.read_text(encoding="utf-8")
        html=html.replace("DE:{lead:","DX:{lead:",1)
        path.write_text(html,encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"DE: substantive"):
            country_coverage(self.root,self.issue["stories"])


if __name__=="__main__":
    unittest.main()
