"""All available licensed destination postcards have substantial, factual reading content."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ExpandedTravelStoriesTest(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        self.html=(ROOT/"index.html").read_text(encoding="utf-8")

    def test_every_available_postcard_has_two_detailed_original_paragraphs(self):
        eligible={key:stop for key,stop in self.manifest.items()
                  if not stop.get("coverOnly") and not stop.get("quizOnly")}
        self.assertGreaterEqual(len(eligible),34)
        seen={}
        for key,stop in eligible.items():
            with self.subTest(destination=key):
                essay=stop.get("travelStory")
                self.assertIsInstance(essay,list)
                self.assertEqual(len(essay),2)
                self.assertTrue(all(isinstance(p,str) and len(p.strip())>=70
                                    and len(p.strip())<=360 for p in essay))
                self.assertNotEqual(essay[0],essay[1])
                self.assertIn(stop["country"],seen or {stop["country"]:True})
                # Different destinations use distinct writing; two IDs
                # referencing the *same* licensed photo may share it.
                asset=stop["photoAsset"]
                if asset in seen:
                    self.assertEqual(essay,seen[asset])
                else:
                    seen[asset]=essay
        self.assertGreaterEqual(len(seen),32)

    def test_travel_stories_are_escaped_and_are_opt_in(self):
        self.assertIn("Array.isArray(stop.travelStory)&&stop.travelStory.length===2",self.html)
        self.assertIn("stop.travelStory.map(paragraph=>'<p>'+escapeHtml(paragraph)+'</p>')",self.html)
        self.assertIn("class=\"travel-story\"",self.html)
        self.assertIn("景色の向こう側へ",self.html)
        self.assertIn("panel.hidden=!opening",self.html)
        self.assertIn("closeOptionalTravelPanels();",self.html)
        self.assertNotIn("名所へ30秒の小旅行",self.html)


if __name__=="__main__":
    unittest.main()
