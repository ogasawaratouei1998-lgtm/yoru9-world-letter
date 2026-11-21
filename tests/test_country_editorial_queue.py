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
        self.assertEqual(report["approvedCountries"],["DE","IT","US"])
        self.assertEqual(report["pendingCountries"],193)
        self.assertEqual(len(report["prioritizedPending"]),193)
        self.assertEqual(len({row["code"] for row in report["prioritizedPending"]}),193)
        self.assertTrue(any(row["code"]=="NG" and
                            "attributed_country_portrait_photo" in row["missing"]
                            for row in report["prioritizedPending"]))
        self.assertTrue(all(row["requiredRemaining"]>=0
                            for row in report["prioritizedPending"]))

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
