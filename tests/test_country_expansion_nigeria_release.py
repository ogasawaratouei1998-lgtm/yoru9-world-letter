"""Nigeria release checks distinguish cultural content from travel advice."""
import unittest
from pathlib import Path
from country_content import check_country_content
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class NigeriaReleaseTests(unittest.TestCase):
    def test_nigeria_complete_and_safety_notices_preserved(self):
        row = check_country_content(ROOT)["countries"]["NG"]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(len(row["portraitPhotos"]), 1)
        self.assertEqual(len(row["quiz"]), 2)
        self.assertIn("レベル4", row["portrait"]["body"])
        expected = {
            "ng-lagos-victoria-cover": ("Ayorinde Ogundele", "CC BY-SA 4.0"),
            "ng-osun-grove-postcard": ("(Jesu-loba)", "CC BY-SA 4.0"),
            "ng-sukur-postcard": ("StefanCramer", "CC BY 3.0"),
        }
        self.assertEqual(set(row["travelStops"]), set(expected))
        self.assertEqual(len({s["photoPage"] for s in row["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = row["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
        for quiz in row["quiz"]:
            stop = row["travelStops"][quiz["photoKey"]]
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(s["url"].startswith("https://www.anzen.mofa.go.jp/") for s in stop["historicalSources"]))
        self.assertIn("危険レベル4", row["travelStops"]["ng-sukur-postcard"]["note"])
        self.assertEqual(set(country_coverage(ROOT, [{"country": "NG"}])), {"NG"})
