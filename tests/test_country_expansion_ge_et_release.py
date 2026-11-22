"""Georgia and Ethiopia: licensed independent photos and safety-aware cultural virtual trips."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems, _commons_identity
from check_country_experience import country_coverage
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads(r'''{"GE":[["ge-mestia-towers-cover","Arian Zwegers from Brussels, Belgium","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Near_Mestia%2C_Svan_towers_%2835252565354%29.jpg"],["ge-mtskheta-cathedral-postcard","Moahim","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:The_Svetitskhoveli_Cathedral_-_01.jpg"],["ge-ushguli-tower-postcard","Arian Zwegers from Brussels, Belgium","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Ushguli%2C_Tamar%27s_Tower_%2835282897653%29.jpg"]],"ET":[["et-lalibela-church-cover","Tmanahan344","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:The_Bete_Giyorgis.jpg"],["et-lalibela-landscape-postcard","A. Davey from Where I Live Now: Pacific Northwest","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Landscape_with_Church_of_Bet_Giyorgis_%283282501914%29.jpg"],["et-aksum-stelae-postcard","A. Davey from Where I Live Now: Pacific Northwest","CC BY 2.0","https://commons.wikimedia.org/wiki/File:The_North_Stelae_Park%2C_Axum%2C_Ethiopia_%282812686646%29.jpg"]]}''')

class GeorgiaEthiopiaReleaseTests(unittest.TestCase):
    def test_complete_country_and_safety(self):
        doc = check_country_content(ROOT)["countries"]
        sw = (ROOT / "service-worker.js").read_text()
        for code, photos in EXPECTED.items():
            with self.subTest(code=code):
                e = doc[code]
                self.assertEqual(e["status"], "approved")
                self.assertEqual(country_quiz_problems(e), ())
                self.assertEqual(len(e["portraitPhotos"]), 1)
                self.assertEqual(len(e["quiz"]), 2)
                self.assertEqual(len(e["travelStops"]), 3)
                self.assertEqual(country_coverage(ROOT, [{"country": code}])[code]["quizRounds"], 2)
                self.assertIn("危険レベル", e["portrait"]["facts"][-1])
                originals = set()
                for key, author, license_name, page in photos:
                    s = e["travelStops"][key]
                    self.assertEqual(s["author"], author)
                    self.assertEqual(s["license"], license_name)
                    self.assertEqual(s["photoPage"], page)
                    self.assertEqual(_commons_identity(s["photo"]), _commons_identity(page))
                    originals.add(_commons_identity(page))
                    self.assertIn(s["photoAsset"], sw)
                    self.assertIn("危険レベル", s["note"])
                self.assertEqual(len(originals), 3)
                self.assertEqual({q["photoKey"] for q in e["quiz"]}, {p[0] for p in photos[1:]})
                for q in e["quiz"]:
                    s = e["travelStops"][q["photoKey"]]
                    self.assertEqual(len(s["travelStory"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in s["travelStory"]))
                    self.assertTrue(any(src["url"].startswith("https://www.anzen.mofa.go.jp/") for src in s["historicalSources"]))
                    if code == "ET":
                        self.assertIn("渡航は勧め", s["travelStory"][1])
