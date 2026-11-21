"""Ireland release: distinct original photographs and sourced mini-trips."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class IrelandCountryReleaseTests(unittest.TestCase):
    def test_ireland_is_ready_with_three_independent_licensed_photos(self):
        doc = check_country_content(ROOT)
        entry = doc["countries"]["IE"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "IE"}])["IE"]["quizRounds"], 2)
        expected = {
            "ie-dublin-hapenny-cover": ("Zairon", "4/41", "Dublin_Ha%27_Penny_Bridge_1.jpg"),
            "ie-newgrange-postcard": ("CooKeeN", "8/81", "Newgrange_entrance.JPG"),
            "ie-skellig-michael-postcard": ("Cathal Curran Photography", "7/75", "Skellig_Michael_Monastery.JPG"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"ie-dublin-hapenny-cover"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(stop["historicalSources"][0]["url"].startswith("https://whc.unesco.org/en/list/"))
