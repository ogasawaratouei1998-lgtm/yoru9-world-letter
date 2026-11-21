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

    def test_all_196_geographic_names_come_from_one_catalog(self):
        from check_country_experience import COUNTRY_NAMES
        from country_codes import catalog, country_codes
        canonical={row["code"]:row["name"] for row in catalog()}
        self.assertEqual(len(canonical),196)
        self.assertEqual(COUNTRY_NAMES,canonical)
        # Previously absent from the hardcoded dozen. These must be recognized
        # correctly while remaining unapproved, rather than given a fake photo.
        for code in ("NG","ID","IS","ZA","TT"):
            self.assertEqual(country_codes(canonical[code]),[code])
        self.assertEqual(country_codes("アンティグア・バーブーダ"),["AG"])
        with self.assertRaisesRegex(ValueError,"NG: country content awaiting editorial approval"):
            country_coverage(ROOT,[{"country":canonical["NG"]}])

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

    def test_new_countries_have_complete_local_quiz_and_portrait_assets(self):
        report=country_coverage(self.root,[{"id":"verified-uk","country":"イギリス"},
                                          {"id":"verified-jp","country":"日本"}])
        self.assertEqual(set(report),{"GB","JP"})
        self.assertEqual(report["GB"]["cover"],"assets/travel/wales-cardiff-castle.jpg")
        self.assertEqual(report["JP"]["cover"],"assets/travel/kyoto-kinkakuji.jpg")

    def test_second_usable_us_cover_must_not_repeat_a_quiz_answer(self):
        # Simulate a photographer's main cover failing to load. The browser
        # then tries the second selectable cover, which must also be safe.
        path=self.root/"index.html"
        page=path.read_text(encoding="utf-8")
        import re
        registry=re.search(r"(?m)^const TODAY_COUNTRY_PHOTOS=Object\.freeze\((.*)\);$",page)
        self.assertIsNotNone(registry)
        covers=json.loads(registry.group(1))
        alternate=next(photo for photo in covers["US"]
                       if photo.get("asset")=="assets/travel/san-francisco-golden-gate.jpg")
        alternate.pop("avoidCover")
        replacement="const TODAY_COUNTRY_PHOTOS=Object.freeze("+json.dumps(
            covers,ensure_ascii=False,separators=(",",":"))+");"
        path.write_text(page[:registry.start()]+replacement+page[registry.end():],
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"US: portrait cover reused as quiz photograph"):
            country_coverage(self.root,[{"country":"United States"}])

    def test_incomplete_selectable_us_fallback_is_never_silently_skipped(self):
        import re
        original=(self.root/"index.html").read_text(encoding="utf-8")
        registry=re.search(r"(?m)^const TODAY_COUNTRY_PHOTOS=Object\\.freeze\\((.*)\\);$",original)
        self.assertIsNotNone(registry)
        for missing_field in ("asset","url","caption","author","license","place"):
            with self.subTest(missing_field=missing_field):
                covers=json.loads(registry.group(1))
                fallback=next(photo for photo in covers["US"]
                              if photo.get("asset")=="assets/travel/new-york-skyline.jpg")
                fallback.pop(missing_field)
                replacement="const TODAY_COUNTRY_PHOTOS=Object.freeze("+json.dumps(
                    covers,ensure_ascii=False,separators=(",",":"))+");"
                (self.root/"index.html").write_text(
                    original[:registry.start()]+replacement+original[registry.end():],
                    encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"US: selectable cover"):
                    country_coverage(self.root,[{"country":"US"}])

    def test_cover_url_must_match_licensed_postcard_not_only_its_asset(self):
        import re
        path=self.root/"index.html"
        page=path.read_text(encoding="utf-8")
        registry=re.search(r"(?m)^const TODAY_COUNTRY_PHOTOS=Object\\.freeze\\((.*)\\);$",page)
        self.assertIsNotNone(registry)
        covers=json.loads(registry.group(1))
        covers["US"][1]["url"]=covers["US"][0]["url"]
        replacement="const TODAY_COUNTRY_PHOTOS=Object.freeze("+json.dumps(
            covers,ensure_ascii=False,separators=(",",":"))+");"
        path.write_text(page[:registry.start()]+replacement+page[registry.end():],
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"US: selectable cover"):
            country_coverage(self.root,[{"country":"US"}])

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
