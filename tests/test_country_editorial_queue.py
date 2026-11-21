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
        self.assertEqual(report["approvedCountries"],["AR","DE","FR","GB","IT","JP","US"])
        self.assertEqual(report["pendingCountries"],189)
        self.assertEqual(len(report["prioritizedPending"]),189)
        self.assertEqual(len({row["code"] for row in report["prioritizedPending"]}),189)
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
        for code in ("ES","NZ"):
            self.assertIn("portrait_photo_reused_in_quiz",pending[code]["missing"])
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
