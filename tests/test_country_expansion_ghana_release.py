"""Ghana release checks distinct photographs, cultural sensitivity and attribution."""
import unittest
from pathlib import Path
from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class GhanaReleaseTests(unittest.TestCase):
    def test_ghana_complete(self):
        row = check_country_content(ROOT)["countries"]["GH"]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(len(row["portraitPhotos"]), 1)
        self.assertEqual(len(row["quiz"]), 2)
        self.assertIn("危険レベル1・2", row["portrait"]["body"])
        expected = {
            "gh-aburi-mampong-cover": ("Penwills", "CC BY-SA 4.0"),
            "gh-besease-shrine-postcard": ("Joy Agyepong", "CC BY-SA 4.0"),
            "gh-cape-coast-castle-postcard": ("Rjruiziii", "CC BY-SA 3.0"),
        }
        self.assertEqual(set(row["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(s["photoPage"]) for s in row["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = row["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
        for quiz in row["quiz"]:
            stop = row["travelStops"][quiz["photoKey"]]
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(s["url"].startswith("https://www.anzen.mofa.go.jp/") for s in stop["historicalSources"]))
            self.assertTrue(any(s["url"].startswith("https://whc.unesco.org/") for s in stop["historicalSources"]))
        self.assertIn("奴隷貿易", row["quiz"][1]["fact"])
        self.assertEqual(set(country_coverage(ROOT, [{"country": "GH"}])), {"GH"})
