"""Tanzania release: independent attributed photos and documented heritage."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class TanzaniaCountryReleaseTests(unittest.TestCase):
    def test_tanzania_release_provenance_and_readiness(self):
        entry = check_country_content(ROOT)["countries"]["TZ"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "TZ"}])["TZ"]["quizRounds"], 2)
        expected = {
            "tz-dar-es-salaam-harbour-cover": ("Kipala", "5/5e", "Dar_es_Salaam_Harbour.jpg"),
            "tz-stone-town-postcard": ("Mo son", "f/f1", "Stone_town_street.jpg"),
            "tz-kilimanjaro-postcard": ("Ganeshpednekar", "5/56", "Mount_Kilimanjaro_from_Moshi.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], "CC BY-SA 4.0")
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"tz-dar-es-salaam-harbour-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/173/", "https://whc.unesco.org/en/list/403/"})
        for q in entry["quiz"]:
            self.assertEqual(len(entry["travelStops"][q["photoKey"]]["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in entry["travelStops"][q["photoKey"]]["travelStory"]))
        self.assertIn("奴隷交易", entry["travelStops"]["tz-stone-town-postcard"]["travelStory"][1])
        self.assertIn("国立公園の外", entry["travelStops"]["tz-kilimanjaro-postcard"]["travelStory"][0])
        self.assertIn("安易な登山は勧めません", entry["travelStops"]["tz-kilimanjaro-postcard"]["travelStory"][1])
