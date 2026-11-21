"""Cambodia release: attribution, separate photos, sourced virtual trips."""
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]

class CambodiaCountryReleaseTests(unittest.TestCase):
    def test_cambodia_release_provenance_and_safety(self):
        entry = check_country_content(ROOT)["countries"]["KH"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(country_quiz_problems(entry), ())
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "KH"}])["KH"]["quizRounds"], 2)
        expected = {
            "kh-phnom-penh-palace-cover": ("PsamatheM", "1/17", "04-Preah_Tineang_Phochani_Royal_Palace-nX-1.jpg"),
            "kh-angkor-wat-postcard": ("Christophe95", "7/79", "Angkor_Wat_at_sunrise_4.jpg"),
            "kh-preah-vihear-postcard": ("William Brehm", "e/e9", "Preah-vihear.jpg"),
        }
        for key, (author, path, title) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["photoPage"], "https://commons.wikimedia.org/wiki/File:" + title)
            self.assertEqual(stop["photo"], "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + path + "/" + title + "/500px-" + title)
            self.assertIn(stop["photoAsset"], (ROOT / "service-worker.js").read_text())
        self.assertEqual({q["photoKey"] for q in entry["quiz"]}, set(expected) - {"kh-phnom-penh-palace-cover"})
        self.assertEqual({entry["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in entry["quiz"]}, {"https://whc.unesco.org/en/list/668/", "https://whc.unesco.org/en/list/1224/"})
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
        restricted = entry["travelStops"]["kh-preah-vihear-postcard"]
        self.assertIn("現地への訪問は勧めません", restricted["travelStory"][1])
        self.assertIn("https://www.anzen.mofa.go.jp/info/pchazardspecificinfo_2026T075.html", {s["url"] for s in restricted["historicalSources"]})
