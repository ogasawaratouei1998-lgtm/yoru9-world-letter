"""Slovakia approved only with independent, attributable photographs and sourced trips."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems, _commons_identity
from check_country_experience import country_coverage
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads(r'''[["sk-bratislava-danube-cover","Frettie","CC BY 3.0","https://commons.wikimedia.org/wiki/File:Danube_in_Bratislava_skyline%2C_New_Bridge%2C_Bratislava_Castle_in_Bratislava%2C_Bratislava_I_District.jpg"],["sk-banska-trinity-square-postcard","Juraj Kubica","CC BY-SA 2.0","https://commons.wikimedia.org/wiki/File:Banska_%C5%A0tiavnica%2C_Central_Square.jpg"],["sk-spis-castle-postcard","Michal Klajban","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Spi%C5%A1sk%C3%BD_hrad%2C_okres_Spi%C5%A1sk%C3%A1_Nov%C3%A1_Ves_-_podhrad%C3%AD_%288%29.JPG"]]''')

class SlovakiaReleaseTests(unittest.TestCase):
    def test_complete_country_and_photographs(self):
        e = check_country_content(ROOT)["countries"]["SK"]
        self.assertEqual(e["status"], "approved")
        self.assertEqual(country_quiz_problems(e), ())
        self.assertEqual(len(e["portraitPhotos"]), 1)
        self.assertEqual(len(e["travelStops"]), 3)
        self.assertEqual(len(e["quiz"]), 2)
        self.assertEqual(country_coverage(ROOT, [{"country": "SK"}])["SK"]["quizRounds"], 2)
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
                         {"https://whc.unesco.org/en/list/618/", "https://whc.unesco.org/en/list/620/"})
