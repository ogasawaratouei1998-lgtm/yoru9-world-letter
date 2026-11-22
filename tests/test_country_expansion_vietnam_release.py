"""Vietnam release: independently reviewed photos and UNESCO-sourced virtual trips."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems, _commons_identity
from check_country_experience import country_coverage
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads(r'''[["vn-hoian-street-cover","Photo by Adam Jones adamjones.freeservers.com","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Street_Scene_-_Hoi_An_-_Vietnam.JPG"],["vn-hoian-thubon-postcard","© Steffen Schmitz (Carschten) / Wikimedia Commons","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:H%E1%BB%99i_An%2C_Ancient_Town%2C_2020-01_CN-01.jpg"],["vn-halong-bay-postcard","© Vyacheslav Argenberg","CC BY 4.0","https://commons.wikimedia.org/wiki/File:Sailing_in_Ha_Long_Bay%2C_Vietnam.jpg"]]''')

class VietnamReleaseTests(unittest.TestCase):
    def test_complete_country_and_photos(self):
        e = check_country_content(ROOT)["countries"]["VN"]
        self.assertEqual(e["status"], "approved")
        self.assertEqual(country_quiz_problems(e), ())
        self.assertEqual(len(e["portraitPhotos"]), 1)
        self.assertEqual(len(e["travelStops"]), 3)
        self.assertEqual(len(e["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "VN"}])["VN"]["quizRounds"], 2)
        originals = set()
        sw = (ROOT / "service-worker.js").read_text()
        for key, author, license_name, page in EXPECTED:
            s = e["travelStops"][key]
            self.assertEqual(s["author"], author)
            self.assertEqual(s["license"], license_name)
            self.assertEqual(s["photoPage"], page)
            self.assertEqual(_commons_identity(s["photo"]), _commons_identity(page))
            originals.add(_commons_identity(page))
            self.assertIn(s["photoAsset"], sw)
        self.assertEqual(len(originals), 3)
        self.assertEqual({q["photoKey"] for q in e["quiz"]}, {p[0] for p in EXPECTED[1:]})
        for q in e["quiz"]:
            s = e["travelStops"][q["photoKey"]]
            self.assertEqual(len(s["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in s["travelStory"]))
        self.assertEqual({e["travelStops"][q["photoKey"]]["historicalSources"][0]["url"] for q in e["quiz"]},
                         {"https://whc.unesco.org/en/list/948/", "https://whc.unesco.org/en/list/672/"})
