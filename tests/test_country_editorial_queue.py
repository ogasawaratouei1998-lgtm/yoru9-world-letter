"""A geographic index is not a content-approval whitelist."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from country_editorial_queue import country_editorial_queue

ROOT=Path(__file__).resolve().parents[1]


class CountryEditorialQueueTest(unittest.TestCase):
    def test_queue_tracks_all_country_codes_without_approving_candidates(self):
        report=country_editorial_queue(ROOT)
        self.assertEqual(report["reportingLocations"],196)
        self.assertEqual(report["approvedCountries"],["AG","AR","AU","BR","CA","DE","ES","FR","GB","GR","IN","IT","JP","KR","MX","NL","NZ","SG","US"])
        self.assertEqual(report["pendingCountries"],177)
        self.assertEqual(len(report["prioritizedPending"]),177)
        self.assertEqual(len({row["code"] for row in report["prioritizedPending"]}),177)
        self.assertTrue(any(row["code"]=="NG" and
                            "attributed_country_portrait_photo" in row["missing"]
                            for row in report["prioritizedPending"]))
        self.assertTrue(all(row["requiredRemaining"]>=0
                            for row in report["prioritizedPending"]))

    def test_cover_licensing_is_inherited_from_exact_postcard_provenance(self):
        report=country_editorial_queue(ROOT)
        pending={x["code"]:x for x in report["prioritizedPending"]}
        # All three source records are real, attributed local photographs.
        # Their index-level cover entries predating sourcePage aren't missing.
        # A reused portrait/quiz image is a different and real release defect.
        self.assertNotIn("NZ",pending)
        self.assertIn("NZ",report["approvedCountries"])
        self.assertNotIn("ES",pending)
        self.assertIn("ES",report["approvedCountries"])
        for code in ("FR","AR","JP","GB"):
            self.assertIn(code,report["approvedCountries"])

    def test_queue_flags_second_fallback_cover_when_it_reuses_a_quiz_image(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            doc=json.loads(path.read_text(encoding="utf-8"))
            argentina=doc["countries"]["AR"]
            argentina["status"]="pending"
            fallback=next(photo for photo in argentina["portraitPhotos"]
                          if photo.get("asset")=="assets/travel/iguazu-argentina.jpg")
            fallback.pop("avoidCover")
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            queue=country_editorial_queue(root)
            row=next(item for item in queue["prioritizedPending"] if item["code"]=="AR")
            self.assertIn("portrait_photo_reused_in_quiz",row["missing"])

    def test_queue_flags_broken_second_cover_even_with_valid_first(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            dataset=json.loads(path.read_text(encoding="utf-8"))
            argentina=dataset["countries"]["AR"]
            argentina["status"]="pending"
            fallback=next(photo for photo in argentina["portraitPhotos"]
                          if photo.get("asset")=="assets/travel/buenos-aires-casa-rosada.jpg")
            fallback.pop("caption")
            path.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
            report=country_editorial_queue(root)
            row=next(item for item in report["prioritizedPending"] if item["code"]=="AR")
            self.assertIn("invalid_selectable_portrait_photo",row["missing"])
            self.assertNotIn("attributed_country_portrait_photo",row["missing"])

    def test_korean_content_is_approved_only_after_review(self):
        report=country_editorial_queue(ROOT)
        self.assertIn("KR",report["approvedCountries"])
        self.assertNotIn("KR",{row["code"] for row in report["prioritizedPending"]})

    def test_two_short_tourism_paragraphs_still_block_a_pending_country(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            doc=json.loads(path.read_text(encoding="utf-8"))
            doc["countries"]["KR"]["status"]="pending"
            for stop in doc["countries"]["KR"]["travelStops"].values():
                if stop.get("travelStory"):
                    stop["travelStory"]=["短すぎる説明。","歴史的な説明も短すぎます。"]
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            queue=country_editorial_queue(root)
            korea=next(row for row in queue["prioritizedPending"]
                       if row["code"]=="KR")
            self.assertIn("two_paragraph_microtravel",korea["missing"])

    def test_brazil_is_explicitly_approved_after_photo_and_source_review(self):
        report=country_editorial_queue(ROOT)
        self.assertIn("BR",report["approvedCountries"])
        self.assertNotIn("BR",{row["code"] for row in report["prioritizedPending"]})

    def test_brazil_cover_source_drift_is_flagged_even_with_usable_quizzes(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for filename in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/filename,root/filename)
            path=root/"country-content.json"
            dataset=json.loads(path.read_text(encoding="utf-8"))
            dataset["countries"]["BR"]["status"]="pending"
            dataset["countries"]["BR"]["portraitPhotos"][0]["author"]="Incorrect photographer"
            path.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
            report=country_editorial_queue(root)
            brazil=next(row for row in report["prioritizedPending"] if row["code"]=="BR")
            self.assertIn("invalid_selectable_portrait_photo",brazil["missing"])
            self.assertIn("attributed_country_portrait_photo",brazil["missing"])

    def test_antigua_was_explicitly_approved_after_source_review(self):
        result=country_editorial_queue(ROOT)
        self.assertIn("AG",result["approvedCountries"])
        self.assertNotIn("AG",{row["code"] for row in result["prioritizedPending"]})

    def test_antigua_quiz_photo_reused_as_cover_is_detected(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            dataset=json.loads(path.read_text(encoding="utf-8"))
            antigua=dataset["countries"]["AG"]
            antigua["status"]="pending"
            cover=antigua["portraitPhotos"][0]
            cover["asset"]=antigua["travelStops"]["antigua-bettys-hope-quiz-image"]["photoAsset"]
            path.write_text(json.dumps(dataset,ensure_ascii=False),encoding="utf-8")
            result=country_editorial_queue(root)
            row=next(item for item in result["prioritizedPending"] if item["code"]=="AG")
            self.assertIn("invalid_selectable_portrait_photo",row["missing"])
            self.assertIn("portrait_photo_reused_in_quiz",row["missing"])

    def test_pending_country_queue_explains_broken_choices_and_answers(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            doc=json.loads(path.read_text(encoding="utf-8"))
            doc["countries"]["IT"]["status"]="pending"
            doc["countries"]["IT"]["quiz"][0]["answer"]=99
            doc["countries"]["IT"]["quiz"][1]["options"]=["same","same","same"]
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            queue=country_editorial_queue(root)
            row=next(row for row in queue["prioritizedPending"] if row["code"]=="IT")
            self.assertIn("complete_three_choice_quiz",row["missing"])
            self.assertNotIn("two_distinct_licensed_photo_quizzes",row["missing"])
            self.assertNotIn("IT",queue["approvedCountries"])

    def test_pending_country_queue_separately_flags_duplicate_answer_photo(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            doc=json.loads(path.read_text(encoding="utf-8"))
            italy=doc["countries"]["IT"]
            italy["status"]="pending"
            italy["quiz"][1]["photoKey"]=italy["quiz"][0]["photoKey"]
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            row=next(row for row in country_editorial_queue(root)["prioritizedPending"]
                     if row["code"]=="IT")
            self.assertIn("two_distinct_licensed_photo_quizzes",row["missing"])
            self.assertNotIn("complete_three_choice_quiz",row["missing"])

    def test_history_source_on_unrelated_cover_does_not_certify_the_trip(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            path=root/"country-content.json"
            doc=json.loads(path.read_text(encoding="utf-8"))
            italy=doc["countries"]["IT"]
            italy["status"]="pending"
            for stop in italy["travelStops"].values():
                stop.pop("historicalSources",None)
                if stop.get("coverOnly"):
                    stop["historicalSources"]=[{
                        "name":"Museum","url":"https://example.org/history",
                        "checkedOn":"2026-11-21"}]
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            report=country_editorial_queue(root)
            row=next(item for item in report["prioritizedPending"] if item["code"]=="IT")
            self.assertNotIn("two_paragraph_microtravel",row["missing"])
            self.assertIn("independent_travel_history_culture_source",row["missing"])

    def test_missing_heritage_source_remains_an_actionable_review_item(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for name in ("country-content.json","country-catalog.json"):
                shutil.copy2(ROOT/name,root/name)
            doc=json.loads((root/"country-content.json").read_text(encoding="utf-8"))
            doc["countries"]["IT"]["status"]="pending"
            doc["countries"]["IT"]["portrait"].pop("sourceUrl",None)
            for item in doc["countries"]["IT"]["travelStops"].values():
                item.pop("historicalSources",None)
            (root/"country-content.json").write_text(
                json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            report=country_editorial_queue(root)
            italy=next(x for x in report["prioritizedPending"] if x["code"]=="IT")
            self.assertIn("portrait_history_culture_source",italy["missing"])
            self.assertIn("independent_travel_history_culture_source",italy["missing"])
            self.assertNotIn("IT",report["approvedCountries"])


if __name__=="__main__":
    unittest.main()
