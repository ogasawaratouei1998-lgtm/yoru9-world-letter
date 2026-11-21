"""Nepal release: independent attributed photographs and sourced virtual trips."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class NepalCountryReleaseTests(unittest.TestCase):
    def test_nepal_release_provenance_and_readiness(self):
        entry = check_country_content(ROOT)["countries"]["NP"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "NP"}])["NP"]["quizRounds"], 2)
        expected = {
            "np-boudhanath-cover": ("Prashantghimire256", "0/01", "Bouddhanath_Stupa_Kathmandu.jpg"),
            "np-patan-durbar-postcard": ("Sworna Maharjan", "d/d4", "Patan_Darbar_Square%2C_Nepal.jpg"),
            "np-everest-postcard": ("Matheus Hobold Sovernigo", "2/2e", "Mount_Everest_from_Kala_Patthar.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], "CC BY-SA 4.0")
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"np-boudhanath-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/121/", "https://whc.unesco.org/en/list/120/"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
        self.assertIn("安易な訪問は勧めません", entry["travelStops"]["np-everest-postcard"]["travelStory"][1])
