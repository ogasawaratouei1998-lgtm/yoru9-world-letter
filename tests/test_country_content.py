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
                          if row["status"]=="approved"},{"IT","DE","US","FR","AR","JP","GB","ES"})
        self.assertGreaterEqual(len(doc["travelOrder"]),40)
        self.assertTrue(doc["countries"]["IT"]["portrait"]["body"])
        self.assertEqual(doc["countries"]["NG"]["status"],"pending")

    def test_spain_source_review_is_prepared_but_approval_is_separate(self):
        doc=load_country_content(ROOT)
        spain=doc["countries"]["ES"]
        self.assertEqual(spain["status"],"approved")
        self.assertTrue(spain["portrait"]["sourceUrl"].startswith(
            "https://www.spain.info/"))
        self.assertEqual(len(spain["quiz"]),2)
        quiz_keys={item["photoKey"] for item in spain["quiz"]}
        self.assertEqual(len(quiz_keys),2)
        covers={item["asset"] for item in spain["portraitPhotos"]
                if not item.get("avoidCover") and not item.get("remoteOnly")}
        assets={spain["travelStops"][key]["photoAsset"] for key in quiz_keys}
        self.assertTrue(covers.isdisjoint(assets))
        self.assertTrue(all(spain["travelStops"][key]["quizOnly"]
                            for key in quiz_keys))
        postcard=spain["travelStops"]["spain-park-guell-postcard"]
        self.assertEqual(len(postcard["travelStory"]),2)
        self.assertTrue(all(len(p)>=110 for p in postcard["travelStory"]))
        self.assertTrue(postcard["historicalSources"])
        self.assertEqual(len(doc["travelOrder"]),len(set(doc["travelOrder"])))

    def test_new_zealand_editorial_content_is_prepared_but_not_auto_approved(self):
        doc=load_country_content(ROOT)
        nz=doc["countries"]["NZ"]
        self.assertEqual(nz["status"],"pending")
        self.assertTrue(nz["portrait"]["sourceUrl"].startswith(
            "https://www.newzealand.com/"))
        self.assertEqual(len(nz["quiz"]),2)
        quiz_keys={q["photoKey"] for q in nz["quiz"]}
        self.assertEqual(len(quiz_keys),2)
        covers={p["asset"] for p in nz["portraitPhotos"]
                if not p.get("avoidCover") and not p.get("remoteOnly")}
        answers={nz["travelStops"][key]["photoAsset"] for key in quiz_keys}
        self.assertTrue(covers.isdisjoint(answers))
        self.assertTrue(all(nz["travelStops"][key].get("quizOnly") for key in quiz_keys))
        for key in ("nz-milford-sound-postcard","nz-tekapo-church-postcard"):
            with self.subTest(destination=key):
                stop=nz["travelStops"][key]
                self.assertEqual(len(stop["travelStory"]),2)
                self.assertTrue(all(len(p)>=110 for p in stop["travelStory"]))
                self.assertTrue(stop.get("historicalSources"))
        self.assertEqual(len(doc["travelOrder"]),len(set(doc["travelOrder"])))

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

    def test_sync_preserves_readiness_of_published_seven(self):
        sync_country_content(self.root)
        txt=(self.root/"world-passport.js").read_text(encoding="utf-8")
        section=txt.split(" US:[",1)[1].split("\n});",1)[0]
        self.assertEqual(section.count("question:"),2,section[:1000])
        result=country_coverage(self.root,[{"id":"a","country":"イタリア"},
                                          {"id":"b","country":"ドイツ"},
                                          {"id":"c","country":"アメリカ合衆国"},
                                          {"id":"d","country":"フランス"},
                                          {"id":"e","country":"アルゼンチン"},
                                          {"id":"f","country":"日本"},
                                          {"id":"g","country":"イギリス"}])
        self.assertEqual(set(result),{"IT","DE","US","FR","AR","JP","GB"})

    def test_country_photo_cannot_be_relabelled_to_another_country(self):
        path=self.root/"country-content.json"
        doc=json.loads(path.read_text(encoding="utf-8"))
        german=doc["countries"]["DE"]["travelStops"]["germany-cologne-cathedral-postcard"]
        german["photoAsset"]="assets/travel/italy-pisa-tower.jpg"
        path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"photograph reused with conflicting"):
            load_country_content(self.root)

    def test_country_postcard_must_match_its_geographic_record(self):
        path=self.root/"country-content.json"
        doc=json.loads(path.read_text(encoding="utf-8"))
        doc["countries"]["FR"]["travelStops"]["fr-eiffel-postcard"]["country"]="イタリア"
        path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"wrong-country postcard"):
            load_country_content(self.root)

    def test_same_country_same_wikimedia_photo_can_have_two_postcards(self):
        # Historic named incidents and evergreen UK cards genuinely share
        # Edinburgh Castle imagery with identical rights and photographer.
        doc=load_country_content(ROOT)
        one=doc["countries"]["GB"]["travelStops"]["flight-wrong-country"]
        two=doc["countries"]["GB"]["travelStops"]["uk-country-postcard"]
        self.assertEqual(one["photoAsset"],two["photoAsset"])
        self.assertEqual(one["photoPage"],two["photoPage"])
        self.assertEqual(one["author"],two["author"])

    def test_pending_country_cannot_be_promoted_without_photos(self):
        file=self.root/"country-content.json"
        data=json.loads(file.read_text(encoding="utf-8"))
        data["countries"]["NG"]["status"]="approved"
        file.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"NG: approved portrait requires named cultural source|NG: approval"):
            load_country_content(self.root)

    def test_approved_postcards_need_historical_sources_separate_from_photo_credits(self):
        doc=load_country_content(ROOT)
        self.assertEqual(sum(bool(stop.get("historicalSources"))
                             for code in ("IT","DE","US","FR","AR","JP","GB")
                             for stop in doc["countries"][code]["travelStops"].values()
                             if stop.get("travelStory")),26)
        file=self.root/"country-content.json"
        dataset=json.loads(file.read_text(encoding="utf-8"))
        dataset["countries"]["US"]["travelStops"]["us-newyork-postcard"].pop("historicalSources")
        file.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"unsourced history/culture"):
            load_country_content(self.root)

    def test_an_approved_country_cannot_repeat_its_quiz_answer_as_lead_cover(self):
        # A content editor can update JSON and the exported JS consistently,
        # but country-level visual readiness must still veto the release.
        content=self.root/"country-content.json"
        data=json.loads(content.read_text(encoding="utf-8"))
        japan=data["countries"]["JP"]
        japanese_fujisan=next(p for p in japan["portraitPhotos"]
                             if p.get("asset")=="assets/travel/fuji-cherry-blossom.jpg")
        japanese_fujisan.pop("avoidCover",None)
        content.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"JP: approved content fails reader readiness"):
            sync_country_content(self.root)

    def test_approved_fallback_must_not_reuse_a_quiz_photo(self):
        # The first Argentine cover is independent. A broken first image
        # must not expose the quiz answer via the second cover candidate.
        path=self.root/"country-content.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        argentina=data["countries"]["AR"]
        self.assertNotEqual(argentina["portraitPhotos"][0]["asset"],
                            argentina["travelStops"][argentina["quiz"][0]["photoKey"]]["photoAsset"])
        fallback=next(photo for photo in argentina["portraitPhotos"]
                      if photo.get("asset")=="assets/travel/iguazu-argentina.jpg")
        self.assertTrue(fallback.pop("avoidCover"))
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,
                                    "AR: approved content fails reader readiness: AR: portrait cover reused"):
            sync_country_content(self.root)

    def test_newly_approved_countries_keep_distinct_covers_and_quiz_photos(self):
        from check_country_experience import country_coverage
        rows=country_coverage(ROOT,[{"country":"日本"},{"country":"イギリス"}])
        self.assertEqual(set(rows),{"JP","GB"})
        self.assertEqual(rows["JP"]["cover"],"assets/travel/kyoto-kinkakuji.jpg")
        self.assertEqual(rows["GB"]["cover"],"assets/travel/wales-cardiff-castle.jpg")
        self.assertTrue(all(len(row["quizPhotoKeys"])==2 for row in rows.values()))

    def test_approved_country_portrait_requires_independent_cultural_source(self):
        file=self.root/"country-content.json"
        dataset=json.loads(file.read_text(encoding="utf-8"))
        dataset["countries"]["JP"]["portrait"].pop("sourceUrl")
        file.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"portrait source URL missing"):
            load_country_content(self.root)

    def test_photo_credit_cannot_masquerade_as_history(self):
        file=self.root/"country-content.json"
        dataset=json.loads(file.read_text(encoding="utf-8"))
        dataset["countries"]["IT"]["travelStops"]["italy-pisa-tower-postcard"]["historicalSources"]=[
            {"name":"写真ページ","url":"https://commons.wikimedia.org/wiki/File:example.jpg",
             "checkedOn":"2026-11-21"}]
        file.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"photo license cannot replace"):
            load_country_content(self.root)

    def test_reader_entrypoint_and_external_stylesheet_are_published_together(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        builder=(ROOT/"build_site.py").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn('href="#issueGallery"',page)
        self.assertIn('href="./assets/reading-focus.css"',page)
        self.assertIn("'assets/reading-focus.css'",builder)
        self.assertIn("'assets/reading-focus.css'",worker)

    def test_unreviewed_country_no_fabricated_photographs(self):
        doc=load_country_content(self.root)
        country=doc["countries"]["NG"]
        self.assertFalse(country["portraitPhotos"])
        self.assertFalse(country["travelStops"])


if __name__=="__main__":
    unittest.main()
