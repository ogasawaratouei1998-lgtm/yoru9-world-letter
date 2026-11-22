"""Guatemala release uses three independently reviewed Commons originals."""
import unittest
from pathlib import Path

from country_content import check_country_content
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class GuatemalaReleaseTests(unittest.TestCase):
    def test_guatemala_has_three_distinct_reviewed_photos_and_complete_quizzes(self):
        doc = check_country_content(ROOT)
        gt = doc["countries"]["GT"]
        self.assertEqual(gt["status"], "approved")
        self.assertEqual(len(gt["portraitPhotos"]), 1)
        self.assertEqual(len(gt["quiz"]), 2)
        self.assertEqual(set(gt["travelStops"]), {
            "gt-atitlan-cover", "gt-tikal-plaza-postcard", "gt-antigua-cathedral-postcard",
        })
        expected = {
            "gt-atitlan-cover": ("1_lake_atitlan_panorama_2009.jpg", "chensiyuan", "CC BY-SA 4.0"),
            "gt-tikal-plaza-postcard": ("Tikal-Plaza-Mayor-Panorama.jpg", "Bjørn Christian Tørrissen", "CC BY-SA 3.0"),
            "gt-antigua-cathedral-postcard": ("Ruins_of_an_Old_Cathedral_-_Antigua_Guatemala_2000.jpg", "Alex Guerrero", "CC BY-SA 2.0"),
        }
        for key, (filename, author, license_name) in expected.items():
            stop = gt["travelStops"][key]
            self.assertTrue(stop["photoPage"].endswith("File:" + filename))
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
            self.assertIn("代表地点", stop["note"])
        for quiz in gt["quiz"]:
            stop = gt["travelStops"][quiz["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(s["url"].startswith("https://www.anzen.mofa.go.jp/") for s in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "GT"}])), {"GT"})
