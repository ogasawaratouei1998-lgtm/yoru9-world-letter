"""Albania release preserves distinct real photos and rich sourced travel stories."""
import unittest
from pathlib import Path
from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class AlbaniaReleaseTests(unittest.TestCase):
    def test_albania_complete(self):
        row = check_country_content(ROOT)["countries"]["AL"]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(len(row["portraitPhotos"]), 1)
        self.assertEqual(len(row["quiz"]), 2)
        self.assertEqual(len(row["travelStops"]), 3)
        expected = {
            "al-tirana-skanderbeg-cover": ("Diego Delso (delso.photo)", "CC BY-SA 3.0"),
            "al-berat-mangalem-postcard": ("Avi1111 dr. avishai teicher", "CC BY-SA 4.0"),
            "al-butrint-theatre-postcard": ("Images by Gina", "CC BY-SA 2.0"),
        }
        self.assertEqual(set(row["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(stop["photoPage"]) for stop in row["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = row["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
        for quiz in row["quiz"]:
            stop = row["travelStops"][quiz["photoKey"]]
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(s["url"].startswith("https://whc.unesco.org/") for s in stop["historicalSources"]))
            self.assertTrue(any(s["url"].startswith("https://www.anzen.mofa.go.jp/") for s in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "AL"}])), {"AL"})
