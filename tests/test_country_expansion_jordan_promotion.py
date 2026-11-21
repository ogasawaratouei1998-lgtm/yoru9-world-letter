"""Jordan release: independently attributed photography and virtual-only heritage trips."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class JordanCountryReleaseTests(unittest.TestCase):
    def test_jordan_release_provenance_and_safety(self):
        entry = check_country_content(ROOT)["countries"]["JO"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "JO"}])["JO"]["quizRounds"], 2)
        self.assertIn("危険レベル2", entry["portrait"]["body"])
        expected = {
            "jo-amman-citadel-cover": ("Garikoitz Knörr", "7/74", "Amman%2C_view_from_the_Citadel.JPG"),
            "jo-petra-treasury-postcard": ("Davidchocron", "5/56", "Petra%2C_Jordan_-The_Treasury.JPG"),
            "jo-wadi-rum-sunset-postcard": ("Trldp", "4/4c", "Sunset_in_Wadi_Rum.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], "CC BY-SA 4.0")
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"jo-amman-citadel-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/326/", "https://whc.unesco.org/en/list/1377/"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertIn("危険レベル2", stop["travelStory"][1])
            self.assertIn("勧めません", stop["travelStory"][1])
            self.assertIn("https://www.anzen.mofa.go.jp/m/mbhazardinfo1_054.html", {s["url"] for s in stop["historicalSources"]})
