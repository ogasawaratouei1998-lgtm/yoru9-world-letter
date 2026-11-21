"""Iceland release: independent photographic originals and documented heritage."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class IcelandCountryReleaseTests(unittest.TestCase):
    def test_iceland_is_ready_with_distinct_attributed_photos(self):
        entry = check_country_content(ROOT)["countries"]["IS"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "IS"}])["IS"]["quizRounds"], 2)
        expected = {
            "is-reykjavik-cover": ("Wa17gs", "3/31", "Reykjavik_from_Hallgrimskikrja.jpg"),
            "is-thingvellir-postcard": ("Olga Ernst", "5/51", "Almannagj%C3%A1%2C_%C3%9Eingvellir_National_Park_%28Iceland%29.jpg"),
            "is-jokulsarlon-postcard": ("Jakub Hałun", "0/0e", "J%C3%B6kuls%C3%A1rl%C3%B3n_glacier_lagoon%2C_Iceland%2C_20240718_1544_2213.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"is-reykjavik-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/1152/", "https://whc.unesco.org/en/list/1604/"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
