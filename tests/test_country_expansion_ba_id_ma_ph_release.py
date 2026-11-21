"""Four country releases with distinct attributed original photographs."""
import json
import unittest
from pathlib import Path
from country_content import check_country_content, country_quiz_problems, _commons_identity
from check_country_experience import country_coverage
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads(r'''{"BA":[["ba-mostar-cover","Ramirez","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:Mostar_Old_Town_Panorama_2007.jpg"],["ba-mostar-night-postcard","BáthoryPéter (talk)","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Mostar%2C_Stari_Most_at_night.jpg"],["ba-visegrad-bridge-postcard","Pudelek (Marcin Szala)","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Mehmed_Pa%C5%A1a_Sokolovi%C4%87_Bridge%2C_Vi%C5%A1egrad.JPG"]],"ID":[["id-sumbing-cover","CEphoto, Uwe Aranas","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Indonesia_Mount-Sumbing-volcano-01.jpg"],["id-borobudur-stupa-postcard","CEphoto, Uwe Aranas","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Borobudur-Temple-Park_Indonesia_Stupas-of-Borobudur-01.jpg"],["id-prambanan-postcard","Crisco 1492","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Entrance_to_Prambanan%2C_23_November_2013.jpg"]],"MA":[["ma-fez-street-cover","Annabel Symington","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Flickr_-_stringer_bel_-_the_old_medina_in_Fes%2C_Morocco.jpg"],["ma-fez-tannery-postcard","yeowatzup","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Fez_Medina%2C_Morocco_%286343039561%29.jpg"],["ma-ait-benhaddou-postcard","cliff williams","CC BY-SA 2.0","https://commons.wikimedia.org/wiki/File:A%C3%AFtBenhaddou_Morocco_2.jpg"]],"PH":[["ph-hapao-terraces-cover","Arian Zwegers from Brussels, Belgium","CC BY 2.0","https://commons.wikimedia.org/wiki/File:Hungduan%2C_Hapao_rice_terraces_-_Flickr.jpg"],["ph-batad-terraces-postcard","Ericmontalban","CC BY-SA 3.0","https://commons.wikimedia.org/wiki/File:Batad_rice_terraces_in_Ifugao.jpg"],["ph-vigan-crisologo-postcard","Hydztemple","CC BY-SA 4.0","https://commons.wikimedia.org/wiki/File:Calle_Crisologo%2C_Vigan_Ilocos_Sur_October%2C_2025.jpg"]]}''')

class FourCountryReleaseTests(unittest.TestCase):
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
