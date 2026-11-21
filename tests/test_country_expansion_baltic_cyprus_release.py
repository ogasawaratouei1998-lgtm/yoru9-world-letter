"""Four-country photo release: exact source identities and complete experience."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems, _commons_identity
from check_country_experience import country_coverage
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads(r'''{"EE":[["ee-tallinn-toompea-cover","Diego Delso","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Vistas_panor%C3%A1micas_desde_Toompea%2C_Tallinn%2C_Estonia%2C_2012-08-05%2C_DD_25.JPG"],["ee-tallinn-square-postcard","Diego Delso","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Plaza_del_ayuntamiento%2C_Tallinn%2C_Estonia%2C_2012-08-05%2C_DD_01.JPG"],["ee-tartu-observatory-postcard","Eksootiline Lind","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:Tartu_T%C3%A4hetorn_%C3%B5htul.jpg"]],"LV":[["lv-riga-skyline-cover","Guillaume Speurt from Vilnius, Lithuania","CC BY-SA 2.0","https://commons.wikimedia.org/wiki/File:Rigas_skyline_%288229128055%29.jpg"],["lv-riga-artnouveau-postcard","Ainars Brūvelis","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Riga%2C_Str%C4%93lnieku_iela_%28Alberta_iela_13%29%2C_Art_Nouveau_-Jugendstil_-_Classicism_-_panoramio_%284%29.jpg"],["lv-kuldiga-bridge-postcard","Ymblanter","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:Baznicas_iela_bridge_Kuldiga.jpg"]],"LT":[["lt-vilnius-river-cover","Tiia Monto","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Vilnius_river.jpg"],["lt-vilnius-anne-postcard","Alma Pater","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Church_of_St_Anne_in_Vilnius_Apse.JPG"],["lt-nida-parnidis-postcard","Bernt Rostad","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Parnidis_dune.jpg"]],"CY":[["cy-paphos-coast-cover","El Nino","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Pafoszi_tengerpart_%28_panor%C3%A1mak%C3%A9p%29_-_Coast_of_Paphos_%28panorama%29_-_panoramio.jpg"],["cy-paphos-mosaic-postcard","Carole Raddato from FRANKFURT, Germany","CC BY-SA 2.0","https://commons.wikimedia.org/wiki/File:Mosaic_of_Narcissus%2C_from_the_House_of_Dionysos%2C_Paphos_Archaeological_Park_%28Nea_Paphos%29%2C_Cyprus_%2822518456155%29.jpg"],["cy-asinou-fresco-postcard","Zairon","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:Nikitari_Kirche_Panagia_Asinou_Au%C3%9Fenfresko_1.jpg"]]}''')

class BalticCyprusReleaseTests(unittest.TestCase):
    def test_complete_independent_photo_experience(self):
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
                originals = set()
                for key, author, license_name, page in photos:
                    s = e["travelStops"][key]
                    self.assertEqual(s["author"], author)
                    self.assertEqual(s["license"], license_name)
                    self.assertEqual(s["photoPage"], page)
                    self.assertEqual(_commons_identity(s["photo"]), _commons_identity(page))
                    originals.add(_commons_identity(page))
                    self.assertIn(s["photoAsset"], sw)
                self.assertEqual(len(originals), 3)
                self.assertEqual({q["photoKey"] for q in e["quiz"]}, {p[0] for p in photos[1:]})
                for q in e["quiz"]:
                    s = e["travelStops"][q["photoKey"]]
                    self.assertEqual(len(s["travelStory"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in s["travelStory"]))
                    self.assertTrue(s["historicalSources"])
