"""Sri Lanka release: independent photographed landmarks and sourced heritage."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class SriLankaCountryReleaseTests(unittest.TestCase):
    def test_sri_lanka_release_provenance_and_readiness(self):
        entry = check_country_content(ROOT)["countries"]["LK"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "LK"}])["LK"]["quizRounds"], 2)
        expected = {
            "lk-colombo-beira-cover": ("Kapila Perera", "9/9f", "Skyline_of_colombo_beira_lake.jpg"),
            "lk-sigiriya-postcard": ("Jolle", "1/17", "Sigiriya_Rock.jpg"),
            "lk-kandy-tooth-postcard": ("Thimuth", "6/6f", "Kandy_Sri_Lanka_Temple_of_the_tooth.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], "CC BY-SA 4.0")
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"lk-colombo-beira-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/202/", "https://whc.unesco.org/en/list/450/"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
