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
                          if row["status"]=="approved"},{"IT","DE","US","FR","AR","JP","GB","ES","NZ","KR","BR"})
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

    def test_new_zealand_editorial_content_is_ready_with_separate_approval(self):
        doc=load_country_content(ROOT)
        nz=doc["countries"]["NZ"]
        self.assertEqual(nz["status"],"approved")
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

    def test_korea_source_review_is_complete_and_explicitly_approved(self):
        doc=load_country_content(ROOT)
        korea=doc["countries"]["KR"]
        self.assertEqual(korea["status"],"approved")
        self.assertEqual(len(korea["quiz"]),2)
        covers={p["asset"] for p in korea["portraitPhotos"]
                if not p.get("avoidCover") and not p.get("remoteOnly")}
        keys={q["photoKey"] for q in korea["quiz"]}
        self.assertEqual(len(keys),2)
        images={korea["travelStops"][k]["photoAsset"] for k in keys}
        self.assertTrue(covers.isdisjoint(images))
        self.assertEqual(len(images),2)
        self.assertTrue(all(korea["travelStops"][k].get("quizOnly")
                            for k in keys))
        self.assertEqual(korea["portraitPhotos"][0]["author"],"螺钉")
        self.assertEqual(korea["travelStops"]["korea-bulguksa-postcard"]["license"],
                         "CC BY 2.0")
        self.assertTrue(korea["portrait"]["sourceUrl"].startswith("https://english.visitkorea.or.kr/"))
        for key,stop in korea["travelStops"].items():
            if not stop.get("travelStory"):
                continue
            with self.subTest(destination=key):
                self.assertEqual(len(stop["travelStory"]),2)
                self.assertTrue(all(110<=len(t)<=360 for t in stop["travelStory"]))
                self.assertTrue(stop.get("historicalSources"))

    def test_korea_approval_is_not_inferred_from_complete_assets(self):
        # A ready-looking Korean portrait without the explicit approval stays
        # blocked. A second opt-in on this isolated fixture enables it.
        path=self.root/"country-content.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["countries"]["KR"]["status"],"approved")
        data["countries"]["KR"]["status"]="pending"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        sync_country_content(self.root)
        with self.assertRaisesRegex(ValueError,"KR: country content awaiting editorial approval"):
            country_coverage(self.root,[{"country":"韓国"}])
        data["countries"]["KR"]["status"]="approved"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        sync_country_content(self.root)
        result=country_coverage(self.root,[{"country":"韓国"}])
        self.assertEqual(set(result),{"KR"})
        self.assertEqual(result["KR"]["quizRounds"],2)
        self.assertEqual(result["KR"]["cover"],"assets/travel/seoul-gyeongbokgung.jpg")
        self.assertEqual(result["KR"]["postcard"],"assets/travel/korea-bulguksa-stairs.jpg")

    def test_brazil_has_independent_brazil_side_photo_and_two_distinct_quizzes(self):
        data=load_country_content(ROOT)
        brazil=data["countries"]["BR"]
        self.assertEqual(brazil["status"],"approved")
        self.assertTrue(brazil["portrait"]["sourceUrl"].startswith("https://www.visitbrasil.com/"))
        self.assertEqual(len(brazil["quiz"]),2)
        keys=[item["photoKey"] for item in brazil["quiz"]]
        self.assertEqual(len(set(keys)),2)
        self.assertIn("brazil-iguacu-brazil-side-quiz-image",keys)
        self.assertEqual(brazil["travelStops"]["brazil-iguacu-brazil-side-quiz-image"]["author"],
                         "MurielDamiana")
        self.assertTrue(all(brazil["travelStops"][key]["quizOnly"] for key in keys))
        cover=brazil["portraitPhotos"][0]
        self.assertEqual(cover["asset"],"assets/travel/brazil-rio-christ-cover.jpg")
        photo_assets=[brazil["travelStops"][key]["photoAsset"] for key in keys]
        postcard=brazil["travelStops"]["brazil-country-postcard"]
        self.assertEqual(postcard["author"],"Flaviohmg")
        self.assertIn("Iguaçu_Falls",postcard["photoPage"])
        self.assertNotEqual(postcard["photoAsset"],
                            brazil["travelStops"]["guaira-degavar-road-marking-2026"]["photoAsset"])
        self.assertEqual(len(set([cover["asset"],postcard["photoAsset"]]+photo_assets)),4)
        self.assertEqual(brazil["travelStops"]["brazil-museum-tomorrow-postcard"]["author"],
                         "Leonardo Chavez")
        for stop in brazil["travelStops"].values():
            if not stop.get("travelStory"):
                continue
            self.assertEqual(len(stop["travelStory"]),2)
            self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
            self.assertTrue(stop.get("historicalSources"))

    def test_brazil_publication_requires_explicit_editorial_approval(self):
        path=self.root/"country-content.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["countries"]["BR"]["status"],"approved")
        data["countries"]["BR"]["status"]="pending"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        sync_country_content(self.root)
        with self.assertRaisesRegex(ValueError,"BR: country content awaiting editorial approval"):
            country_coverage(self.root,[{"country":"ブラジル"}])
        data["countries"]["BR"]["status"]="approved"
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        sync_country_content(self.root)
        result=country_coverage(self.root,[{"country":"ブラジル"}])
        self.assertEqual(set(result),{"BR"})
        self.assertEqual(result["BR"]["quizRounds"],2)
        self.assertEqual(result["BR"]["cover"],"assets/travel/brazil-rio-christ-cover.jpg")
        self.assertEqual(result["BR"]["postcard"],
                         "assets/travel/brazil-iguacu-brazil-side-postcard.jpg")

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
